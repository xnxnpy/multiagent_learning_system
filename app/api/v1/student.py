from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import get_db, User, StudentProfile, LearningPath, LearningRecord, ProfileChatMessage
from app.core.logger import log
from app.api.v1.deps import get_current_user
from app.agents.profile_agent import ProfileAgent
from app.agents.learning_path_agent import LearningPathAgent
from app.agents.document_agent import DocumentAgent
from app.agents.question_agent import QuestionAgent
from app.agents.mindmap_agent import MindmapAgent
from app.agents.knowledge_graph_agent import KnowledgeGraphAgent
from app.agents.code_agent import CodeAgent
from app.agents.evaluation_agent import create_evaluation_agent
from app.workflows.graph_builder import workflow_manager
from fastapi import HTTPException
from typing import Optional, List
import asyncio
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from datetime import datetime
import json

# 用户级评估锁，防止同一用户并发触发多次评估
_evaluating_users: set[int] = set()
# 用户级评估延迟任务：最后一道题提交后等几秒再评估
_eval_delay_tasks: dict[int, asyncio.Task] = {}
EVAL_DELAY_SECONDS = 5  # 延迟秒数


router = APIRouter(prefix="/student", tags=["学生端"])

# 资源生成互斥锁：防止同一用户同一阶段并发生成
_stage_gen_locks: dict[str, asyncio.Lock] = {}


class ProfileBuildRequest(BaseModel):
    """画像构建请求"""
    message: str = Field(..., description="学生输入的对话内容")


class ProfileResponse(BaseModel):
    """画像响应"""
    model_config = {"extra": "allow", "from_attributes": True}

    id: int
    user_id: int
    profile_name: Optional[str] = None
    major: Optional[str] = None
    grade: Optional[str] = None
    goal: Optional[str] = None
    knowledge_level: Optional[str] = None
    learning_style: Optional[str] = None
    interests: Optional[list] = None
    weakness: Optional[list] = None
    coding_ability: Optional[str] = None
    updated_at: Optional[datetime] = None


class LearningStage(BaseModel):
    """学习阶段"""
    model_config = {"extra": "allow"}

    stage_id: Optional[int] = None
    title: str
    knowledge_points: List[str] = Field(default_factory=list)
    recommended_resource_types: List[str] = Field(default_factory=list)
    estimated_hours: Optional[float] = None
    description: str = ""


class LearningPathResponse(BaseModel):
    """学习路径响应"""
    model_config = {"extra": "allow", "from_attributes": True}

    id: int
    user_id: int
    title: str
    stages: List[LearningStage] = Field(default_factory=list)
    completed_stages: List[int] = Field(default_factory=list)
    created_at: Optional[datetime] = None





class QuestionResponse(BaseModel):
    """题目响应 - 兼容选择题、判断题、编程题等不同题型"""
    model_config = {"extra": "allow"}

    question_id: Optional[int] = None
    type: str
    difficulty: Optional[str] = "中等"
    question: str
    options: Optional[List[str]] = None
    answer: Optional[str] = None
    test_cases: Optional[List[dict]] = None
    score: Optional[int] = 10
    explanation: Optional[str] = None



class AnswerSubmitRequest(BaseModel):
    """答案提交请求"""
    question_id: int
    answer: str
    topic: str
    duration_seconds: Optional[int] = Field(None, description="答题耗时（秒）")


class AnswerEvaluation(BaseModel):
    """答案评估"""
    model_config = {"extra": "allow"}

    question_id: int
    correct: bool
    score: int
    max_score: int
    feedback: Optional[str] = None
    code_results: Optional[dict] = None


class SubmitResponse(BaseModel):
    """提交响应"""
    model_config = {"extra": "allow"}

    total_score: int
    max_score: int
    evaluations: List[AnswerEvaluation] = Field(default_factory=list)






class CodeRunRequest(BaseModel):
    """代码运行请求"""
    code: str = Field(..., description="要运行的 Python 代码")
    timeout: Optional[int] = Field(30, description="超时时间（秒）")


class CodeRunResponse(BaseModel):
    """代码运行响应"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None



class ChatMessageResponse(BaseModel):
    """聊天消息响应"""
    id: int
    role: str
    content: str
    time: str


class ChatHistoryResponse(BaseModel):
    """聊天历史响应"""
    messages: List[ChatMessageResponse]


class ProfileListResponse(BaseModel):
    """画像列表响应"""
    model_config = {"from_attributes": True}

    id: int
    profile_name: str
    is_active: bool
    is_archived: bool
    major: Optional[str] = None
    grade: Optional[str] = None
    goal: Optional[str] = None
    knowledge_level: Optional[str] = None
    learning_style: Optional[str] = None
    weakness: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    coding_ability: Optional[str] = None
    updated_at: Optional[datetime] = None


class ProfileCreateRequest(BaseModel):
    """新建画像请求"""
    profile_name: str = Field(..., min_length=1, max_length=100, description="画像名称")


class ProfileUpdateRequest(BaseModel):
    """更新画像请求"""
    profile_name: Optional[str] = Field(None, min_length=1, max_length=100)
    major: Optional[str] = Field(None, max_length=100)
    grade: Optional[str] = Field(None, max_length=50)
    goal: Optional[str] = Field(None, max_length=500)
    learning_style: Optional[str] = Field(None, max_length=100)
    interests: Optional[List[str]] = Field(None)
    coding_ability: Optional[str] = Field(None, max_length=50)



@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前学生画像"""
    log.info(f"学生 {current_user.id} 获取画像")
    
    result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
            StudentProfile.is_archived == False,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        return ProfileResponse(
            id=0,
            user_id=current_user.id,
            major=None,
            grade=None,
            goal=None,
            knowledge_level=None,
            learning_style=None,
            interests=[],
            weakness=[],
            coding_ability=None,
            updated_at=None
        )
    
    return ProfileResponse.model_validate(profile)


# ========== 画像管理 API ==========

@router.get("/profiles", response_model=List[ProfileListResponse])
async def list_profiles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户所有画像"""
    result = await db.execute(
        select(StudentProfile)
        .where(StudentProfile.user_id == current_user.id)
        .order_by(StudentProfile.is_active.desc(), StudentProfile.updated_at.desc())
    )
    return [ProfileListResponse.model_validate(p) for p in result.scalars().all()]


@router.post("/profiles", response_model=ProfileListResponse, status_code=201)
async def create_profile(
    request: ProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新建画像（自动设为活跃画像）"""
    from sqlalchemy import update as sa_update

    # 将当前活跃画像停用
    await db.execute(
        sa_update(StudentProfile)
        .where(StudentProfile.user_id == current_user.id, StudentProfile.is_active == True)
        .values(is_active=False)
    )
    # 创建新画像
    profile = StudentProfile(
        user_id=current_user.id,
        profile_name=request.profile_name,
        is_active=True,
        is_archived=False,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return ProfileListResponse.model_validate(profile)


@router.put("/profiles/{profile_id}", response_model=ProfileListResponse)
async def update_profile(
    profile_id: int,
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新画像信息（允许手动修改：专业/年级/目标/学习风格/兴趣/编程能力）"""
    profile = await db.get(StudentProfile, profile_id)
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="画像不存在")

    # 更新允许手动修改的字段
    if request.profile_name is not None:
        profile.profile_name = request.profile_name
    if request.major is not None:
        profile.major = request.major
    if request.grade is not None:
        profile.grade = request.grade
    if request.goal is not None:
        profile.goal = request.goal
    if request.learning_style is not None:
        profile.learning_style = request.learning_style
    if request.interests is not None:
        profile.interests = request.interests
    if request.coding_ability is not None:
        profile.coding_ability = request.coding_ability

    await db.commit()
    await db.refresh(profile)
    return ProfileListResponse.model_validate(profile)


@router.post("/profiles/{profile_id}/activate")
async def activate_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """设为活跃画像"""
    from sqlalchemy import update as sa_update

    profile = await db.get(StudentProfile, profile_id)
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="画像不存在")
    # 停用所有画像
    await db.execute(
        sa_update(StudentProfile)
        .where(StudentProfile.user_id == current_user.id, StudentProfile.is_active == True)
        .values(is_active=False)
    )
    profile.is_active = True
    await db.commit()
    return {"success": True, "message": f"画像 {profile.profile_name} 已设为活跃"}


@router.post("/profiles/{profile_id}/archive")
async def archive_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """归档画像"""
    profile = await db.get(StudentProfile, profile_id)
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="画像不存在")
    if profile.is_active:
        raise HTTPException(status_code=400, detail="不能归档活跃画像，请先切换到其他画像")
    # 检查是否只剩这一个非归档画像
    count_result = await db.execute(
        select(func.count(StudentProfile.id)).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_archived == False,
        )
    )
    if count_result.scalar() <= 1:
        raise HTTPException(status_code=400, detail="至少保留一个画像，不能归档最后一个")
    profile.is_archived = True
    profile.archived_at = datetime.now()
    await db.commit()
    return {"success": True, "message": f"画像 {profile.profile_name} 已归档"}


@router.post("/profiles/{profile_id}/restore")
async def restore_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """恢复归档画像"""
    profile = await db.get(StudentProfile, profile_id)
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="画像不存在")
    profile.is_archived = False
    profile.archived_at = None
    await db.commit()
    return {"success": True, "message": f"画像 {profile.profile_name} 已恢复"}


# ========== 画像对话历史 API ==========

@router.get("/profiles/{profile_id}/chat-history", response_model=ChatHistoryResponse)
async def get_profile_chat_history(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定画像的对话历史"""
    profile = await db.get(StudentProfile, profile_id)
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="画像不存在")
    result = await db.execute(
        select(ProfileChatMessage)
        .where(ProfileChatMessage.profile_id == profile_id)
        .order_by(ProfileChatMessage.created_at.asc())
        .limit(200)
    )
    records = result.scalars().all()
    messages = [
        ChatMessageResponse(
            id=r.id, role=r.role, content=r.content,
            time=r.created_at.strftime("%H:%M") if r.created_at else ""
        ) for r in records
    ]
    # 空历史时插入欢迎消息
    if not messages:
        messages = [ChatMessageResponse(
            id=0, role="assistant",
            content=f"你好！我是你的学习画像采集助手。请描述你的学习背景、目标、兴趣等，我来帮你构建专属学习画像。",
            time="",
        )]
    return ChatHistoryResponse(messages=messages)


@router.get("/profiles/chat-history/all")
async def get_all_chat_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有画像对话汇总"""
    result = await db.execute(
        select(ProfileChatMessage, StudentProfile.profile_name)
        .join(StudentProfile, ProfileChatMessage.profile_id == StudentProfile.id, isouter=True)
        .where(ProfileChatMessage.user_id == current_user.id)
        .order_by(ProfileChatMessage.created_at.asc())
        .limit(500)
    )
    return [
        {"role": r.role, "content": r.content, "profile_name": name,
         "time": r.created_at.strftime("%H:%M") if r.created_at else ""}
        for r, name in result.all()
    ]


class InitStatusResponse(BaseModel):
    """初始化状态响应"""
    has_profile: bool
    has_path: bool
    needs_workflow: bool


class ChatMessageRequest(BaseModel):
    """发送聊天消息请求"""
    role: str = Field(..., description="角色: user / assistant")
    content: str = Field(..., description="消息内容")


class ChatMessageWithSessionRequest(BaseModel):
    """发送聊天消息请求（带 session_id）"""
    role: str = Field(..., description="角色: user / assistant")
    content: str = Field(..., description="消息内容")
    session_id: Optional[str] = Field(None, description="会话 ID（可选）")
    profile_id: Optional[int] = Field(None, description="画像 ID（可选）")


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    profile_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取聊天历史（默认获取活跃画像的历史）"""
    # 如果没传 profile_id，查活跃画像
    if not profile_id:
        p = (await db.execute(
            select(StudentProfile).where(
                StudentProfile.user_id == current_user.id,
                StudentProfile.is_active == True,
            )
        )).scalar_one_or_none()
        profile_id = p.id if p else None

    query = select(ProfileChatMessage).where(ProfileChatMessage.user_id == current_user.id)
    if profile_id:
        query = query.where(ProfileChatMessage.profile_id == profile_id)

    result = await db.execute(
        query.order_by(ProfileChatMessage.created_at.asc()).limit(200)
    )
    records = result.scalars().all()

    messages = []
    for r in records:
        messages.append(ChatMessageResponse(
            id=r.id,
            role=r.role,
            content=r.content,
            time=r.created_at.strftime("%H:%M") if r.created_at else ""
        ))

    # 始终在最前面添加欢迎消息（如果第一条消息不是欢迎消息）
    welcome_msg = "您好！我是您的学习助手。为了给您提供个性化的学习资源，请告诉我一些关于您学习背景的信息，比如您的专业、年级、学习目标、兴趣方向等。"

    if not messages or messages[0].content != welcome_msg:
        messages.insert(0, ChatMessageResponse(
            id=0,
            role="assistant",
            content=welcome_msg,
            time=""
        ))

    return ChatHistoryResponse(messages=messages)


@router.post("/chat/message")
async def save_chat_message(
    request: ChatMessageWithSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """保存一条聊天消息（带 session_id）"""
    session_id = request.session_id or f"default_{current_user.id}"

    # 如果前端没传 profile_id，查活跃画像
    profile_id = request.profile_id
    if not profile_id:
        prof_result = await db.execute(
            select(StudentProfile).where(
                StudentProfile.user_id == current_user.id,
                StudentProfile.is_active == True,
            )
        )
        prof = prof_result.scalar_one_or_none()
        profile_id = prof.id if prof else None

    msg = ProfileChatMessage(
        user_id=current_user.id,
        session_id=session_id,
        role=request.role,
        content=request.content,
        profile_id=profile_id,
    )
    db.add(msg)
    await db.commit()

    return {"id": msg.id, "message": "ok", "session_id": session_id}


@router.delete("/chat/history")
async def clear_chat_history(
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """清空聊天历史（支持按 session_id 清空）"""
    from sqlalchemy import delete as sa_delete

    # 构建删除条件
    delete_stmt = sa_delete(ProfileChatMessage).where(
        ProfileChatMessage.user_id == current_user.id
    )

    # 如果提供了 session_id，则按 session_id 过滤
    if session_id:
        delete_stmt = delete_stmt.where(
            ProfileChatMessage.session_id == session_id
        )

    await db.execute(delete_stmt)
    await db.commit()

    return {"message": "聊天记录已清空", "session_id": session_id}


@router.get("/init-status", response_model=InitStatusResponse)
async def get_init_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """检查学生初始化状态：是否有画像、是否有学习路径"""
    # 查活跃画像
    profile_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
            StudentProfile.is_archived == False,
        )
    )
    profile = profile_result.scalar_one_or_none()

    # 查该画像的学习路径
    path_query = select(LearningPath).where(LearningPath.user_id == current_user.id)
    if profile:
        path_query = path_query.where(LearningPath.profile_id == profile.id)
    path_result = await db.execute(
        path_query.order_by(LearningPath.created_at.desc()).limit(1)
    )
    path = path_result.scalar_one_or_none()

    has_profile = profile is not None and profile.major is not None
    has_path = path is not None

    return InitStatusResponse(
        has_profile=has_profile,
        has_path=has_path,
        needs_workflow=has_profile and not has_path
    )


@router.post("/learning-path/generate", response_model=LearningPathResponse)
async def generate_learning_path(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成学习路径"""
    log.info(f"学生 {current_user.id} 开始生成学习路径")
    
    path_agent = LearningPathAgent(db)
    path_data = await path_agent.run(current_user.id)

    # 获取活跃画像
    gp_prof_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
        )
    )
    gp_prof = gp_prof_result.scalar_one_or_none()
    gp_path_query = select(LearningPath).where(LearningPath.user_id == current_user.id)
    if gp_prof:
        gp_path_query = gp_path_query.where(LearningPath.profile_id == gp_prof.id)
    result = await db.execute(gp_path_query)
    path = result.scalar_one_or_none()
    
    return LearningPathResponse.model_validate(path)


@router.get("/learning-path", response_model=Optional[LearningPathResponse])
async def get_learning_path(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取学习路径（按当前活跃画像）"""
    log.info(f"学生 {current_user.id} 获取学习路径")

    # 查活跃画像
    profile_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
        )
    )
    profile = profile_result.scalar_one_or_none()

    path_query = select(LearningPath).where(LearningPath.user_id == current_user.id)
    if profile:
        path_query = path_query.where(LearningPath.profile_id == profile.id)
    result = await db.execute(
        path_query.order_by(LearningPath.created_at.desc()).limit(1)
    )
    path = result.scalar_one_or_none()

    if not path:
        return None

    # 确保 completed_stages 不为 None
    if path.completed_stages is None:
        path.completed_stages = []

    return LearningPathResponse.model_validate(path)


@router.get("/resources")
async def get_resources(
    stage_id: Optional[int] = Query(None, description="按阶段 ID 过滤资源"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """纯读取接口 — 直接从 DB 返回学习资源，不触发任何 LLM 调用"""
    log.info(f"学生 {current_user.id} 读取学习资源 stage_id={stage_id}")
    from app.models import LearningResource

    # 获取活跃画像 profile_id
    profile_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
        )
    )
    active_profile = profile_result.scalar_one_or_none()
    profile_id = active_profile.id if active_profile else None

    # 两步查询：先查 ID，再取 content（避免 sort_buffer_size 溢出）
    query = select(
        LearningResource.resource_type,
        func.max(LearningResource.id).label("max_id")
    ).where(LearningResource.user_id == current_user.id)
    if profile_id:
        query = query.where(LearningResource.profile_id == profile_id)
    else:
        query = query.where(LearningResource.profile_id.is_(None))

    if stage_id is not None:
        query = query.where(LearningResource.stage_id == stage_id)

    id_result = await db.execute(query.group_by(LearningResource.resource_type))
    latest_ids = [row.max_id for row in id_result.all()]

    resources: dict = {}
    if latest_ids:
        content_result = await db.execute(
            select(LearningResource).where(LearningResource.id.in_(latest_ids))
        )
        for row in content_result.scalars().all():
            # 统一 content 为 dict：兼容历史保存的 JSON 字符串
            raw = row.content
            if isinstance(raw, str):
                try:
                    import json as _json
                    parsed = _json.loads(raw)
                    if isinstance(parsed, (dict, list)):
                        raw = parsed
                    else:
                        raw = {"content": raw}
                except Exception:
                    raw = {"content": raw}
            elif raw is None:
                raw = {}
            resources[row.resource_type] = raw

    result = {
        "document": resources.get("document"),
        "questions": resources.get("question"),
        "code": resources.get("code"),
        "video_script": resources.get("video_script"),
        "mindmap": resources.get("mindmap"),
        "mindmap_html": resources.get("mindmap_html"),
        "knowledge_graph": resources.get("knowledge_graph"),
        "reading_material": resources.get("reading_material"),
        "glossary": resources.get("glossary"),
        "knowledge_link": resources.get("knowledge_link"),
        "summary": resources.get("summary"),
        "ppt_video": resources.get("ppt_video"),
    }

    # ── 质量门控过滤 ──────────────────────────────────────
    from app.core.quality_thresholds import quality_thresholds
    filtered_resources = []
    # 资源类型映射：response key → 实际 resource_type（用于查阈值）
    type_key_map = {
        "document": "document", "questions": "question", "code": "code",
        "mindmap": "mindmap", "reading_material": "reading_material",
        "glossary": "glossary", "knowledge_link": "knowledge_link",
        "summary": "summary", "ppt_video": "ppt_video",
        "video_script": "video_script", "mindmap_html": "mindmap",
        "mindmap_markdown": "mindmap", "knowledge_graph": "knowledge_link",
    }
    for key in list(result.keys()):
        content = result[key]
        if not content or not isinstance(content, dict):
            continue
        res_type = type_key_map.get(key, key)
        quality = content.get("quality_score", {})
        score = quality.get("overall_score")
        if score is None:
            # 未评估的资源：根据阈值决定是否展示
            # 如果阈值 > 0，未评估资源不展示（需要评估后才可见）
            # 如果阈值 == 0，未评估资源正常展示
            threshold = quality_thresholds.get_threshold(res_type)
            if threshold > 0:
                result[key] = None
                filtered_resources.append({
                    "type": res_type,
                    "display_name": key,
                    "reason": "not_evaluated",
                    "score": None,
                    "threshold": threshold,
                })
            continue
        threshold = quality_thresholds.get_threshold(res_type)
        if score < threshold:
            result[key] = None
            filtered_resources.append({
                "type": res_type,
                "display_name": key,
                "reason": "quality_below_threshold",
                "score": score,
                "threshold": threshold,
            })

    result["filtered_resources"] = filtered_resources

    return result


# ── 单资源重新生成 ──────────────────────────────────────

# 资源类型 → Agent 生成函数映射
_RESOURCE_GENERATORS = {
    "document": "_gen_document",
    "mindmap": "_gen_mindmap",
    "code": "_gen_code",
    "question": "_gen_question",
    "reading_material": "_gen_reading_material",
    "glossary": "_gen_glossary",
    "knowledge_link": "_gen_knowledge_link",
    "summary": "_gen_summary",
    "ppt_video": "_gen_ppt_video",
}


async def _generate_and_evaluate(db, user_id, stage_id, stage_topic, resource_type, profile_id=None):
    """为指定用户生成单种资源并评估质量，返回 (content, quality_score)"""
    from app.models import LearningResource
    from app.models.upsert import upsert as mysql_upsert
    from app.agents.resource_quality_agent import ResourceQualityAgent

    gen_func = _RESOURCE_GENERATORS.get(resource_type)
    if not gen_func:
        raise ValueError(f"不支持的资源类型: {resource_type}")

    content = await globals()[gen_func](db, user_id, stage_topic, stage_id)
    # 统一 content 为 dict：兼容 Agent 返回字符串 / DB 读取的历史 JSON 字符串
    if isinstance(content, str):
        try:
            import json as _json
            _parsed = _json.loads(content)
            content = _parsed if isinstance(_parsed, (dict, list)) else {"content": content}
        except Exception:
            content = {"content": content}
    elif content is None:
        content = {}

    resource_values = {
        "user_id": user_id, "profile_id": profile_id, "stage_id": stage_id,
        "resource_type": resource_type, "topic": stage_topic, "content": content,
    }
    await mysql_upsert(db, LearningResource.__table__, values=resource_values)
    await db.commit()

    quality_agent = ResourceQualityAgent(db)
    quality = await quality_agent.run(
        topic=stage_topic, resource_type=resource_type,
        content=content, user_id=user_id,
    )
    # content 已是 dict，直接拷贝并追加质量评分
    updated_content = dict(content) if isinstance(content, dict) else {"content": content}
    updated_content["quality_score"] = quality
    resource_values["content"] = updated_content
    await mysql_upsert(db, LearningResource.__table__, values=resource_values)
    await db.commit()

    return updated_content, quality


async def _gen_document(db, user_id, topic, stage_id):
    from app.agents.document_agent import DocumentAgent
    return await DocumentAgent(db).run(topic, user_id=user_id)

async def _gen_mindmap(db, user_id, topic, stage_id):
    from app.agents.mindmap_agent import MindmapAgent
    result = await MindmapAgent(db).run(topic, user_id=user_id)
    return {"mindmap_markdown": result.get("mindmap_markdown", ""), "mindmap_html": result.get("mindmap_html", "")} if isinstance(result, dict) else result

async def _gen_code(db, user_id, topic, stage_id):
    from app.agents.code_agent import CodeAgent
    return await CodeAgent(db).run(topic, user_id=user_id)

async def _gen_question(db, user_id, topic, stage_id):
    from app.agents.question_agent import QuestionAgent
    return await QuestionAgent(db).run(topic, user_id=user_id)

async def _gen_reading_material(db, user_id, topic, stage_id):
    from app.agents.reading_material_agent import ReadingMaterialAgent
    return await ReadingMaterialAgent(db).run(topic, user_id=user_id)

async def _gen_glossary(db, user_id, topic, stage_id):
    from app.agents.glossary_agent import GlossaryAgent
    return await GlossaryAgent(db).run(topic, user_id=user_id)

async def _gen_knowledge_link(db, user_id, topic, stage_id):
    result = await KnowledgeGraphAgent(db, scope="stage").run(topic, user_id=user_id)
    return result if isinstance(result, dict) else {"title": "知识点关联图", "nodes": [], "edges": []}

async def _gen_summary(db, user_id, topic, stage_id):
    from app.agents.summary_agent import SummaryAgent
    return await SummaryAgent(db).run(topic, user_id=user_id)

async def _gen_ppt_video(db, user_id, topic, stage_id):
    from app.agents.ppt_video_agent import PptVideoAgent
    result = await PptVideoAgent(db).run(topic=topic, stage_id=stage_id, user_id=user_id)
    return result if isinstance(result, dict) else {}


class RegenerateRequest(BaseModel):
    stage_id: int = Field(..., description="阶段 ID")


@router.post("/resources/{resource_type}/regenerate")
async def regenerate_resource(
    resource_type: str,
    request: RegenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """重新生成单种资源（删旧生新 + 重新评估）"""
    if resource_type not in _RESOURCE_GENERATORS:
        raise HTTPException(status_code=400, detail=f"不支持的资源类型: {resource_type}")

    # 获取活跃画像 profile_id
    profile_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
        )
    )
    active_profile = profile_result.scalar_one_or_none()
    profile_id = active_profile.id if active_profile else None

    from app.models import LearningPath
    path_query = select(LearningPath).where(LearningPath.user_id == current_user.id)
    if profile_id:
        path_query = path_query.where(LearningPath.profile_id == profile_id)
    path_result = await db.execute(path_query)
    path = path_result.scalar_one_or_none()
    if not path or not path.stages:
        raise HTTPException(status_code=404, detail="学习路径不存在")

    stage = next((s for s in path.stages if s.get("stage_id") == request.stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail=f"阶段 {request.stage_id} 不存在")

    kps = stage.get("knowledge_points", [])
    raw_kps = [kp.get("name", "") if isinstance(kp, dict) else str(kp) for kp in kps]
    # 限制知识点数量和长度，避免 topic 过长
    raw_kps = [kp[:20] for kp in raw_kps[:5]]
    stage_topic = "、".join(raw_kps) or stage.get("title", "")
    if len(stage_topic) > 80:
        stage_topic = "、".join(raw_kps[:3]) or stage.get("title", "")

    from app.models import LearningResource
    delete_query = LearningResource.__table__.delete().where(
        LearningResource.user_id == current_user.id,
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
                LearningRecord.user_id == current_user.id,
                LearningRecord.resource_type == "question",
            )
        )

    await db.commit()

    try:
        content, quality = await _generate_and_evaluate(
            db, current_user.id, request.stage_id, stage_topic, resource_type,
            profile_id=profile_id,
        )
        return {"success": True, "content": content, "quality_score": quality}
    except Exception as e:
        log.error(f"重新生成 {resource_type} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重新生成失败: {str(e)}")




@router.post("/question/submit", response_model=SubmitResponse)
async def submit_answer(
    request: AnswerSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交答案并评分，自动触发学习评估"""
    log.info(f"学生 {current_user.id} 提交答案，题目ID: {request.question_id}")

    # 直接从 DB 查找该用户当前画像的题目
    from sqlalchemy import select as sa_select
    from app.models import LearningResource
    q_prof_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
        )
    )
    q_prof = q_prof_result.scalar_one_or_none()
    q_query = sa_select(LearningResource).where(
        LearningResource.user_id == current_user.id,
        LearningResource.resource_type == "question"
    )
    if q_prof:
        q_query = q_query.where(LearningResource.profile_id == q_prof.id)
    result = await db.execute(q_query.order_by(LearningResource.created_at.desc()))
    records = result.scalars().all()

    question = None
    for record in records:
        content = record.content if isinstance(record.content, dict) else {}
        questions_list = content.get("questions", [])
        for q in questions_list:
            if q.get("question_id") == request.question_id:
                question = q
                break
        if question:
            break

    if not question:
        raise HTTPException(status_code=404, detail=f"题目 {request.question_id} 不存在，请先重新生成题目")

    evaluation = await evaluate_answer(request.answer, question)

    # 从题目数据中提取考察的知识点
    kp = question.get("knowledge_point", "") or request.topic or "通用"

    learning_record = LearningRecord(
        user_id=current_user.id,
        resource_type="question",
        resource_id=request.question_id,
        correct=evaluation.correct,
        score=evaluation.score,
        duration_seconds=getattr(request, 'duration_seconds', 0) or 0,
        behavior_data={"topic": kp, "answer": request.answer, "knowledge_point": kp}
    )
    db.add(learning_record)
    await db.commit()

    # ============ 延迟触发学习评估（最后一道题提交后等几秒再评估） ============
    _schedule_eval_delay(current_user.id)

    return SubmitResponse(
        total_score=evaluation.score,
        max_score=evaluation.max_score,
        evaluations=[evaluation]
    )


@router.get("/question/answers")
async def get_question_answers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户的历史答题记录（用于刷新后恢复状态）"""
    from sqlalchemy import select as sa_select

    result = await db.execute(
        sa_select(LearningRecord).where(
            LearningRecord.user_id == current_user.id,
            LearningRecord.resource_type == "question"
        ).order_by(LearningRecord.created_at.desc())
    )
    records = result.scalars().all()

    # 同一题只保留最新一次作答
    seen = {}
    for r in records:
        qid = r.resource_id
        if qid and qid not in seen:
            seen[qid] = {
                "question_id": qid,
                "answer": r.behavior_data.get("answer", "") if r.behavior_data else "",
                "correct": r.correct,
                "score": r.score,
                "submitted_at": r.created_at.isoformat() if r.created_at else None,
            }

    return {"answers": list(seen.values())}


# 评估触发阈值配置
EVALUATION_TRIGGER_COUNT = 15  # 累积15条学习行为记录触发评估
EVALUATION_TRIGGER_ACCURACY_DROP = 0.2  # 正确率下降超过20%触发
EVALUATION_TRIGGER_STUDY_TIME = 3600  # 累计学习时长1小时触发


async def _eval_delay_callback(user_id: int):
    """延迟评估回调：等待几秒后执行评估"""
    await asyncio.sleep(EVAL_DELAY_SECONDS)
    _eval_delay_tasks.pop(user_id, None)
    if user_id in _evaluating_users:
        return
    from app.models import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await _try_trigger_evaluation(user_id, db)


def _schedule_eval_delay(user_id: int):
    """为用户调度延迟评估：取消旧任务，创建新任务"""
    if user_id in _eval_delay_tasks:
        _eval_delay_tasks[user_id].cancel()
    _eval_delay_tasks[user_id] = asyncio.create_task(_eval_delay_callback(user_id))


async def _try_trigger_evaluation(user_id: int, db: AsyncSession, force: bool = False):
    """尝试触发学习评估

    Args:
        user_id: 用户 ID
        db: 数据库 session
        force: 强制触发（阶段完成时使用），跳过阈值判断
    """
    # 防止同一用户并发触发多次评估
    if user_id in _evaluating_users:
        log.debug(f"学生 {user_id} 已有评估在进行中，跳过")
        return None
    _evaluating_users.add(user_id)
    try:
        from sqlalchemy import select as sa_select, func as sa_func
        from app.models import EvaluationReport

        # 查询最近一次评估的时间
        last_eval_result = await db.execute(
            select(EvaluationReport).where(
                EvaluationReport.user_id == user_id
            ).order_by(EvaluationReport.created_at.desc()).limit(1)
        )
        last_eval = last_eval_result.scalar_one_or_none()

        # 统计所有类型的学习行为记录（不只是答题）
        LEARNING_EVENT_TYPES = ("question", "resource_view", "code_execute", "stage_complete")

        if last_eval:
            new_records_result = await db.execute(
                sa_select(sa_func.count(LearningRecord.id)).where(
                    LearningRecord.user_id == user_id,
                    LearningRecord.resource_type.in_(LEARNING_EVENT_TYPES),
                    LearningRecord.created_at > last_eval.created_at
                )
            )
            new_records_count = new_records_result.scalar() or 0
        else:
            total_result = await db.execute(
                sa_select(sa_func.count(LearningRecord.id)).where(
                    LearningRecord.user_id == user_id,
                    LearningRecord.resource_type.in_(LEARNING_EVENT_TYPES),
                )
            )
            new_records_count = total_result.scalar() or 0

        # 强制触发（阶段完成时）直接评估
        if force:
            should_trigger = new_records_count > 0
            if not should_trigger:
                log.debug(f"学生 {user_id} 阶段完成但无新学习记录，跳过评估")
                return None
            log.info(f"学生 {user_id} 阶段完成，强制触发评估")
        else:
            # 触发条件1：累积学习行为达到阈值
            should_trigger = new_records_count >= EVALUATION_TRIGGER_COUNT

            # 触发条件2：正确率大幅下降（答题记录）
            if not should_trigger and new_records_count >= 3:
                recent_records_result = await db.execute(
                    select(LearningRecord).where(
                        LearningRecord.user_id == user_id,
                        LearningRecord.resource_type == "question"
                    ).order_by(LearningRecord.created_at.desc()).limit(5)
                )
                recent_records = recent_records_result.scalars().all()

                if len(recent_records) >= 3:
                    recent_accuracy = sum(1 for r in recent_records if r.correct) / len(recent_records)
                    if last_eval and last_eval.accuracy_rate is not None:
                        if last_eval.accuracy_rate - recent_accuracy >= EVALUATION_TRIGGER_ACCURACY_DROP:
                            should_trigger = True
                            log.info(f"学生 {user_id} 正确率下降 {EVALUATION_TRIGGER_ACCURACY_DROP*100}%，触发评估")

            # 触发条件3：累计学习时长达到阈值（1小时）
            if not should_trigger:
                time_result = await db.execute(
                    sa_select(sa_func.coalesce(sa_func.sum(LearningRecord.duration_seconds), 0)).where(
                        LearningRecord.user_id == user_id,
                        LearningRecord.resource_type.in_(LEARNING_EVENT_TYPES),
                    )
                )
                total_seconds = time_result.scalar() or 0
                if total_seconds >= EVALUATION_TRIGGER_STUDY_TIME:
                    should_trigger = True
                    log.info(f"学生 {user_id} 累计学习 {total_seconds//60} 分钟，触发评估")

        if should_trigger:
            if force:
                trigger_reason = "阶段完成（强制）"
            elif new_records_count >= EVALUATION_TRIGGER_COUNT:
                trigger_reason = f"累积 {new_records_count} 条学习行为"
            else:
                trigger_reason = "正确率下降或学习时长达标"
            log.info(f"学生 {user_id} 触发评估：{trigger_reason}")

            # 执行评估
            from app.agents.evaluation_agent import create_evaluation_agent
            evaluation_agent = create_evaluation_agent(db)
            eval_result = await evaluation_agent.run(user_id)

            # 发送WebSocket通知
            from app.core.websocket_manager import notification_manager
            await notification_manager.send_evaluation_result(user_id, eval_result)

            # 答题触发时不做路径更新，只提示阶段完成后再优化
            if eval_result.get("should_update_path"):
                await notification_manager.send_notification(
                    user_id=user_id,
                    notification_type="learning_progress",
                    data={"path_updated": False},
                    title="学习评估",
                    content="答题已记录，继续加油！完成本阶段后系统会为你评估学习效果并优化路径。"
                )

            log.info(f"学生 {user_id} 自动评估完成，等级: {eval_result.get('overall_grade')}")
            return eval_result
        else:
            log.debug(f"学生 {user_id} 新增 {new_records_count} 条记录，未达到评估阈值({EVALUATION_TRIGGER_COUNT})")
            return None

    except Exception as e:
        log.error(f"自动触发评估失败: {e}")
        # 评估失败不影响主流程
        return None
    finally:
        _evaluating_users.discard(user_id)





@router.post("/code/run", response_model=CodeRunResponse)
async def run_code(
    request: CodeRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """运行代码（沙箱环境）"""
    log.info(f"学生 {current_user.id} 开始运行代码")

    code_agent = CodeAgent()
    result = await code_agent.execute_code(request.code, request.timeout)

    # 记录代码执行事件（独立 try，不影响主流程）
    try:
        from app.models import LearningRecord
        db.add(LearningRecord(
            user_id=current_user.id,
            resource_type="code_execute",
            correct=result.get("success"),
            behavior_data={"code_length": len(request.code), "success": result.get("success")},
        ))
        await db.commit()
    except Exception as e:
        log.warning(f"代码执行事件记录失败: {e}")
        await db.rollback()

    return CodeRunResponse(**result)


class KnowledgePoint(BaseModel):
    """知识点掌握情况"""
    model_config = {"extra": "allow"}

    topic: str
    score: Optional[int] = 0
    total: Optional[int] = 0
    mastery: Optional[float] = 0.0
    status: Optional[str] = "未学习"


class Analysis(BaseModel):
    """分析结果"""
    model_config = {"extra": "allow"}

    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    """评估响应"""
    model_config = {"extra": "allow"}

    overall_grade: Optional[str] = "N/A"
    total_score: Optional[int] = 0
    total_attempts: Optional[int] = 0
    accuracy_rate: Optional[float] = 0.0
    mastery_level: Optional[float] = 0.0
    analysis: Optional[Analysis] = None
    knowledge_points: Optional[List[KnowledgePoint]] = Field(default_factory=list)
    report: Optional[str] = ""
    should_update_path: Optional[bool] = False


@router.post("/evaluation/run", response_model=EvaluationResponse)
async def run_evaluation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """执行学生评估"""
    log.info(f"学生 {current_user.id} 开始执行评估")
    
    evaluation_agent = create_evaluation_agent(db)
    result = await evaluation_agent.run(current_user.id)
    
    return EvaluationResponse(**result)


@router.get("/evaluation/report", response_model=EvaluationResponse)
async def get_evaluation_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取评估报告（先查库，有则返回并重算统计；无则执行评估）"""
    log.info(f"学生 {current_user.id} 获取评估报告")

    # 先查库获取最新报告
    from app.models import EvaluationReport
    result = await db.execute(
        select(EvaluationReport).where(
            EvaluationReport.user_id == current_user.id
        ).order_by(EvaluationReport.created_at.desc()).limit(1)
    )
    report = result.scalar_one_or_none()

    # 判断是否需要重新评估：报告对应的已完成阶段数与当前不一致则重新评估
    should_re_evaluate = False
    from app.models import LearningPath
    path_result = await db.execute(
        select(LearningPath).where(LearningPath.user_id == current_user.id)
        .order_by(LearningPath.created_at.desc()).limit(1)
    )
    path = path_result.scalar_one_or_none()
    current_completed_count = len(path.completed_stages) if path and path.completed_stages else 0
    report_completed_count = 0
    if report and report.report_data:
        report_completed_count = report.report_data.get("_completed_stages_count", 0)
    if report and current_completed_count != report_completed_count:
        should_re_evaluate = True
        log.info(f"学生 {current_user.id} 已完成阶段数变化（{report_completed_count}→{current_completed_count}），重新评估")

    if report and report.report_data and not should_re_evaluate:
        log.info(f"从数据库返回评估报告，用户 {current_user.id}")
        report_data = dict(report.report_data)

        # 重算统计：按 resource_id 去重，同一题目只取最高分
        from app.models import LearningRecord
        recs_result = await db.execute(
            select(LearningRecord).where(
                LearningRecord.user_id == current_user.id,
                LearningRecord.resource_type == "question"
            ).order_by(LearningRecord.created_at.desc())
        )
        records = recs_result.scalars().all()

        best_by_rid: dict = {}
        for r in records:
            rid = r.resource_id
            if rid is None:
                continue
            if rid not in best_by_rid or (r.score or 0) > (best_by_rid[rid].score or 0):
                best_by_rid[rid] = r

        deduped = list(best_by_rid.values())
        total_score = sum(r.score for r in deduped if r.score is not None)
        total_attempts = len(deduped)
        correct_count = sum(1 for r in deduped if r.correct)
        accuracy_rate = correct_count / total_attempts if total_attempts > 0 else 0.0

        # 更新报告统计字段
        report_data["total_score"] = total_score
        report_data["total_attempts"] = total_attempts
        report_data["accuracy_rate"] = accuracy_rate

        # 用真实答题数据重新按知识点分组计算，确保与最新答题记录一致
        kp_data: dict = {}
        for r in records:
            behavior = r.behavior_data if isinstance(r.behavior_data, dict) else {}
            kp = behavior.get("knowledge_point") or behavior.get("topic") or "通用"
            # 按 resource_id 去重，同一题目只取最高分
            rid = r.resource_id
            if rid is None:
                continue
            if rid not in kp_data:
                kp_data[rid] = {"kp": kp, "score": r.score or 0, "correct": r.correct}
            elif (r.score or 0) > kp_data[rid]["score"]:
                kp_data[rid] = {"kp": kp, "score": r.score or 0, "correct": r.correct}

        kp_grouped: dict = {}
        for rid, info in kp_data.items():
            kp = info["kp"]
            if kp not in kp_grouped:
                kp_grouped[kp] = {"total": 0, "correct": 0, "score": 0, "max_score": 0}
            kp_grouped[kp]["total"] += 1
            kp_grouped[kp]["max_score"] += 10
            if info["correct"]:
                kp_grouped[kp]["correct"] += 1
            kp_grouped[kp]["score"] += info["score"]

        new_kps = []
        for kp_name, data in kp_grouped.items():
            mastery = data["correct"] / data["total"] if data["total"] > 0 else 0.0
            if mastery >= 0.8:
                status = "掌握"
            elif mastery >= 0.3:
                status = "学习中"
            else:
                status = "薄弱"
            new_kps.append({
                "topic": kp_name,
                "score": min(data["score"], data["max_score"]),
                "total": data["max_score"],
                "mastery": round(mastery, 2),
                "status": status,
            })

        # 补充未考查的知识点
        existing_kp_names = {kp["topic"] for kp in new_kps}
        old_kps = report_data.get("knowledge_points", [])
        for old_kp in old_kps:
            if old_kp.get("topic") not in existing_kp_names:
                new_kps.append({
                    "topic": old_kp["topic"],
                    "score": 0,
                    "total": 10,
                    "mastery": 0.0,
                    "status": "未考查",
                })

        report_data["knowledge_points"] = new_kps

        # 回写数据库
        report.total_score = total_score
        report.accuracy_rate = accuracy_rate
        report.report_data = report_data
        await db.commit()

        return EvaluationResponse(**report_data)

    # 没有报告则执行评估
    evaluation_agent = create_evaluation_agent(db)
    eval_result = await evaluation_agent.run(current_user.id)

    return EvaluationResponse(**eval_result)


class WorkflowStartRequest(BaseModel):
    """工作流启动请求"""
    pass


class WorkflowStartResponse(BaseModel):
    """工作流启动响应"""
    session_id: str
    message: str


class WorkflowStateResponse(BaseModel):
    """工作流状态响应"""
    session_id: str
    current_step: str
    progress: float
    steps_history: List[dict]
    error: Optional[str]
    completed: bool


@router.post("/learn/start", response_model=WorkflowStartResponse)
async def start_learning(
    request: WorkflowStartRequest = WorkflowStartRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """启动学习工作流"""
    log.info(f"学生 {current_user.id} 启动学习工作流")

    session_id = await workflow_manager.start_workflow(current_user.id, db)
    
    return WorkflowStartResponse(
        session_id=session_id,
        message="学习工作流已启动"
    )


@router.websocket("/ws/workflow")
async def workflow_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="认证 token"),
):
    """工作流 WebSocket 端点 — 替代 SSE，支持双向通信

    客户端发送:
        {"type": "start", "session_id": "xxx"}
        {"type": "resume", "session_id": "xxx"}

    服务端推送:
        {"type": "connected", "message": "连接成功"}
        {"type": "step", "data": {current_step, progress, ...}}
        {"type": "complete", "message": "工作流完成"}
        {"type": "error", "message": "错误信息"}
    """
    from app.core.security import decode_token

    # 认证
    try:
        payload = decode_token(token)
        if payload is None:
            await websocket.close(code=4001)
            return
        user_id = int(payload.get("sub", 0))
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    await websocket.send_json({"type": "connected", "message": "连接成功"})
    log.info(f"工作流 WebSocket 连接: user_id={user_id}")

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            session_id = data.get("session_id", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if not session_id:
                await websocket.send_json({"type": "error", "message": "缺少 session_id"})
                continue

            # 从数据库获取 db session
            from app.models import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                try:
                    # 设置进度回调：步骤内发送中间进度到前端
                    async def _progress_cb(msg):
                        try:
                            await websocket.send_json(msg)
                        except Exception:
                            pass
                    workflow_manager.set_progress_callback(user_id, _progress_cb)

                    if msg_type == "resume":
                        workflow_gen = workflow_manager.resume_workflow(session_id, db)
                    else:
                        workflow_gen = workflow_manager.run_workflow(session_id, db)

                    async for state in workflow_gen:
                        state_dict = state.dict()
                        state_dict.pop("db", None)
                        try:
                            await websocket.send_json({"type": "step", "data": state_dict})
                        except Exception:
                            log.warning("工作流 step 事件发送失败（WebSocket 可能已断开）")

                    workflow_manager.clear_progress_callback(user_id)
                    try:
                        await websocket.send_json({"type": "complete", "message": "工作流完成"})
                    except Exception:
                        log.warning("工作流 complete 事件发送失败（WebSocket 已断开）")
                    log.info(f"工作流完成: user_id={user_id}, session={session_id}")

                except Exception as e:
                    log.error(f"工作流执行失败: {e}")
                    await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        log.info(f"工作流 WebSocket 断开: user_id={user_id}")
    except Exception as e:
        log.error(f"工作流 WebSocket 异常: {e}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


@router.get("/learn/state/{session_id}", response_model=WorkflowStateResponse)
async def get_workflow_state(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取工作流状态"""
    log.info(f"学生 {current_user.id} 获取工作流状态: {session_id}")
    
    state = await workflow_manager.get_state(session_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    return WorkflowStateResponse(
        session_id=state.session_id,
        current_step=state.current_step,
        progress=state.progress,
        steps_history=state.steps_history,
        error=state.error,
        completed=state.progress >= 1.0
    )


@router.delete("/learn/cancel/{session_id}")
async def cancel_learning(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """取消学习工作流"""
    log.info(f"学生 {current_user.id} 取消学习工作流: {session_id}")
    
    await workflow_manager.cancel_workflow(session_id)
    
    return {"message": "工作流已取消"}


# ==================== 阶段资源异步生成 ====================

# 保活后台任务引用，防止被垃圾回收
_background_stage_tasks: set = set()


async def generate_all_stage_resources(user_id: int):
    """学习路径生成后调用：只生成当前阶段的资源

    后续阶段等学生到达时再按需生成。
    """
    from app.models import AsyncSessionLocal

    # 获取学习路径（按活跃画像）
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select as sa_select
        from app.models import StudentProfile
        prof_result = await db.execute(
            sa_select(StudentProfile).where(
                StudentProfile.user_id == user_id,
                StudentProfile.is_active == True,
            )
        )
        prof = prof_result.scalar_one_or_none()
        path_query = select(LearningPath).where(LearningPath.user_id == user_id)
        if prof:
            path_query = path_query.where(LearningPath.profile_id == prof.id)
        result = await db.execute(path_query)
        path = result.scalar_one_or_none()

    if not path or not path.stages:
        return

    stages = path.stages
    completed = path.completed_stages or []

    # 找到当前阶段（第一个未完成的阶段）
    current_index = 0
    for i, stage in enumerate(stages):
        if stage.get("stage_id") not in completed:
            current_index = i
            break

    # 只生成当前阶段资源
    log.info(f"为用户 {user_id} 生成当前阶段 {current_index + 1} 资源")
    await _generate_one_stage(user_id, stages[current_index])
    log.info(f"阶段 {current_index + 1} 资源生成完毕")



async def _generate_one_stage(user_id: int, stage: dict, force: bool = False,
                             progress_base: int = 0, progress_range: int = 100):
    """为单个阶段生成资源（文档/思维导图/代码）

    Args:
        progress_base: 进度基准百分比（用于在更大流程中映射进度）
        progress_range: 进度区间宽度（百分比）
    """
    from app.models import AsyncSessionLocal, LearningResource
    from app.core.websocket_manager import notification_manager

    stage_id = stage.get("stage_id")

    # 互斥锁：防止同一用户同一阶段并发生成
    lock_key = f"{user_id}_{stage_id}"
    if lock_key in _stage_gen_locks:
        log.info(f"阶段 {stage_id} 正在生成中，跳过重复调用")
        return
    _stage_gen_locks[lock_key] = asyncio.Lock()
    try:
        async with _stage_gen_locks[lock_key]:
            await _do_generate_one_stage(user_id, stage, force=force,
                                         progress_base=progress_base, progress_range=progress_range)
    finally:
        _stage_gen_locks.pop(lock_key, None)


async def _do_generate_one_stage(user_id: int, stage: dict, force: bool = False,
                                 progress_base: int = 0, progress_range: int = 100):
    """实际的资源生成逻辑"""
    from app.models import AsyncSessionLocal, LearningResource
    from app.core.websocket_manager import notification_manager

    stage_id = stage.get("stage_id")
    kps = stage.get("knowledge_points", [])
    # knowledge_points 可能是字符串列表或字典列表
    if kps and isinstance(kps[0], dict):
        raw_kps = [kp.get("name", "") for kp in kps]
    else:
        raw_kps = [str(kp) for kp in kps]
    # 限制知识点数量和长度，避免 topic 过长
    raw_kps = [kp[:20] for kp in raw_kps[:5]]
    stage_topic = "、".join(raw_kps) or stage.get("title", "")
    if len(stage_topic) > 80:
        stage_topic = "、".join(raw_kps[:3]) or stage.get("title", "")
    # 固定生成全部资源类型，名称与主工作流对齐
    resource_steps = [
        ("document", "文档生成 Agent · 生成学习文档"),
        ("ppt_video", "PPT 视频 Agent · 生成教学视频"),
        ("mindmap", "思维导图 Agent · 生成思维导图"),
        ("question", "题库生成 Agent · 生成练习题目"),
        ("code", "代码实操 Agent · 生成代码示例"),
        ("reading_material", "拓展阅读 Agent · 生成阅读材料"),
        ("glossary", "术语词汇 Agent · 生成词汇卡片"),
        ("knowledge_link", "知识图谱 Agent · 生成知识点关联图"),
        ("summary", "学习总结 Agent · 生成总结报告"),
    ]

    # 获取活跃 profile_id + 检查缺失的资源类型（同一个 session）
    async with AsyncSessionLocal() as db:
        prof_result = await db.execute(
            select(StudentProfile).where(
                StudentProfile.user_id == user_id,
                StudentProfile.is_active == True,
            )
        )
        prof = prof_result.scalar_one_or_none()
        res_profile_id = prof.id if prof else None

        # 查询该阶段已有的资源类型
        existing_types_query = select(LearningResource.resource_type).where(
            LearningResource.user_id == user_id,
            LearningResource.stage_id == stage_id,
        )
        if res_profile_id:
            existing_types_query = existing_types_query.where(LearningResource.profile_id == res_profile_id)
        existing_types_result = await db.execute(existing_types_query)
        existing_types = {row[0] for row in existing_types_result.all()}

    # 过滤掉已存在的类型，只生成缺失的（force=True 时全部重新生成）
    if not force:
        needed_types = [t for t in resource_steps if t[0] not in existing_types]
        if not needed_types:
            log.info(f"阶段 {stage_id} 所有资源已存在（profile_id={res_profile_id}），跳过生成")
            return
        resource_steps = needed_types
        log.info(f"阶段 {stage_id} 缺失资源类型: {[t[0] for t in needed_types]}，开始生成")
    else:
        log.info(f"阶段 {stage_id} 强制重新生成全部资源（profile_id={res_profile_id}）")

    async def _send_gen_progress(step_key: str, step_name: str, idx: int, total: int, status: str = "running"):
        """发送资源生成进度通知"""
        try:
            pct = round(progress_base + (idx / total) * progress_range)
            await notification_manager.send_notification(
                user_id=user_id,
                notification_type="resource_generation",
                title="📚 资源生成中" if status == "running" else "✅ 资源生成完成",
                content=f"正在生成{step_name}..." if status == "running" else "本阶段资源已全部生成",
                data={
                    "step": step_key,
                    "step_name": step_name,
                    "progress": pct,
                    "status": status,
                    "stage_id": stage_id,
                },
            )
        except Exception:
            pass  # 通知失败不影响生成

    log.info(f"为用户 {user_id} 阶段 {stage_id} 生成资源: topic='{stage_topic}'")

    total = len(resource_steps)
    for idx, (res_type, display_name) in enumerate(resource_steps, 1):
        await _send_gen_progress(res_type, display_name, idx, total, "running")

        async with AsyncSessionLocal() as db:
            from app.models.upsert import upsert as mysql_upsert

            try:
                if res_type == "document":
                    doc_agent = DocumentAgent(db)
                    doc_result = await doc_agent.run(stage_topic, user_id=user_id)
                    await mysql_upsert(db, LearningResource.__table__, values={
                        "user_id": user_id, "profile_id": res_profile_id, "stage_id": stage_id,
                        "resource_type": "document", "topic": stage_topic, "content": doc_result,
                    })
                    await db.commit()

                elif res_type == "mindmap":
                    mm_agent = MindmapAgent(db)
                    mm_result = await mm_agent.run(stage_topic, user_id=user_id)
                    mindmap_md = mm_result.get("mindmap_markdown", "") if isinstance(mm_result, dict) else ""
                    mindmap_html = mm_result.get("mindmap_html", "") if isinstance(mm_result, dict) else ""
                    await mysql_upsert(db, LearningResource.__table__, values={
                        "user_id": user_id, "profile_id": res_profile_id, "stage_id": stage_id,
                        "resource_type": "mindmap", "topic": stage_topic,
                        "content": {"mindmap_markdown": mindmap_md, "mindmap_html": mindmap_html},
                    })
                    await db.commit()

                elif res_type == "code":
                    code_agent = CodeAgent(db)
                    code_result = await code_agent.run(stage_topic, user_id=user_id)
                    await mysql_upsert(db, LearningResource.__table__, values={
                        "user_id": user_id, "profile_id": res_profile_id, "stage_id": stage_id,
                        "resource_type": "code", "topic": stage_topic, "content": code_result,
                    })
                    await db.commit()

                elif res_type == "question":
                    question_agent = QuestionAgent(db)
                    q_result = await question_agent.run(stage_topic, user_id=user_id)
                    await mysql_upsert(db, LearningResource.__table__, values={
                        "user_id": user_id, "profile_id": res_profile_id, "stage_id": stage_id,
                        "resource_type": "question", "topic": stage_topic, "content": q_result,
                    })
                    await db.commit()

                elif res_type == "ppt_video":
                    from app.agents.ppt_video_agent import PptVideoAgent
                    pv_agent = PptVideoAgent(db)
                    pv_result = await pv_agent.run(topic=stage_topic, stage_id=stage_id, user_id=user_id)
                    await mysql_upsert(db, LearningResource.__table__, values={
                        "user_id": user_id, "profile_id": res_profile_id, "stage_id": stage_id,
                        "resource_type": "ppt_video", "topic": stage_topic, "content": pv_result,
                    })
                    await db.commit()

                elif res_type == "reading_material":
                    from app.agents.reading_material_agent import ReadingMaterialAgent
                    rm_agent = ReadingMaterialAgent(db)
                    rm_result = await rm_agent.run(stage_topic, user_id=user_id)
                    await mysql_upsert(db, LearningResource.__table__, values={
                        "user_id": user_id, "profile_id": res_profile_id, "stage_id": stage_id,
                        "resource_type": "reading_material", "topic": stage_topic, "content": rm_result,
                    })
                    await db.commit()

                elif res_type == "glossary":
                    from app.agents.glossary_agent import GlossaryAgent
                    gl_agent = GlossaryAgent(db)
                    gl_result = await gl_agent.run(stage_topic, user_id=user_id)
                    await mysql_upsert(db, LearningResource.__table__, values={
                        "user_id": user_id, "profile_id": res_profile_id, "stage_id": stage_id,
                        "resource_type": "glossary", "topic": stage_topic, "content": gl_result,
                    })
                    await db.commit()

                elif res_type == "knowledge_link":
                    from app.agents.knowledge_graph_agent import KnowledgeGraphAgent
                    kl_agent = KnowledgeGraphAgent(db, scope="stage")
                    kl_result = await kl_agent.run(stage_topic, user_id=user_id)
                    await mysql_upsert(db, LearningResource.__table__, values={
                        "user_id": user_id, "profile_id": res_profile_id, "stage_id": stage_id,
                        "resource_type": "knowledge_link", "topic": stage_topic, "content": kl_result,
                    })
                    await db.commit()

                elif res_type == "summary":
                    from app.agents.summary_agent import SummaryAgent
                    sm_agent = SummaryAgent(db)
                    sm_result = await sm_agent.run(stage_topic, user_id=user_id)
                    await mysql_upsert(db, LearningResource.__table__, values={
                        "user_id": user_id, "profile_id": res_profile_id, "stage_id": stage_id,
                        "resource_type": "summary", "topic": stage_topic, "content": sm_result,
                    })
                    await db.commit()

            except Exception as e:
                log.error(f"阶段 {stage_id} {display_name}生成失败: {e}")

    # 发送完成通知
    await _send_gen_progress("done", "完成", total, total, "completed")

    # ============ 资源质量评估 ============
    try:
        from app.agents.resource_quality_agent import ResourceQualityAgent
        quality_agent = ResourceQualityAgent(db=None)
        for res_type, _ in resource_steps:
            async with AsyncSessionLocal() as q_db:
                res_result = await q_db.execute(
                    select(LearningResource).where(
                        LearningResource.user_id == user_id,
                        LearningResource.stage_id == stage_id,
                        LearningResource.resource_type == res_type,
                    ).order_by(LearningResource.created_at.desc()).limit(1)
                )
                res_record = res_result.scalar_one_or_none()
                if res_record and not (isinstance(res_record.content, dict) and res_record.content.get("quality_score")):
                    quality = await quality_agent.run(
                        topic=stage_topic,
                        resource_type=res_type,
                        content=res_record.content,
                        user_id=user_id
                    )
                    updated_content = dict(res_record.content) if isinstance(res_record.content, dict) else {"content": res_record.content}
                    updated_content["quality_score"] = quality
                    res_record.content = updated_content
                    await q_db.commit()
                    log.info(f"阶段 {stage_id} 资源 {res_type} 质量评估完成: {quality.get('overall_score')}分")
    except Exception as e:
        log.error(f"阶段 {stage_id} 资源质量评估失败: {e}")

    log.info(f"阶段 {stage_id} 资源生成完成")


# ==================== 阶段完成 & 按阶段生成资源 ====================

class StageCompleteRequest(BaseModel):
    stage_id: int = Field(..., description="要完成的阶段 ID")


@router.post("/learn/stage/complete")
async def complete_stage(
    request: StageCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记某个学习阶段为已完成"""
    # 获取活跃画像
    prof_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
        )
    )
    prof = prof_result.scalar_one_or_none()
    path_query = select(LearningPath).where(LearningPath.user_id == current_user.id)
    if prof:
        path_query = path_query.where(LearningPath.profile_id == prof.id)
    result = await db.execute(path_query)
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=404, detail="学习路径不存在")

    completed = list(path.completed_stages) if path.completed_stages else []
    if request.stage_id not in completed:
        completed.append(request.stage_id)
        path.completed_stages = completed
        await db.commit()

        # 记录阶段完成事件（供评估 Agent 回顾趋势）
        try:
            stage_record = LearningRecord(
                user_id=current_user.id,
                resource_type="stage_complete",
                resource_id=None,
                correct=True,
                score=10,
                behavior_data={"stage_id": request.stage_id},
            )
            db.add(stage_record)
            await db.commit()
        except Exception:
            pass  # 记录失败不影响主流程

    # 后台任务：触发评估 + 预生成下一阶段资源（失败不影响主流程）
    async def _post_complete():
        try:
            from app.models import AsyncSessionLocal
            from app.core.websocket_manager import notification_manager

            # ── 阶段1：学习评估 ──
            await notification_manager.send_notification(
                user_id=current_user.id,
                notification_type="resource_generation",
                title="📊 正在评估学习效果",
                content="评估 Agent 正在分析您的学习情况...",
                data={"step": "evaluation", "step_name": "评估 Agent · 分析学习效果", "progress": 5, "status": "running"},
            )
            eval_result = None
            try:
                async with AsyncSessionLocal() as eval_db:
                    eval_result = await _try_trigger_evaluation(current_user.id, eval_db, force=True)
            except Exception as e:
                log.error(f"后台评估失败: {e}")
            await notification_manager.send_notification(
                user_id=current_user.id,
                notification_type="resource_generation",
                title="📊 评估完成",
                content="学习评估已完成，正在判断是否需要优化路径...",
                data={"step": "evaluation", "step_name": "评估 Agent · 分析学习效果", "progress": 25, "status": "running"},
            )

            # ── 阶段2：路径增量更新判断 ──
            await notification_manager.send_notification(
                user_id=current_user.id,
                notification_type="resource_generation",
                title="🧭 正在优化学习路径",
                content="路径规划 Agent 正在判断是否需要调整学习路径...",
                data={"step": "path_update", "step_name": "路径规划 Agent · 优化学习路径", "progress": 30, "status": "running"},
            )
            if eval_result:
                try:
                    from app.agents.evaluation_agent import EvaluationAgent
                    eval_agent = EvaluationAgent(db=None)
                    path_updated = await eval_agent._update_path_incrementally(current_user.id, eval_result)
                    if path_updated:
                        await notification_manager.send_notification(
                            user_id=current_user.id,
                            notification_type="learning_progress",
                            data={"path_updated": True},
                            title="📊 学习路径已优化",
                            content="根据您的学习情况，学习路径已优化调整，请查看最新学习计划。"
                        )
                except Exception as e:
                    log.error(f"后台路径更新失败: {e}")
            await notification_manager.send_notification(
                user_id=current_user.id,
                notification_type="resource_generation",
                title="🧭 路径检查完成",
                content="开始生成下一阶段学习资源...",
                data={"step": "path_update", "step_name": "路径规划 Agent · 优化学习路径", "progress": 40, "status": "running"},
            )

            # ── 阶段3：预生成下一阶段资源（进度映射到 40-100%） ──
            try:
                async with AsyncSessionLocal() as gen_db:
                    from sqlalchemy import select as sa_select
                    from app.models import StudentProfile as SP
                    gp = (await gen_db.execute(sa_select(SP).where(SP.user_id == current_user.id, SP.is_active == True))).scalar_one_or_none()
                    gpq = select(LearningPath).where(LearningPath.user_id == current_user.id)
                    if gp:
                        gpq = gpq.where(LearningPath.profile_id == gp.id)
                    r = await gen_db.execute(gpq)
                    fresh_path = r.scalar_one_or_none()
                    if fresh_path and fresh_path.stages:
                        done = fresh_path.completed_stages or []
                        for s in fresh_path.stages:
                            if s.get("stage_id") not in done:
                                log.info(f"预生成阶段 {s.get('stage_id')} 资源")
                                await _generate_one_stage(current_user.id, s, progress_base=40, progress_range=60)
                                break
                # 生成完成通知
                await notification_manager.send_notification(
                    user_id=current_user.id,
                    notification_type="resource_generation",
                    title="✅ 下一阶段资源已就绪",
                    content="学习资源已生成完毕，可以开始学习了。",
                    data={"step": "auto_generate", "progress": 100, "status": "completed"},
                )
            except Exception as e:
                log.error(f"后台资源预生成失败: {e}")

        except Exception as e:
            log.error(f"阶段完成后台任务失败: {e}")

    # 保持任务引用，防止被 GC 回收
    _bg_task = asyncio.create_task(_post_complete())
    _bg_task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)

    log.info(f"学生 {current_user.id} 完成阶段 {request.stage_id}")
    return {"message": "阶段已完成", "completed_stages": completed}


class StageGenerateRequest(BaseModel):
    stage_id: int = Field(..., description="要生成资源的阶段 ID")
    force: bool = Field(False, description="是否强制重新生成")


class KnowledgeGraphRequest(BaseModel):
    stage_id: Optional[int] = Field(None, description="阶段 ID（不传则生成全局图谱）")
    topic: Optional[str] = Field(None, description="主题（不传则自动使用学习目标）")


@router.post("/learn/stage/generate")
async def generate_stage_resources(
    request: StageGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """为指定学习阶段生成全部资源（复用 _generate_one_stage）"""
    from app.models import LearningResource

    # 获取活跃画像
    prof_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
        )
    )
    prof = prof_result.scalar_one_or_none()
    path_query = select(LearningPath).where(LearningPath.user_id == current_user.id)
    if prof:
        path_query = path_query.where(LearningPath.profile_id == prof.id)
    result = await db.execute(path_query)
    path = result.scalar_one_or_none()
    if not path or not path.stages:
        raise HTTPException(status_code=404, detail="学习路径不存在")

    stage = None
    for s in path.stages:
        if s.get("stage_id") == request.stage_id:
            stage = s
            break
    if not stage:
        raise HTTPException(status_code=404, detail=f"阶段 {request.stage_id} 不存在")

    kps = stage.get("knowledge_points", [])
    if kps and isinstance(kps[0], dict):
        stage_topic = "、".join([kp.get("name", "") for kp in kps]) or stage.get("title", "")
    else:
        stage_topic = "、".join([str(kp) for kp in kps]) or stage.get("title", "")

    # 直接复用统一的生成函数（含进度通知 + 质量评估）
    await _generate_one_stage(current_user.id, stage, force=request.force)

    # 读回生成结果返回给前端（按 profile_id 过滤）
    id_query = select(LearningResource.resource_type, func.max(LearningResource.id).label("max_id")).where(
        LearningResource.user_id == current_user.id,
        LearningResource.stage_id == request.stage_id,
    )
    if prof:
        id_query = id_query.where(LearningResource.profile_id == prof.id)
    id_result = await db.execute(id_query.group_by(LearningResource.resource_type))
    latest_ids = [row.max_id for row in id_result.all()]
    generated = {}
    if latest_ids:
        content_result = await db.execute(
            select(LearningResource).where(LearningResource.id.in_(latest_ids))
        )
        for r in content_result.scalars().all():
            generated[r.resource_type] = r.content

    return {"stage_id": request.stage_id, "topic": stage_topic, "generated": generated}


@router.get("/learn/stage/resources/{stage_id}")
async def get_stage_resources(
    stage_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定阶段的已生成资源（两步查询，避免 sort_buffer_size 溢出）"""
    from app.models import LearningResource

    # 第一步：按 resource_type 分组取 max(id)
    id_result = await db.execute(
        select(
            LearningResource.resource_type,
            func.max(LearningResource.id).label("max_id")
        ).where(
            LearningResource.user_id == current_user.id,
            LearningResource.stage_id == stage_id,
        ).group_by(LearningResource.resource_type)
    )
    latest_ids = [row.max_id for row in id_result.all()]

    # 第二步：按 ID 精确取 content
    typed_resources = {}
    if latest_ids:
        content_result = await db.execute(
            select(LearningResource).where(LearningResource.id.in_(latest_ids))
        )
        for r in content_result.scalars().all():
            typed_resources[r.resource_type] = r.content

    return {"stage_id": stage_id, "resources": typed_resources}


async def evaluate_answer(answer: str, question: dict) -> AnswerEvaluation:
    """评估答案"""
    import re

    question_type = question.get("type", "")
    correct_answer = question.get("answer", "")
    score = question.get("score", 10)

    if question_type == "code":
        test_cases = question.get("test_cases", [])
        question_agent = QuestionAgent()
        code_result = await question_agent.evaluate_code(answer, test_cases)

        is_correct = code_result["score_ratio"] == 1.0
        earned_score = int(score * code_result["score_ratio"])

        return AnswerEvaluation(
            question_id=question["question_id"],
            correct=is_correct,
            score=earned_score,
            max_score=score,
            feedback=f"测试用例通过 {code_result['passed']}/{code_result['total']}",
            code_results=code_result
        )

    if question_type == "case_analysis":
        # 案例分析题：开放题，有作答即给 60% 基础分
        has_answer = bool(answer and answer.strip())
        earned_score = int(score * 0.6) if has_answer else 0
        return AnswerEvaluation(
            question_id=question["question_id"],
            correct=has_answer,  # 有作答视为"完成"
            score=earned_score,
            max_score=score,
            feedback="案例分析已提交，教师可进一步评分" if has_answer else "未作答"
        )

    # 选择题/判断题/填空题
    def _extract_letter(text: str) -> str:
        """提取选项字母前缀，如 'A. P(Y)P(X)' → 'A'"""
        m = re.match(r'^([A-Za-z])', text.strip())
        return m.group(1).upper() if m else ""

    submitted = answer.strip()
    correct = correct_answer.strip()

    # 1. 全文本比较（最严格）
    is_correct = submitted.lower() == correct.lower()

    # 2. 字母前缀比较（处理 "A. xxx" vs "A"）
    if not is_correct:
        sub_letter = _extract_letter(submitted)
        cor_letter = _extract_letter(correct)
        if sub_letter and cor_letter:
            is_correct = sub_letter == cor_letter
        elif sub_letter and not cor_letter:
            # 正确答案是纯字母，用户提交的是完整选项
            is_correct = sub_letter == correct.upper()
        elif cor_letter and not sub_letter:
            # 用户提交的是纯字母，正确答案是完整选项
            is_correct = submitted.upper() == cor_letter

    # 3. 包含比较（处理 "P(X|Y)" vs "A. P(X|Y)" 等边缘情况）
    if not is_correct:
        s_lower = submitted.lower()
        c_lower = correct.lower()
        if len(s_lower) > 2 and len(c_lower) > 2:
            is_correct = c_lower in s_lower or s_lower in c_lower

    return AnswerEvaluation(
        question_id=question["question_id"],
        correct=is_correct,
        score=score if is_correct else 0,
        max_score=score,
        feedback="回答正确！" if is_correct else f"正确答案是: {correct_answer}"
    )


# ==================== 学习行为追踪 ====================

VALID_EVENT_TYPES = {"resource_view", "stage_start", "stage_complete", "code_execute", "chat_message", "question"}


class TrackEventRequest(BaseModel):
    event_type: str = Field(..., description="事件类型")
    resource_type: Optional[str] = Field(None, description="资源类型: document/mindmap/code/question/video_script")
    stage_id: Optional[int] = Field(None, description="阶段 ID")
    metadata: Optional[dict] = Field(None, description="附加数据")
    duration_seconds: Optional[int] = Field(None, description="停留时长（秒）")


@router.post("/track/event")
async def track_event(
    request: TrackEventRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """通用学习行为追踪 — 写入 learning_records"""
    if request.event_type not in VALID_EVENT_TYPES:
        return {"ok": False, "error": f"invalid event_type: {request.event_type}"}

    from app.models import LearningRecord
    try:
        record = LearningRecord(
            user_id=current_user.id,
            resource_type=request.event_type,
            resource_id=None,
            correct=None,
            score=None,
            duration_seconds=request.duration_seconds,
            behavior_data={
                "resource_type": request.resource_type,
                "stage_id": request.stage_id,
                **(request.metadata or {}),
            },
        )
        db.add(record)
        await db.commit()
        return {"ok": True}
    except Exception as e:
        log.error(f"追踪事件写入失败: {e}")
        await db.rollback()
        return {"ok": False, "error": str(e)}


# ==================== 学习进度汇总接口 ====================

class ProgressSummary(BaseModel):
    """学习进度汇总"""
    total_stages: int
    completed_stages: int
    completion_rate: float
    total_resources: int
    total_questions: int
    correct_questions: int
    accuracy_rate: float
    learning_hours: float
    weak_points: List[str]
    last_activity: Optional[datetime] = None
    # 新增行为追踪维度
    resource_access_count: int = 0
    avg_session_duration: float = 0.0
    learning_streak: int = 0
    total_study_time: int = 0
    event_type_counts: dict = {}
    daily_stats: List[dict] = []


@router.get("/progress/summary", response_model=ProgressSummary)
async def get_progress_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取学习进度汇总"""
    log.info(f"学生 {current_user.id} 获取学习进度汇总")

    # 查询学习路径（按活跃画像）
    prof_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
        )
    )
    prof = prof_result.scalar_one_or_none()
    path_query = select(LearningPath).where(LearningPath.user_id == current_user.id)
    if prof:
        path_query = path_query.where(LearningPath.profile_id == prof.id)
    path_result = await db.execute(path_query)
    path = path_result.scalar_one_or_none()
    total_stages = len(path.stages) if path and path.stages else 0

    # 查询所有学习记录
    records_result = await db.execute(
        select(LearningRecord).where(LearningRecord.user_id == current_user.id)
    )
    records = list(records_result.scalars().all())

    # 计算统计
    completed_stages = len(path.completed_stages) if path and path.completed_stages else 0
    total_questions = sum(1 for r in records if r.resource_type == "question")
    correct_questions = sum(1 for r in records if r.resource_type == "question" and r.correct)
    total_hours = sum(r.duration_seconds or 0 for r in records) / 3600

    # 最后活动时间
    last_activity = max((r.created_at for r in records), default=None) if records else None

    # ── 行为追踪新维度 ──
    resource_views = [r for r in records if r.resource_type == "resource_view"]
    resource_access_count = len(resource_views)
    total_study_time = sum(r.duration_seconds or 0 for r in resource_views)
    # 平均单次时长：只统计有时长的记录，避免旧数据的 0 值拉低平均
    timed_views = [r for r in resource_views if (r.duration_seconds or 0) > 0]
    avg_session_duration = round(total_study_time / max(len(timed_views), 1) / 60, 1)

    # 连续学习天数
    from datetime import date, timedelta as td
    active_dates = sorted(set(r.created_at.date() for r in records if hasattr(r.created_at, 'date')), reverse=True)
    learning_streak = 0
    if active_dates:
        most_recent = active_dates[0]
        today = date.today()
        expected = today if most_recent >= today else most_recent
        for d in active_dates:
            if d == expected:
                learning_streak += 1
                expected = expected - td(days=1)
            elif d < expected:
                break

    # 近7天学习时长统计
    today = date.today()
    daily_stats = []
    for i in range(6, -1, -1):
        day = today - td(days=i)
        day_records = [r for r in records if r.created_at and r.created_at.date() == day]
        day_duration = sum(r.duration_seconds or 0 for r in day_records)
        daily_stats.append({"date": day.isoformat(), "duration": day_duration})

    # 事件类型分布
    event_type_counts = {}
    for r in records:
        if r.resource_type:
            event_type_counts[r.resource_type] = event_type_counts.get(r.resource_type, 0) + 1

    return ProgressSummary(
        total_stages=total_stages,
        completed_stages=completed_stages,
        completion_rate=round(completed_stages / max(total_stages, 1), 2),
        total_resources=len(records),
        total_questions=total_questions,
        correct_questions=correct_questions,
        accuracy_rate=round(correct_questions / max(total_questions, 1), 2),
        learning_hours=round(total_hours, 2),
        weak_points=[],
        last_activity=last_activity,
        resource_access_count=resource_access_count,
        avg_session_duration=avg_session_duration,
        learning_streak=learning_streak,
        total_study_time=total_study_time,
        event_type_counts=event_type_counts,
        daily_stats=daily_stats,
    )


# ==================== 学生作业接口 ====================

@router.get("/assignments")
async def get_student_assignments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取学生被分配的作业列表"""
    from app.models import Assignment
    from sqlalchemy import select

    log.info(f"学生 {current_user.id} 获取作业列表")

    result = await db.execute(
        select(Assignment).where(
            Assignment.status == "published",
            Assignment.target_students.contains([current_user.id])
        )
    )
    assignments = result.scalars().all()

    return [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "teacher_id": a.teacher_id,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in assignments
    ]


@router.post("/assignments/{assignment_id}/submit")
async def submit_assignment(
    assignment_id: int,
    content: str = "",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提交作业"""
    from app.models import Assignment, AssignmentSubmission
    from sqlalchemy import select
    from datetime import datetime

    log.info(f"学生 {current_user.id} 提交作业 {assignment_id}")

    # 检查作业是否存在且已分配给该学生
    assignment_result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.status != "published":
        raise HTTPException(status_code=400, detail="作业未发布")
    if current_user.id not in (assignment.target_students or []):
        raise HTTPException(status_code=403, detail="未被分配此作业")

    # 检查是否已提交
    existing_result = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == current_user.id
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        # 更新已存在的提交
        existing.content = content
        existing.submitted_at = datetime.now()
        existing.status = "submitted"
    else:
        # 创建新的提交
        submission = AssignmentSubmission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            content=content,
            status="submitted"
        )
        db.add(submission)

    await db.commit()

    return {"message": "作业已提交", "assignment_id": assignment_id}


@router.get("/assignments/{assignment_id}/submission")
async def get_assignment_submission(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取学生的作业提交记录"""
    from app.models import AssignmentSubmission
    from sqlalchemy import select

    log.info(f"学生 {current_user.id} 获取作业 {assignment_id} 的提交记录")

    result = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == current_user.id
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        return None

    return {
        "id": submission.id,
        "content": submission.content,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "score": submission.score,
        "feedback": submission.feedback,
        "status": submission.status
    }


# ────────────────────────────────────────────────────────────────
# 知识图谱 API（Neo4j）
# ────────────────────────────────────────────────────────────────

@router.get("/knowledge-graph")
async def get_knowledge_graph(
    stage_id: Optional[int] = Query(None, description="阶段 ID（不传则返回全部）"),
    current_user: User = Depends(get_current_user),
):
    """从 Neo4j 获取知识图谱"""
    try:
        from app.core.neo4j_client import KnowledgeGraphStore
        graph = await KnowledgeGraphStore.get_graph(current_user.id, stage_id=stage_id)
        return graph
    except Exception as e:
        log.warning(f"获取知识图谱失败（Neo4j 可能未启动）: {e}")
        return {"nodes": [], "edges": []}


@router.post("/knowledge-graph/generate")
async def generate_knowledge_graph(
    body: KnowledgeGraphRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成全局知识图谱并存入 Neo4j（基于学习路径结构，覆盖所有阶段）"""
    try:
        from app.core.neo4j_client import KnowledgeGraphStore
        from app.agents.knowledge_graph_agent import KnowledgeGraphAgent
    except ImportError as e:
        log.error(f"Neo4j 驱动未安装: {e}")
        raise HTTPException(status_code=500, detail="Neo4j 驱动未安装，请先运行: pip install neo4j")

    # 从学习路径结构中提取所有阶段信息作为图谱素材（按活跃画像）
    from app.models import LearningPath, StudentProfile
    kg_prof_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
        )
    )
    kg_prof = kg_prof_result.scalar_one_or_none()
    kg_path_query = select(LearningPath).where(LearningPath.user_id == current_user.id)
    if kg_prof:
        kg_path_query = kg_path_query.where(LearningPath.profile_id == kg_prof.id)
    path_result = await db.execute(
        kg_path_query.order_by(LearningPath.created_at.desc()).limit(1)
    )
    path = path_result.scalar_one_or_none()

    content_text = ""
    if path and path.stages:
        for stage in path.stages:
            title = stage.get("title", "")
            desc = stage.get("description", "")
            kps = stage.get("knowledge_points", [])
            kp_names = []
            for kp in kps:
                if isinstance(kp, dict):
                    kp_names.append(kp.get("name", ""))
                else:
                    kp_names.append(str(kp))
            content_text += f"## {title}\n{desc}\n知识点：{'、'.join(kp_names)}\n\n"

    # 用学习目标作为全局主题
    profile_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_active == True,
        )
    )
    profile = profile_result.scalar_one_or_none()
    topic = body.topic or (profile.goal if profile and profile.goal else "学习路径知识图谱")

    try:
        kg_agent = KnowledgeGraphAgent(db)
        # force=True：用户主动点击"重新生成"时强制重新生成
        graph = await kg_agent.run(topic, content=content_text, user_id=current_user.id, stage_id=None, force=True)
        return graph
    except Exception as e:
        log.error(f"知识图谱生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"知识图谱生成失败: {str(e)}")


# ==================== 语音识别（ASR） ====================

@router.post("/asr/recognize")
async def recognize_speech(
    file: UploadFile = File(..., description="音频文件（PCM/WAV/MP3）"),
    current_user: User = Depends(get_current_user),
):
    """语音识别：将音频转为文本"""
    log.info(f"学生 {current_user.id} 请求语音识别")

    audio_data = await file.read()
    if len(audio_data) < 100:
        raise HTTPException(status_code=400, detail="音频数据过短")

    try:
        from app.multimodal.asr_client import xunfei_asr
        text = await xunfei_asr.recognize(audio_data)
        return {"text": text}
    except Exception as e:
        log.error(f"语音识别失败: {e}")
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")


# ==================== 图片文字识别（OCR） ====================

@router.post("/ocr/recognize")
async def recognize_image(
    file: UploadFile = File(..., description="图片文件（JPG/PNG）"),
    current_user: User = Depends(get_current_user),
):
    """图片文字识别：将图片中的题目文字转为文本

    用于辅导场景，学生上传题目图片 → OCR 识别为文字 → 传给智能辅导 Agent。
    TutorAgent 使用的大模型不一定支持多模态，因此图片需先经 OCR 转为纯文本。
    """
    log.info(f"学生 {current_user.id} 请求图片文字识别")

    image_data = await file.read()
    if len(image_data) < 100:
        raise HTTPException(status_code=400, detail="图片数据过小")

    # 限制图片大小（5MB）
    if len(image_data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片不能超过 5MB")

    try:
        from app.multimodal.ocr_client import xunfei_ocr
        text = await xunfei_ocr.recognize(image_data)
        if not text:
            raise HTTPException(status_code=422, detail="未识别出文字内容")
        return {"text": text}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"图片文字识别失败: {e}")
        raise HTTPException(status_code=500, detail=f"图片识别失败: {str(e)}")
