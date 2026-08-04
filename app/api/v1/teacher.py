import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from app.models import User, Course, ResourceReview, LearningRecord, StudentProfile, LearningResource
from app.models.knowledge_document import KnowledgeDocument
from app.api.v1.deps import get_current_user, require_roles
from app.rag.document_loader import DocumentLoader
from app.rag.text_splitter import ChineseTextSplitter
from app.rag.retriever import retriever
from app.services.course_service import course_service
from app.services.resource_review_service import resource_review_service
from app.services.stats_service import stats_service
from app.repositories.learning_path_repository import LearningPathRepository
from app.schemas.common import PageResponse
from app.core.logger import log
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import get_db
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter(prefix="/teacher", tags=["教师端"])


class CourseCreate(BaseModel):
    """创建课程请求"""
    title: str = Field(..., description="课程标题")
    description: Optional[str] = Field(None, description="课程描述")
    knowledge_tree: Optional[dict] = Field(None, description="知识树结构")


class CourseUpdate(BaseModel):
    """更新课程请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    knowledge_tree: Optional[dict] = None


class CourseResponse(BaseModel):
    """课程响应"""
    id: int
    teacher_id: int
    title: str
    description: Optional[str]
    knowledge_tree: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool
    message: str
    documents_added: int


class DocumentInfo(BaseModel):
    """文档信息"""
    file_name: str
    file_size: int
    status: str
    message: str


class KnowledgeStatsResponse(BaseModel):
    """知识库统计响应"""
    total_documents: int
    total_chunks: int
    collection_name: str


class KnowledgeGraphNode(BaseModel):
    """知识图谱节点"""
    id: str
    label: str
    level: int
    description: Optional[str] = ""


class KnowledgeGraphEdge(BaseModel):
    """知识图谱边"""
    source: str
    target: str
    relationship: Optional[str] = ""


class KnowledgeGraphResponse(BaseModel):
    """知识图谱响应"""
    title: str
    knowledge_point_count: int
    nodes: List[KnowledgeGraphNode]
    edges: List[KnowledgeGraphEdge]


class ResourceReviewResponse(BaseModel):
    """资源审核响应"""
    id: int
    resource_type: str
    resource_content: str
    status: str
    creator_id: int
    reviewer_id: Optional[int]
    review_comment: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewRequest(BaseModel):
    """审核请求"""
    action: str = Field(..., description="操作: approve/reject")
    comment: Optional[str] = Field(None, description="审核意见")


class AssignmentCreate(BaseModel):
    """作业创建请求"""
    title: str = Field(..., description="作业标题")
    description: str = Field(..., description="作业描述")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    target_students: List[int] = Field(default_factory=list, description="目标学生ID列表")
    status: Optional[str] = Field(None, description="作业状态: draft/published")


class AssignmentResponse(BaseModel):
    """作业响应"""
    id: int
    title: str
    description: str
    due_date: Optional[datetime]
    target_students: List[int]
    created_at: datetime

    class Config:
        from_attributes = True


class StudentProgress(BaseModel):
    """学生进度"""
    student_id: int
    student_name: str
    total_learning_records: int
    accuracy: float
    average_score: float
    current_path_stage: Optional[int]
    last_activity: Optional[datetime]


class ClassStatsResponse(BaseModel):
    """班级统计响应"""
    total_students: int
    active_students: int
    average_accuracy: float
    total_learning_records: int
    student_progress: List[StudentProgress]


class PathAdjustmentRequest(BaseModel):
    """路径调整请求"""
    student_id: Optional[int] = Field(None, description="学生ID")
    new_stages: List[dict] = Field(..., description="新的学习阶段")
    reason: Optional[str] = Field(None, description="调整原因")


# ==================== 课程管理接口 ====================

@router.post("/courses", response_model=CourseResponse, status_code=201)
async def create_course(
    course_data: CourseCreate,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """创建课程"""
    log.info(f"教师 {current_user.id} 创建课程: {course_data.title}")
    
    course = await course_service.create(
        db=db,
        teacher_id=current_user.id,
        title=course_data.title,
        description=course_data.description,
        knowledge_tree=course_data.knowledge_tree
    )
    
    return CourseResponse.model_validate(course)


@router.get("/courses", response_model=PageResponse[CourseResponse])
async def get_courses(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取课程列表"""
    log.info(f"教师 {current_user.id} 获取课程列表")
    
    skip = (page - 1) * page_size
    courses, total = await course_service.get_courses_paginated(
        db, skip=skip, limit=page_size, search=search, teacher_id=current_user.id
    )
    
    return PageResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[CourseResponse.model_validate(c) for c in courses],
    )


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: int,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取单个课程"""
    log.info(f"教师 {current_user.id} 获取课程: {course_id}")
    
    course = await course_service.get_by_id(db, course_id)
    
    if course.teacher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问此课程")
    
    return CourseResponse.model_validate(course)


@router.put("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_data: CourseUpdate,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """更新课程"""
    log.info(f"教师 {current_user.id} 更新课程: {course_id}")
    
    course = await course_service.get_by_id(db, course_id)
    
    if course.teacher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权修改此课程")
    
    course = await course_service.update(
        db=db,
        course_id=course_id,
        title=course_data.title,
        description=course_data.description,
        knowledge_tree=course_data.knowledge_tree
    )
    
    return CourseResponse.model_validate(course)


@router.delete("/courses/{course_id}", status_code=204)
async def delete_course(
    course_id: int,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """删除课程"""
    log.info(f"教师 {current_user.id} 删除课程: {course_id}")

    course = await course_service.get_by_id(db, course_id)

    if course.teacher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权删除此课程")

    await course_service.delete(db, course_id)
    return None


@router.get("/courses/{course_id}/export")
async def export_course_report(
    course_id: int,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """导出课程统计报表"""
    log.info(f"教师 {current_user.id} 导出课程 {course_id} 报表")

    from sqlalchemy import select
    import csv
    import io

    course = await course_service.get_by_id(db, course_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["学生ID", "学生姓名", "学习记录数", "正确率", "平均分", "最后活动"])

    student_query = select(User).where(User.role == "student")
    student_result = await db.execute(student_query)
    students = list(student_result.scalars().all())

    for student in students:
        record_query = select(LearningRecord).where(
            LearningRecord.user_id == student.id
        )
        record_result = await db.execute(record_query)
        records = list(record_result.scalars().all())

        accuracy = 0
        avg_score = 0
        if records:
            correct_count = sum(1 for r in records if r.correct)
            accuracy = correct_count / len(records)
            avg_score = sum(r.score or 0 for r in records) / len(records)

        last_activity = records[0].created_at.isoformat() if records else "无"

        writer.writerow([
            student.id,
            student.real_name or student.username,
            len(records),
            f"{accuracy:.2%}",
            f"{avg_score:.2f}",
            last_activity
        ])

    csv_content = output.getvalue()
    output.close()

    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=course_{course_id}_report_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


# ==================== 知识库管理接口 ====================

@router.post("/knowledge/upload", response_model=UploadResponse)
async def upload_knowledge(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """上传知识库文档（支持多文件，逐个处理，记录状态）"""
    log.info(f"教师 {current_user.id} 上传 {len(files)} 个文档")

    saved_files = []
    failed_files = []
    document_loader = DocumentLoader()
    text_splitter = ChineseTextSplitter(chunk_size=500, chunk_overlap=100)

    for file in files:
        # 创建元数据记录（status=processing）
        doc_record = KnowledgeDocument(
            filename=file.filename,
            file_size=0,
            file_type=os.path.splitext(file.filename or "")[1].lower().lstrip("."),
            status="processing",
            uploaded_by=current_user.id,
        )
        db.add(doc_record)
        await db.flush()

        try:
            # 读取文件并记录大小
            content = await file.read()
            doc_record.file_size = len(content)

            import tempfile
            file_ext = os.path.splitext(file.filename or "")[1]
            tmp_dir = tempfile.gettempdir()
            file_path = os.path.join(tmp_dir, f"kb_{doc_record.id}{file_ext}")
            with open(file_path, "wb") as buffer:
                buffer.write(content)

            # 解析 + 分块 + 向量化
            docs = document_loader.load_document(file_path)
            chunks = text_splitter.split_documents(docs)
            await retriever.add_documents(chunks)

            # 更新状态
            doc_record.status = "completed"
            doc_record.chunk_count = len(chunks)
            doc_record.completed_at = datetime.utcnow()
            saved_files.append(file.filename)

            os.remove(file_path)

        except Exception as e:
            log.error(f"上传文件 {file.filename} 失败: {e}")
            doc_record.status = "failed"
            doc_record.error_message = str(e)[:500]
            failed_files.append(file.filename)
            import tempfile as _tf
            safe_path = os.path.join(_tf.gettempdir(), f"kb_{doc_record.id}{os.path.splitext(file.filename or '')[1]}")
            if os.path.exists(safe_path):
                os.remove(safe_path)

    await db.commit()

    msg = f"成功 {len(saved_files)} 个"
    if failed_files:
        msg += f"，失败 {len(failed_files)} 个"
    return UploadResponse(
        success=len(saved_files) > 0,
        message=msg,
        documents_added=len(saved_files),
    )


@router.get("/knowledge/documents")
async def list_knowledge_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库文档列表"""
    count_q = select(func.count(KnowledgeDocument.id))
    total_result = await db.execute(count_q)
    total = total_result.scalar()

    query = (
        select(KnowledgeDocument)
        .order_by(KnowledgeDocument.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
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


@router.delete("/knowledge/clear")
async def clear_knowledge(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """清空知识库"""
    log.info(f"教师 {current_user.id} 清空知识库")

    try:
        await retriever.clear_collection()
        # 清除元数据
        await db.execute(KnowledgeDocument.__table__.delete())
        await db.commit()
        return {"message": "知识库已清空"}
    except Exception as e:
        log.error(f"清空知识库失败: {e}")
        raise HTTPException(status_code=500, detail="清空知识库失败")


@router.delete("/knowledge")
async def delete_knowledge(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
):
    """删除知识库（兼容前端调用）"""
    return await clear_knowledge(current_user)


@router.get("/knowledge/stats", response_model=KnowledgeStatsResponse)
async def get_knowledge_stats(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
):
    """获取知识库统计信息"""
    log.info(f"教师 {current_user.id} 获取知识库统计")
    
    try:
        stats = retriever.get_collection_stats()
        return KnowledgeStatsResponse(
            total_documents=stats.get("count", 0),
            total_chunks=stats.get("count", 0),
            collection_name=stats.get("name", "knowledge_base")
        )
    except Exception as e:
        log.error(f"获取知识库统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取知识库统计失败")


# ==================== 知识图谱接口 ====================

@router.post("/knowledge/graph/generate", response_model=KnowledgeGraphResponse)
async def generate_knowledge_graph(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """从已上传文档中自动生成知识图谱"""
    log.info(f"教师 {current_user.id} 生成知识图谱")

    # 从 ChromaDB 获取全部文档内容
    try:
        collection = retriever.vector_store.get_collection()
        if not collection:
            raise HTTPException(status_code=400, detail="知识库为空，请先上传文档")
        count = collection.count()
        if count == 0:
            raise HTTPException(status_code=400, detail="知识库为空，请先上传文档")

        all_docs = collection.get(limit=min(count, 200))
        documents = all_docs.get("documents", [])
        content = "\n\n".join(doc for doc in documents if doc)
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"从 ChromaDB 获取文档失败: {e}")
        raise HTTPException(status_code=500, detail="获取知识库文档失败")

    if not content.strip():
        raise HTTPException(status_code=400, detail="知识库文档内容为空")

    from app.agents.knowledge_graph_agent import KnowledgeGraphAgent
    from app.api.v1.student import send_agent_progress
    await send_agent_progress(
        current_user.id, step="knowledge_graph",
        step_name="知识图谱 Agent · 从文档构建知识图谱中", progress=10, status="running",
    )
    try:
        agent = KnowledgeGraphAgent(db)
        graph_data = await agent.run(topic="上传文档知识图谱", content=content, user_id=current_user.id)
    except Exception:
        await send_agent_progress(
            current_user.id, step="knowledge_graph", step_name="知识图谱 Agent · 运行失败",
            progress=10, status="failed",
        )
        raise

    # 补全缺失字段
    graph_data.setdefault("title", "上传文档知识图谱")
    graph_data.setdefault("knowledge_point_count", len(graph_data.get("nodes", [])))

    await send_agent_progress(
        current_user.id, step="knowledge_graph", step_name="完成",
        progress=100, status="completed",
    )

    return KnowledgeGraphResponse(**graph_data)


@router.get("/knowledge/graph", response_model=Optional[KnowledgeGraphResponse])
async def get_knowledge_graph(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取已缓存的知识图谱"""
    log.info(f"教师 {current_user.id} 获取知识图谱")

    from sqlalchemy import select as sa_select
    result = await db.execute(
        sa_select(LearningResource).where(
            LearningResource.user_id == current_user.id,
            LearningResource.resource_type == "knowledge_graph",
        ).order_by(LearningResource.created_at.desc()).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return None

    return KnowledgeGraphResponse(**record.content)


# ==================== 资源审核接口 ====================

@router.get("/resources/pending", response_model=PageResponse[ResourceReviewResponse])
async def get_pending_resources(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取待审核资源列表"""
    log.info(f"教师 {current_user.id} 获取待审核资源")
    
    skip = (page - 1) * page_size
    reviews, total = await resource_review_service.get_reviews_paginated(
        db, skip=skip, limit=page_size, status="pending"
    )
    
    return PageResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[ResourceReviewResponse.model_validate(r) for r in reviews],
    )


@router.get("/resources/{review_id}", response_model=ResourceReviewResponse)
async def get_resource(
    review_id: int,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取资源审核详情"""
    log.info(f"教师 {current_user.id} 获取资源: {review_id}")

    review = await resource_review_service.get_by_id(db, review_id)
    return ResourceReviewResponse.model_validate(review)


@router.get("/resources")
async def get_all_resources(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取所有资源列表（兼容前端调用）"""
    log.info(f"教师 {current_user.id} 获取所有资源")

    skip = (page - 1) * page_size
    reviews, total = await resource_review_service.get_reviews_paginated(
        db, skip=skip, limit=page_size, status=None
    )

    return PageResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[ResourceReviewResponse.model_validate(r) for r in reviews],
    )


@router.put("/resources/{review_id}/review", response_model=ResourceReviewResponse)
async def review_resource(
    review_id: int,
    request: ReviewRequest,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """审核资源"""
    log.info(f"教师 {current_user.id} 审核资源: {review_id}, 操作: {request.action}")

    if request.action == "approve":
        review = await resource_review_service.approve(
            db, review_id, current_user.id, request.comment
        )
    elif request.action == "reject":
        if not request.comment:
            raise HTTPException(status_code=400, detail="拒绝操作必须提供原因")
        review = await resource_review_service.reject(
            db, review_id, current_user.id, request.comment
        )
    else:
        raise HTTPException(status_code=400, detail="无效的操作类型")

    return ResourceReviewResponse.model_validate(review)


@router.post("/resources/{review_id}/review", response_model=ResourceReviewResponse)
async def review_resource_post(
    review_id: int,
    request: ReviewRequest,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """审核资源（POST 兼容）"""
    return await review_resource(review_id, request, current_user, db)


# ==================== 学生资源+质量分数接口 ====================

class TeacherRegenerateRequest(BaseModel):
    """教师端重新生成请求"""
    stage_id: int = Field(..., description="阶段 ID")


@router.get("/students/resources")
async def get_all_student_resources(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取所有学生的学习资源（按阶段分组，每个阶段每种类型都显示）"""
    log.info(f"教师 {current_user.id} 获取所有学生资源")

    RESOURCE_NAMES = {
        "document": "学习文档", "mindmap": "思维导图", "question": "练习题目",
        "code": "代码示例", "ppt_video": "教学视频",
        "reading_material": "拓展阅读", "glossary": "术语词汇",
        "knowledge_link": "知识关联", "summary": "学习总结",
    }
    RESOURCE_ORDER = ["document", "ppt_video", "mindmap", "question", "code", "reading_material", "glossary", "knowledge_link", "summary"]

    students_result = await db.execute(select(User).where(User.role == "student"))
    students = list(students_result.scalars().all())

    result = []
    for student in students:
        # 查询该学生所有资源（不排序，避免大 JSON content 列导致 sort_buffer 溢出）
        res_result = await db.execute(
            select(LearningResource)
            .where(LearningResource.user_id == student.id)
        )
        all_resources = res_result.scalars().all()

        # Python 端排序（轻量级，不涉及大字段）
        all_resources.sort(key=lambda r: (r.stage_id or 0, r.resource_type, -(r.created_at.timestamp() if r.created_at else 0)))

        # 按阶段分组，每个阶段内按类型去重（保留最新）
        stages_map = {}
        for r in all_resources:
            stage_id = r.stage_id or 0
            if stage_id not in stages_map:
                stages_map[stage_id] = {}
            # 同一阶段同一类型只保留最新（id 最大的）
            if r.resource_type not in stages_map[stage_id]:
                stages_map[stage_id][r.resource_type] = r

        # 扁平化为列表，附带阶段信息
        resources = []
        for stage_id in sorted(stages_map.keys()):
            for res_type, r in stages_map[stage_id].items():
                # 统一 content 为 dict：兼容历史保存的 JSON 字符串
                content = r.content
                if isinstance(content, str):
                    try:
                        import json as _json
                        _parsed = _json.loads(content)
                        content = _parsed if isinstance(_parsed, (dict, list)) else {"content": content}
                    except Exception:
                        content = {"content": content}
                elif not isinstance(content, dict):
                    content = {}
                # 规范化资源内容
                if isinstance(content, dict):
                    from app.agents.utils import normalize_resource_content
                    content = normalize_resource_content(content, res_type)
                quality = content.get("quality_score") or content.get("quality") or {}
                resources.append({
                    "resource_type": res_type,
                    "resource_type_name": RESOURCE_NAMES.get(res_type, res_type),
                    "topic": r.topic,
                    "stage_id": r.stage_id,
                    "stage_title": f"阶段 {stage_id}",
                    "quality_score": quality,
                    "content": content,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                })

        # 按标准顺序排序
        resources.sort(key=lambda r: RESOURCE_ORDER.index(r["resource_type"]) if r["resource_type"] in RESOURCE_ORDER else 99)

        result.append({
            "user_id": student.id,
            "username": student.username,
            "real_name": getattr(student, "real_name", None) or student.username,
            "resources": resources,
        })

    return result


@router.post("/students/{student_id}/resources/{resource_type}/regenerate")
async def teacher_regenerate_resource(
    student_id: int,
    resource_type: str,
    request: TeacherRegenerateRequest,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """教师重新生成指定学生的某类资源"""
    log.info(f"教师 {current_user.id} 重新生成学生 {student_id} 的 {resource_type}")

    from app.models import LearningPath
    from app.api.v1.student import _RESOURCE_GENERATORS, _generate_and_evaluate

    if resource_type not in _RESOURCE_GENERATORS:
        raise HTTPException(status_code=400, detail=f"不支持的资源类型: {resource_type}")

    # 验证学生存在
    student = await db.get(User, student_id)
    if not student or student.role != "student":
        raise HTTPException(status_code=404, detail="学生不存在")

    # 获取学生活跃画像
    profile_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == student_id,
            StudentProfile.is_active == True,
        )
    )
    active_profile = profile_result.scalar_one_or_none()
    profile_id = active_profile.id if active_profile else None

    path_query = select(LearningPath).where(LearningPath.user_id == student_id)
    if profile_id:
        path_query = path_query.where(LearningPath.profile_id == profile_id)
    path_result = await db.execute(path_query)
    path = path_result.scalar_one_or_none()
    if not path or not path.stages:
        raise HTTPException(status_code=404, detail="学生学习路径不存在")

    stage = next((s for s in path.stages if s.get("stage_id") == request.stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail=f"阶段 {request.stage_id} 不存在")

    kps = stage.get("knowledge_points", [])
    stage_topic = "、".join([kp.get("name", "") if isinstance(kp, dict) else str(kp) for kp in kps]) or stage.get("title", "")

    # 删除旧资源（按 profile_id 过滤）
    delete_query = LearningResource.__table__.delete().where(
        LearningResource.user_id == student_id,
        LearningResource.stage_id == request.stage_id,
        LearningResource.resource_type == resource_type,
    )
    if profile_id:
        delete_query = delete_query.where(LearningResource.profile_id == profile_id)
    await db.execute(delete_query)

    # 如果重新生成题目，同时清掉该阶段的旧答题记录
    if resource_type == "question":
        from app.models import LearningRecord
        await db.execute(
            LearningRecord.__table__.delete().where(
                LearningRecord.user_id == student_id,
                LearningRecord.resource_type == "question",
            )
        )

    await db.commit()

    try:
        content, quality = await _generate_and_evaluate(
            db, student_id, request.stage_id, stage_topic, resource_type,
            profile_id=profile_id, trigger_user_id=current_user.id,
        )
        return {"success": True, "content": content, "quality_score": quality}
    except Exception as e:
        log.error(f"教师重新生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重新生成失败: {str(e)}")


@router.post("/students/{student_id}/resources/{resource_type}/reevaluate")
async def teacher_reevaluate_resource(
    student_id: int,
    resource_type: str,
    request: TeacherRegenerateRequest,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """教师对指定学生的某类资源重新评估质量"""
    log.info(f"教师 {current_user.id} 重新评估学生 {student_id} 的 {resource_type}")

    # 查找资源
    result = await db.execute(
        select(LearningResource).where(
            LearningResource.user_id == student_id,
            LearningResource.stage_id == request.stage_id,
            LearningResource.resource_type == resource_type,
        ).order_by(LearningResource.created_at.desc()).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="资源不存在")

    content = record.content if isinstance(record.content, dict) else {"content": str(record.content)}
    # 规范化资源内容
    if isinstance(content, dict):
        from app.agents.utils import normalize_resource_content
        content = normalize_resource_content(content, resource_type)
    topic = record.topic or ""

    try:
        from app.api.v1.student import send_agent_progress, _RESOURCE_AGENT_NAMES
        from app.agents.resource_quality_agent import ResourceQualityAgent
        agent_name = _RESOURCE_AGENT_NAMES.get(resource_type, f"{resource_type} Agent")
        await send_agent_progress(
            current_user.id, step=resource_type,
            step_name=f"{agent_name.split(' · ')[0]} · 资源质量评估中",
            progress=30, status="running", stage_id=request.stage_id,
        )
        quality_agent = ResourceQualityAgent(db)
        quality = await quality_agent.run(
            topic=topic, resource_type=resource_type,
            content=content, user_id=student_id,
        )
        # 更新 quality_score
        updated = dict(record.content) if isinstance(record.content, dict) else {}
        updated["quality_score"] = quality
        record.content = updated
        await db.commit()

        await send_agent_progress(
            current_user.id, step=resource_type, step_name="完成",
            progress=100, status="completed", stage_id=request.stage_id,
        )

        return {"success": True, "quality_score": quality}
    except Exception as e:
        log.error(f"教师重新评估失败: {e}", exc_info=True)
        from app.api.v1.student import send_agent_progress as _sap
        await _sap(
            current_user.id, step=resource_type, step_name="资源质量评估失败",
            progress=30, status="failed", stage_id=request.stage_id,
        )
        raise HTTPException(status_code=500, detail=f"重新评估失败: {str(e)}")


# ==================== 班级学情统计接口 ====================

@router.get("/class/stats", response_model=ClassStatsResponse)
async def get_class_stats(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取班级学情统计"""
    log.info(f"教师 {current_user.id} 获取班级学情统计")

    from sqlalchemy import select, and_

    student_query = select(User).where(User.role == "student")
    student_result = await db.execute(student_query)
    students = list(student_result.scalars().all())

    student_progress_list = []
    active_count = 0

    for student in students:
        record_query = select(LearningRecord).where(
            LearningRecord.user_id == student.id
        )
        record_result = await db.execute(record_query)
        records = list(record_result.scalars().all())

        path_repo = LearningPathRepository()
        path = await path_repo.get_latest_by_user_id(db, student.id)

        accuracy = 0
        avg_score = 0
        if records:
            correct_count = sum(1 for r in records if r.correct)
            accuracy = correct_count / len(records)
            avg_score = sum(r.score or 0 for r in records) / len(records)

        last_activity = records[0].created_at if records else None

        if records:
            active_count += 1

        student_progress_list.append(StudentProgress(
            student_id=student.id,
            student_name=student.real_name or student.username,
            total_learning_records=len(records),
            accuracy=accuracy,
            average_score=avg_score,
            current_path_stage=path.stages[0].get("stage_id") if path and path.stages else None,
            last_activity=last_activity
        ))

    total_records = sum(s.total_learning_records for s in student_progress_list)
    avg_accuracy = sum(s.accuracy for s in student_progress_list) / len(student_progress_list) if student_progress_list else 0

    return ClassStatsResponse(
        total_students=len(students),
        active_students=active_count,
        average_accuracy=avg_accuracy,
        total_learning_records=total_records,
        student_progress=student_progress_list
    )


@router.get("/analytics")
async def get_analytics(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取班级学情分析数据（兼容前端调用）"""
    log.info(f"教师 {current_user.id} 获取学情分析")
    return await get_class_stats(current_user, db)


@router.get("/analytics/class-stats")
async def get_class_stats_analytics(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取班级统计（兼容前端调用）"""
    log.info(f"教师 {current_user.id} 获取班级统计")
    return await get_class_stats(current_user, db)


@router.get("/analytics/export")
async def export_analytics_report(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """导出班级报表（兼容前端调用）"""
    log.info(f"教师 {current_user.id} 导出报表")
    return await export_class_report(current_user, db)


@router.get("/student/{student_id}/progress")
async def get_student_progress(
    student_id: int,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取单个学生学习进度"""
    log.info(f"教师 {current_user.id} 获取学生 {student_id} 的学习进度")

    from sqlalchemy import select

    record_query = select(LearningRecord).where(
        LearningRecord.user_id == student_id
    ).order_by(LearningRecord.created_at.desc())
    record_result = await db.execute(record_query)
    records = list(record_result.scalars().all())

    path_repo = LearningPathRepository()
    path = await path_repo.get_latest_by_user_id(db, student_id)

    profile_query = select(StudentProfile).where(
        StudentProfile.user_id == student_id,
        StudentProfile.is_active == True,
    )
    profile_result = await db.execute(profile_query)
    profile = profile_result.scalar_one_or_none()

    return {
        "student_id": student_id,
        "learning_records": len(records),
        "accuracy": sum(1 for r in records if r.correct) / len(records) if records else 0,
        "average_score": sum(r.score or 0 for r in records) / len(records) if records else 0,
        "learning_path": path.stages if path else None,
        "profile": {
            "knowledge_level": profile.knowledge_level if profile else None,
            "weakness": profile.weakness if profile else None
        } if profile else None
    }


@router.get("/students/progress")
async def get_students_progress_list(
    student_id: Optional[int] = Query(None, description="学生ID筛选"),
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """获取学生进度列表（兼容前端调用）"""
    log.info(f"教师 {current_user.id} 获取学生进度列表")

    if student_id:
        result = await get_student_progress(student_id, current_user, db)
        return [result]

    from sqlalchemy import select

    student_query = select(User).where(User.role == "student")
    student_result = await db.execute(student_query)
    students = list(student_result.scalars().all())

    progress_list = []
    for student in students:
        result = await get_student_progress(student.id, current_user, db)
        result["student_name"] = student.real_name or student.username
        progress_list.append(result)

    return progress_list


# ==================== 调整学生学习路径接口 ====================

@router.post("/student/{student_id}/path", response_model=dict)
async def adjust_student_path(
    student_id: int,
    request: PathAdjustmentRequest,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """调整学生学习路径"""
    log.info(f"教师 {current_user.id} 调整学生 {student_id} 的学习路径")

    path_repo = LearningPathRepository()
    path = await path_repo.get_latest_by_user_id(db, student_id)

    if path:
        await path_repo.update_stages(db, path.id, request.new_stages)
    else:
        path = await path_repo.create_for_user(
            db=db,
            user_id=student_id,
            title="教师调整的学习路径",
            stages=request.new_stages
        )

    return {
        "message": "学习路径已更新",
        "path_id": path.id,
        "reason": request.reason
    }


@router.post("/students/{student_id}/adjust-path", response_model=dict)
async def adjust_student_path_compat(
    student_id: int,
    request: PathAdjustmentRequest,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """调整学生学习路径（兼容前端调用）"""
    return await adjust_student_path(student_id, request, current_user, db)


# ==================== 导出统计报表接口 ====================

@router.get("/class/export")
async def export_class_report(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """导出班级统计报表"""
    log.info(f"教师 {current_user.id} 导出班级统计报表")
    
    from sqlalchemy import select
    import csv
    import io
    
    student_query = select(User).where(User.role == "student")
    student_result = await db.execute(student_query)
    students = list(student_result.scalars().all())
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["学生ID", "学生姓名", "学习记录数", "正确率", "平均分", "最后活动"])
    
    for student in students:
        record_query = select(LearningRecord).where(
            LearningRecord.user_id == student.id
        )
        record_result = await db.execute(record_query)
        records = list(record_result.scalars().all())
        
        accuracy = 0
        avg_score = 0
        if records:
            correct_count = sum(1 for r in records if r.correct)
            accuracy = correct_count / len(records)
            avg_score = sum(r.score or 0 for r in records) / len(records)
        
        last_activity = records[0].created_at.isoformat() if records else "无"
        
        writer.writerow([
            student.id,
            student.real_name or student.username,
            len(records),
            f"{accuracy:.2%}",
            f"{avg_score:.2f}",
            last_activity
        ])
    
    csv_content = output.getvalue()
    output.close()
    
    from fastapi.responses import StreamingResponse
    
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=class_report_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


# ==================== 作业管理接口 ====================

@router.post("/assignments", response_model=AssignmentResponse, status_code=201)
async def create_assignment(
    request: AssignmentCreate,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """创建作业"""
    from app.models import Assignment

    log.info(f"教师 {current_user.id} 创建作业: {request.title}")

    assignment = Assignment(
        teacher_id=current_user.id,
        title=request.title,
        description=request.description,
        due_date=request.due_date,
        target_students=request.target_students,
        status=request.status or "draft"
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    return AssignmentResponse(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        due_date=assignment.due_date,
        target_students=assignment.target_students or [],
        created_at=assignment.created_at
    )


@router.get("/assignments", response_model=PageResponse[AssignmentResponse])
async def get_assignments(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="作业状态"),
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """获取作业列表"""
    from app.models import Assignment
    from sqlalchemy import select, func

    log.info(f"教师 {current_user.id} 获取作业列表")

    query = select(Assignment).where(Assignment.teacher_id == current_user.id)
    if status:
        query = query.where(Assignment.status == status)

    total_query = select(func.count()).select_from(Assignment).where(Assignment.teacher_id == current_user.id)
    if status:
        total_query = total_query.where(Assignment.status == status)

    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    skip = (page - 1) * page_size
    query = query.offset(skip).limit(page_size)
    result = await db.execute(query)
    assignments = result.scalars().all()

    return PageResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            AssignmentResponse(
                id=a.id,
                title=a.title,
                description=a.description,
                due_date=a.due_date,
                target_students=a.target_students or [],
                created_at=a.created_at
            )
            for a in assignments
        ]
    )


@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: int,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """获取作业详情"""
    from app.models import Assignment

    log.info(f"教师 {current_user.id} 获取作业 {assignment_id}")

    result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.teacher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问此作业")

    return AssignmentResponse(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        due_date=assignment.due_date,
        target_students=assignment.target_students or [],
        created_at=assignment.created_at
    )


@router.put("/assignments/{assignment_id}/assign")
async def assign_assignment(
    assignment_id: int,
    request: dict,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """将作业分配给指定学生"""
    from app.models import Assignment
    from datetime import datetime

    student_ids = request.get("student_ids", [])

    log.info(f"教师 {current_user.id} 将作业 {assignment_id} 分配给 {len(student_ids)} 名学生")

    result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.teacher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权修改此作业")

    assignment.target_students = student_ids
    assignment.assigned_at = datetime.now()
    assignment.status = "published"
    await db.commit()

    return {
        "message": f"已分配给 {len(student_ids)} 名学生",
        "assignment_id": assignment_id,
        "student_count": len(student_ids)
    }


@router.put("/assignments/{assignment_id}")
async def update_assignment(
    assignment_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    status: Optional[str] = None,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """更新作业"""
    from app.models import Assignment

    log.info(f"教师 {current_user.id} 更新作业 {assignment_id}")

    result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.teacher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权修改此作业")

    if title is not None:
        assignment.title = title
    if description is not None:
        assignment.description = description
    if due_date is not None:
        assignment.due_date = due_date
    if status is not None:
        if status not in ["draft", "published", "closed"]:
            raise HTTPException(status_code=400, detail="无效的状态")
        assignment.status = status

    await db.commit()

    return {"message": "作业已更新"}


@router.delete("/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: int,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """删除作业"""
    from app.models import Assignment

    log.info(f"教师 {current_user.id} 删除作业 {assignment_id}")

    result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.teacher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权删除此作业")

    await db.delete(assignment)
    await db.commit()

    return {"message": "作业已删除"}


@router.get("/assignments/{assignment_id}/submissions")
async def get_assignment_submissions(
    assignment_id: int,
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """获取作业提交列表"""
    from app.models import Assignment, AssignmentSubmission

    log.info(f"教师 {current_user.id} 获取作业 {assignment_id} 的提交列表")

    result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.teacher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问此作业")

    submissions_result = await db.execute(
        select(AssignmentSubmission).where(AssignmentSubmission.assignment_id == assignment_id)
    )
    submissions = submissions_result.scalars().all()

    return {
        "assignment_id": assignment_id,
        "submissions": [
            {
                "id": s.id,
                "student_id": s.student_id,
                "content": s.content,
                "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
                "score": s.score,
                "feedback": s.feedback,
                "status": s.status
            }
            for s in submissions
        ]
    }
