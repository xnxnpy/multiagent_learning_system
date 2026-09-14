"""学习笔记 API — 知识沉淀

CRUD + 可选写入 ChromaDB（使笔记可被 RAG 检索）。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.models import StudyNote, User
from app.models.base import get_db
from app.core.logger import log

router = APIRouter(prefix="/notes", tags=["学习笔记"])


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    stage_id: Optional[int] = None
    source: str = Field(default="manual", pattern="^(manual|tutor|resource)$")
    tags: str = ""


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    tags: Optional[str] = None


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    stage_id: Optional[int] = None
    source: str
    tags: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class NoteListResponse(BaseModel):
    total: int
    items: List[NoteOut]


def _to_out(n: StudyNote) -> NoteOut:
    return NoteOut(
        id=n.id,
        title=n.title,
        content=n.content,
        stage_id=n.stage_id,
        source=n.source,
        tags=n.tags or "",
        created_at=str(n.created_at) if n.created_at else None,
        updated_at=str(n.updated_at) if n.updated_at else None,
    )


async def _index_note(note: StudyNote) -> None:
    """笔记写入 ChromaDB，使后续 RAG 可检索"""
    try:
        from app.vectorstore.chroma_store import vector_store
        note_key = f"user{note.user_id}_note{note.id}"
        # 先删旧块
        vector_store.delete_documents_by_filter({"note_key": note_key})
        text = f"{note.title}\n{note.content}"
        if not text.strip():
            return
        metadatas = [{
            "user_id": note.user_id,
            "resource_type": "note",
            "note_key": note_key,
            "topic": note.title,
            "source": "study_note",
        }]
        vector_store.add_documents([text[:2000]], metadatas=metadatas, ids=[note_key])
    except Exception as e:
        log.warning(f"笔记索引进 Chroma 失败（不影响保存）: {e}")


@router.get("", response_model=NoteListResponse)
async def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(StudyNote).where(StudyNote.user_id == current_user.id)
    if search:
        like = f"%{search}%"
        query = query.where(StudyNote.title.like(like) | StudyNote.content.like(like))
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(
        query.order_by(StudyNote.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return NoteListResponse(total=total, items=[_to_out(n) for n in result.scalars().all()])


@router.post("", response_model=NoteOut)
async def create_note(
    body: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = StudyNote(
        user_id=current_user.id,
        title=body.title.strip(),
        content=body.content.strip(),
        stage_id=body.stage_id,
        source=body.source,
        tags=body.tags or "",
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    await _index_note(note)
    return _to_out(note)


@router.put("/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: int,
    body: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(StudyNote, note_id)
    if not note or note.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="笔记不存在")
    if body.title is not None:
        note.title = body.title.strip()
    if body.content is not None:
        note.content = body.content.strip()
    if body.tags is not None:
        note.tags = body.tags
    await db.commit()
    await db.refresh(note)
    await _index_note(note)
    return _to_out(note)


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(StudyNote, note_id)
    if not note or note.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="笔记不存在")
    note_key = f"user{note.user_id}_note{note.id}"
    await db.delete(note)
    await db.commit()
    try:
        from app.vectorstore.chroma_store import vector_store
        vector_store.delete_documents_by_filter({"note_key": note_key})
    except Exception:
        pass
    return {"message": "已删除"}
