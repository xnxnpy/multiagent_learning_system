"""学生个人知识库 — 材料上传与管理

- 每个学生只看到/删除自己上传的材料（uploaded_by + Chroma metadata.user_id）
- 分块写入共享 collection，但带 user_id，retrieve_smart 按用户过滤
"""
import os
import tempfile
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.logger import log
from app.models import KnowledgeDocument, User, get_db

router = APIRouter(prefix="/knowledge", tags=["知识库"])


class UploadResponse(BaseModel):
    success: bool
    message: str
    documents_added: int = 0


def _doc_key(user_id: int, doc_id: int) -> str:
    return f"user{user_id}_kbdoc{doc_id}"


async def _index_chunks(
    user_id: int, doc_id: int, file_path: str, filename: str
) -> int:
    """解析文件 → 分块 → 带 user_id 写入 Chroma，返回块数"""
    from app.rag.document_loader import DocumentLoader
    from app.rag.text_splitter import ChineseTextSplitter
    from app.vectorstore.chroma_store import vector_store

    docs = DocumentLoader().load_document(file_path)
    chunks = ChineseTextSplitter(chunk_size=500, chunk_overlap=100).split_documents(docs)
    if not chunks:
        return 0

    key = _doc_key(user_id, doc_id)
    vector_store.delete_documents_by_filter({"doc_key": key})

    texts, metas, ids = [], [], []
    for i, d in enumerate(chunks):
        text = d.page_content or ""
        if not text.strip():
            continue
        texts.append(text)
        metas.append({
            "user_id": user_id,
            "doc_key": key,
            "doc_id": doc_id,
            "filename": filename,
            "resource_type": "kb_document",
            "source": "student_upload",
        })
        ids.append(f"{key}_c{i}")

    if texts:
        vector_store.add_documents(texts, metadatas=metas, ids=ids)
    return len(texts)


@router.post("/upload", response_model=UploadResponse)
async def upload_knowledge(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传个人知识库材料（仅本人可检索引用）"""
    log.info(f"学生 {current_user.id} 上传 {len(files)} 个知识库文档")
    saved, failed = 0, 0

    for file in files:
        record = KnowledgeDocument(
            filename=file.filename or "unnamed",
            file_size=0,
            file_type=os.path.splitext(file.filename or "")[1].lower().lstrip("."),
            status="processing",
            uploaded_by=current_user.id,
        )
        db.add(record)
        await db.flush()

        tmp_path = None
        try:
            content = await file.read()
            record.file_size = len(content)
            ext = os.path.splitext(file.filename or "")[1]
            tmp_path = os.path.join(tempfile.gettempdir(), f"stu_kb_{record.id}{ext}")
            with open(tmp_path, "wb") as f:
                f.write(content)

            n = await _index_chunks(current_user.id, record.id, tmp_path, record.filename)
            if n == 0:
                raise ValueError("文档无可提取文本")

            record.status = "completed"
            record.chunk_count = n
            record.completed_at = datetime.utcnow()
            saved += 1
        except Exception as e:
            log.error(f"上传 {record.filename} 失败: {e}")
            record.status = "failed"
            record.error_message = str(e)[:500]
            failed += 1
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    await db.commit()
    msg = f"成功 {saved} 个"
    if failed:
        msg += f"，失败 {failed} 个"
    return UploadResponse(success=saved > 0, message=msg, documents_added=saved)


@router.get("/documents")
async def list_my_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """当前学生自己的知识库文档列表"""
    base = select(KnowledgeDocument).where(
        KnowledgeDocument.uploaded_by == current_user.id
    )
    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0
    result = await db.execute(
        base.order_by(KnowledgeDocument.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    docs = result.scalars().all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": d.id,
                "filename": d.filename,
                "file_size": d.file_size,
                "file_type": d.file_type,
                "status": d.status,
                "chunk_count": d.chunk_count,
                "error_message": d.error_message,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "completed_at": d.completed_at.isoformat() if d.completed_at else None,
            }
            for d in docs
        ],
    }


@router.get("/stats")
async def my_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """个人知识库统计"""
    rows = await db.execute(
        select(KnowledgeDocument.status, func.count())
        .where(KnowledgeDocument.uploaded_by == current_user.id)
        .group_by(KnowledgeDocument.status)
    )
    by_status = {r[0]: r[1] for r in rows.all()}
    total = sum(by_status.values())
    completed = by_status.get("completed", 0)
    chunks = (await db.execute(
        select(func.coalesce(func.sum(KnowledgeDocument.chunk_count), 0)).where(
            KnowledgeDocument.uploaded_by == current_user.id,
            KnowledgeDocument.status == "completed",
        )
    )).scalar() or 0
    return {
        "total_documents": total,
        "total_chunks": int(chunks),
        "failed": by_status.get("failed", 0),
        "completed": completed,
        "collection_name": "knowledge_base",
    }


@router.delete("/documents/{doc_id}")
async def delete_my_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除自己的文档及对应向量块"""
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.uploaded_by == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在或无权删除")

    try:
        from app.vectorstore.chroma_store import vector_store
        vector_store.delete_documents_by_filter({"doc_key": _doc_key(current_user.id, doc.id)})
    except Exception as e:
        log.warning(f"删除向量块失败（继续删元数据）: {e}")

    await db.delete(doc)
    await db.commit()
    return {"message": "已删除"}
