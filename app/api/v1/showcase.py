"""案例展示 API - 从数据库查询真实系统数据"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models import (
    get_db, User, StudentProfile, LearningPath,
    LearningResource, EvaluationReport, TutorChatMessage,
)
from app.models.base import async_engine, Base
from app.api.v1.deps import get_current_user
from app.schemas.showcase import (
    ShowcaseResponse, ProfileCase, ResourceCase, PathCase,
    TutorCase, EvaluationCase,
)
from app.core.logger import log

router = APIRouter(prefix="/showcase", tags=["案例展示"])

RESOURCE_TYPE_NAMES = {
    "document": "学习文档", "mindmap": "思维导图", "question": "练习题目",
    "code": "代码示例", "ppt_video": "教学视频",
    "reading_material": "拓展阅读", "glossary": "术语词汇",
    "knowledge_link": "知识关联", "summary": "学习总结",
}
RESOURCE_ORDER = ["document", "ppt_video", "mindmap", "question", "code", "reading_material", "glossary", "knowledge_link", "summary"]


@router.get("/cases", response_model=ShowcaseResponse)
async def get_showcase_cases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从数据库查询真实案例数据"""
    log.info(f"用户 {current_user.id} 获取案例展示数据（数据库模式）")

    try:
        # 确保表存在
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # 1. 查询所有有画像的学生
        profile_query = (
            select(StudentProfile, User)
            .join(User, StudentProfile.user_id == User.id)
            .where(User.role == "student")
            .order_by(StudentProfile.id)
        )
        profile_result = await db.execute(profile_query)
        profile_rows = profile_result.all()

        profiles = []
        for sp, user in profile_rows:
            profiles.append(ProfileCase(
                case_id=sp.id,
                title=f"{user.real_name or user.username} — {sp.profile_name or '默认画像'}",
                description=f"专业{sp.major}，{sp.grade}，{sp.knowledge_level}水平，{sp.learning_style}学习风格",
                profile_data={
                    "major": sp.major, "grade": sp.grade, "goal": sp.goal,
                    "knowledge_level": sp.knowledge_level,
                    "learning_style": sp.learning_style,
                    "weakness": sp.weakness or [],
                    "interests": sp.interests or [],
                    "coding_ability": sp.coding_ability,
                },
                created_at=str(sp.updated_at) if sp.updated_at else None,
            ))

        if not profiles:
            return _empty_response()

        # 2. 查询每个画像的学习路径（按 profile_id）
        paths = []
        for sp, user in profile_rows:
            path_q = (
                select(LearningPath)
                .where(LearningPath.profile_id == sp.id)
                .order_by(desc(LearningPath.created_at))
                .limit(1)
            )
            path_r = await db.execute(path_q)
            lp = path_r.scalar_one_or_none()
            if lp:
                stages = lp.stages or []
                completed = lp.completed_stages or []
                for s in stages:
                    s["completion_status"] = "completed" if s.get("stage_id") in completed else "current" if stages.index(s) == len(completed) else "pending"
                paths.append(PathCase(
                    case_id=lp.id,
                    title=lp.title,
                    student_profile_summary=f"{user.real_name or user.username}，{sp.major}{sp.grade}，{sp.knowledge_level}，{sp.goal}",
                    path_stages=stages,
                    recommendation_reason=_build_recommendation(stages),
                    match_score=0.85 + (lp.path_version - 1) * 0.03,
                    created_at=str(lp.created_at) if lp.created_at else None,
                ))

        # 3. 查询每个画像的资源（按 profile_id）
        resources_by_student = []
        for sp, user in profile_rows:
            profile_summary = f"{user.real_name or user.username}，{sp.major}{sp.grade}，{sp.knowledge_level}，{sp.goal}"

            res_result = await db.execute(
                select(LearningResource)
                .where(LearningResource.profile_id == sp.id)
            )
            all_resources = list(res_result.scalars().all())
            all_resources.sort(key=lambda r: (r.stage_id or 0, r.resource_type, -(r.created_at.timestamp() if r.created_at else 0)))

            stages_map = {}
            for r in all_resources:
                stage_id = r.stage_id or 0
                if stage_id not in stages_map:
                    stages_map[stage_id] = {}
                if r.resource_type not in stages_map[stage_id]:
                    stages_map[stage_id][r.resource_type] = r

            student_resources = []
            for stage_id in sorted(stages_map.keys()):
                for res_type, lr in stages_map[stage_id].items():
                    content = lr.content if isinstance(lr.content, dict) else {"content": str(lr.content)}
                    student_resources.append(ResourceCase(
                        case_id=lr.id,
                        resource_type=res_type,
                        resource_type_name=RESOURCE_TYPE_NAMES.get(res_type, res_type),
                        topic=lr.topic,
                        stage_id=stage_id,
                        content=content,
                        quality_score=content.get("quality_score"),
                        created_at=str(lr.created_at) if lr.created_at else None,
                    ))

            student_resources.sort(key=lambda r: RESOURCE_ORDER.index(r.resource_type) if r.resource_type in RESOURCE_ORDER else 99)

            if student_resources:
                resources_by_student.append({
                    "student_name": user.real_name or user.username,
                    "student_profile": profile_summary,
                    "resources": student_resources,
                })

        # 兼容旧格式：扁平列表（用于统计等）
        resources = [r for s in resources_by_student for r in s["resources"]]

        # 4. 查询每个学生的最新评估报告（按 user_id，评估报告不区分画像）
        seen_eval_user_ids = set()
        evaluations = []
        for sp, user in profile_rows:
            if user.id in seen_eval_user_ids:
                continue
            seen_eval_user_ids.add(user.id)
            eval_q = (
                select(EvaluationReport)
                .where(EvaluationReport.user_id == user.id)
                .order_by(desc(EvaluationReport.created_at))
                .limit(1)
            )
            eval_r = await db.execute(eval_q)
            er = eval_r.scalar_one_or_none()
            if er:
                rd = er.report_data if isinstance(er.report_data, dict) else {}
                evaluations.append(EvaluationCase(
                    case_id=er.id,
                    title=f"{user.real_name or user.username} 学习评估报告",
                    student_profile_summary=f"{user.real_name or user.username}，{sp.major}{sp.grade}，{sp.knowledge_level}，{sp.goal}",
                    evaluation_result={
                        "overall_grade": er.overall_grade,
                        "total_score": er.total_score,
                        "accuracy_rate": er.accuracy_rate,
                        "mastery_level": er.mastery_level,
                        **rd,
                    },
                    created_at=str(er.created_at) if er.created_at else None,
                ))

        # 5. 查询辅导对话（按 user_id，对话不区分画像）
        tutor_dialogues = []
        seen_tutor_user_ids = set()
        for sp, user in profile_rows:
            if user.id in seen_tutor_user_ids:
                continue
            seen_tutor_user_ids.add(user.id)
            chat_q = (
                select(TutorChatMessage)
                .where(TutorChatMessage.user_id == user.id)
                .order_by(TutorChatMessage.session_id, TutorChatMessage.id)
            )
            chat_r = await db.execute(chat_q)
            chats = chat_r.scalars().all()

            session_msgs = {}
            for msg in chats:
                session_msgs.setdefault(msg.session_id, []).append(msg)

            for sid, msgs in session_msgs.items():
                user_msg = next((m for m in msgs if m.role == "user"), None)
                asst_msg = next((m for m in msgs if m.role == "assistant"), None)
                if user_msg and asst_msg:
                    tutor_dialogues.append(TutorCase(
                        case_id=user_msg.id,
                        title=f"{user.real_name or user.username}的辅导对话",
                        question=user_msg.content,
                        answer=asst_msg.content,
                        question_type=_classify_question(user_msg.content),
                        created_at=str(user_msg.created_at) if user_msg.created_at else None,
                    ))

        # 构造响应
        return ShowcaseResponse(
            profiles=profiles,
            resources=resources,
            resources_by_student=resources_by_student,
            paths=paths,
            tutor_dialogues=tutor_dialogues,
            evaluations=evaluations,
            system_info={
                "total_students": len(profiles),
                "total_resources": len(resources),
                "total_paths": len(paths),
                "total_evaluations": len(evaluations),
                "total_tutor_sessions": len(tutor_dialogues),
                "data_source": "database",
            },
        )

    except Exception as e:
        log.error(f"查询案例数据失败: {e}", exc_info=True)
        return _empty_response()


def _build_recommendation(stages: list) -> str:
    """根据路径阶段构建推荐理由"""
    if not stages:
        return "系统根据学生画像自动生成的学习路径"
    stage_count = len(stages)
    topics = [s.get("title", "") for s in stages[:3]]
    return f"共{stage_count}个学习阶段：{'、'.join(topics)}等。路径根据学生画像和学习目标智能推荐。"


def _classify_question(content: str) -> str:
    """简单分类问题类型"""
    if any(k in content for k in ["代码", "编程", "写", "实现"]):
        return "代码相关"
    if any(k in content for k in ["区别", "不同", "对比", "比较"]):
        return "概念对比"
    if any(k in content for k in ["怎么", "如何", "为什么", "是什么"]):
        return "概念理解"
    return "综合问题"


def _empty_response() -> ShowcaseResponse:
    return ShowcaseResponse(
        profiles=[], resources=[], paths=[],
        tutor_dialogues=[], evaluations=[],
        system_info={"message": "暂无案例数据，请先运行工作流生成数据", "data_source": "database"},
    )
