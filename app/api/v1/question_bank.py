"""题库与错题本 API

- 题库：学生全部题目的统一视图（按阶段/知识点/作答状态筛选）
- 错题本：最近一次作答错误且未移出的题目，支持重练与移出
- 与 /question/submit 共享答题闭环：提交时同步 QuestionItem 状态
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.models import AsyncSessionLocal, QuestionItem, StudentProfile, User
from app.models.base import get_db
from app.core.logger import log

router = APIRouter(prefix="/question-bank", tags=["题库与错题本"])


# ── 响应模型 ───────────────────────────────────────────────


class QuestionItemOut(BaseModel):
    id: int
    question_uid: str
    stage_id: Optional[int] = None
    knowledge_point: Optional[str] = None
    difficulty: Optional[str] = None
    question_type: Optional[str] = None
    question_data: dict
    last_correct: Optional[bool] = None
    last_score: Optional[float] = None
    attempt_count: int = 0
    wrong_book_status: Optional[str] = None


class BankListResponse(BaseModel):
    total: int
    items: List[QuestionItemOut]


class WrongBookStats(BaseModel):
    active: int = 0
    mastered: int = 0
    removed: int = 0
    by_knowledge_point: dict = {}


# ── 服务函数（供 submit_answer 等处复用）───────────────────


async def upsert_question_from_resource(
    db: AsyncSession,
    user_id: int,
    profile_id: Optional[int],
    stage_id: Optional[int],
    questions: List[dict],
) -> int:
    """把资源里的题目列表同步进题库；返回新增/更新条数

    同一 question_uid 幂等：已存在则更新题面（重生成场景），不动作答状态。
    """
    count = 0
    for q in questions:
        if not isinstance(q, dict):
            continue
        uid = str(q.get("question_uid") or f"s{stage_id or 0}_q{q.get('question_id')}")
        q["question_uid"] = uid

        existing = await db.execute(
            select(QuestionItem).where(QuestionItem.question_uid == uid)
        )
        item = existing.scalar_one_or_none()
        if item:
            item.question_data = q
            item.knowledge_point = q.get("knowledge_point") or item.knowledge_point
            item.difficulty = str(q.get("difficulty") or item.difficulty or "")
            item.question_type = str(q.get("type") or item.question_type or "")
        else:
            item = QuestionItem(
                user_id=user_id,
                profile_id=profile_id,
                stage_id=stage_id,
                question_uid=uid,
                knowledge_point=q.get("knowledge_point"),
                difficulty=str(q.get("difficulty") or ""),
                question_type=str(q.get("type") or ""),
                question_data=q,
            )
            db.add(item)
        count += 1
    await db.commit()
    return count


async def record_answer_for_question(
    db: AsyncSession,
    user_id: int,
    question_uid: str,
    correct: bool,
    score: float,
) -> None:
    """提交答案后同步题库状态 + 错题本状态机"""
    result = await db.execute(
        select(QuestionItem).where(QuestionItem.question_uid == str(question_uid))
    )
    item = result.scalar_one_or_none()
    if not item:
        return
    item.last_correct = correct
    item.last_score = score
    item.attempt_count = (item.attempt_count or 0) + 1
    if correct:
        # 重练正确：错题本中则标记已掌握
        if item.wrong_book_status == "active":
            item.wrong_book_status = "mastered"
    else:
        # 答错且此前不在错题本（或已移出）→ 重新进入错题本
        if item.wrong_book_status in (None, "mastered", "removed"):
            item.wrong_book_status = "active"
    await db.commit()


# ── API ────────────────────────────────────────────────────


@router.get("", response_model=BankListResponse)
async def list_question_bank(
    stage_id: Optional[int] = Query(None),
    knowledge_point: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="unanswered|correct|wrong"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """题库列表（分页 + 筛选）"""
    query = select(QuestionItem).where(QuestionItem.user_id == current_user.id)
    if stage_id is not None:
        query = query.where(QuestionItem.stage_id == stage_id)
    if knowledge_point:
        query = query.where(QuestionItem.knowledge_point == knowledge_point)
    if status == "unanswered":
        query = query.where(QuestionItem.attempt_count == 0)
    elif status == "correct":
        query = query.where(QuestionItem.last_correct == True)  # noqa: E712
    elif status == "wrong":
        query = query.where(QuestionItem.last_correct == False)  # noqa: E712

    total_result = await db.execute(select(func.count()).select_from(query.subquery())
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(QuestionItem.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()
    return BankListResponse(
        total=total,
        items=[_to_out(i) for i in items],
    )


@router.get("/wrong-book", response_model=BankListResponse)
async def list_wrong_book(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """错题本：wrong_book_status=active 的题目"""
    query = select(QuestionItem).where(
        QuestionItem.user_id == current_user.id,
        QuestionItem.wrong_book_status == "active",
    )
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    result = await db.execute(
        query.order_by(QuestionItem.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return BankListResponse(total=total, items=[_to_out(i) for i in result.scalars().all()])


@router.get("/wrong-book/stats", response_model=WrongBookStats)
async def wrong_book_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """错题本统计（按知识点聚合，喂给 Supervisor/Evaluation）"""
    result = await db.execute(
        select(QuestionItem.wrong_book_status, func.count())
        .where(QuestionItem.user_id == current_user.id)
        .group_by(QuestionItem.wrong_book_status)
    )
    stats = WrongBookStats()
    for status, cnt in result.all():
        if status == "active":
            stats.active = cnt
        elif status == "mastered":
            stats.mastered = cnt
        elif status == "removed":
            stats.removed = cnt

    kp_result = await db.execute(
        select(QuestionItem.knowledge_point, func.count())
        .where(
            QuestionItem.user_id == current_user.id,
            QuestionItem.wrong_book_status == "active",
        )
        .group_by(QuestionItem.knowledge_point)
    )
    stats.by_knowledge_point = {kp or "通用": cnt for kp, cnt in kp_result.all()}
    return stats


@router.post("/wrong-book/{question_uid}/remove")
async def remove_from_wrong_book(
    question_uid: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """手动移出错题本（标记为 removed，保留在题库）"""
    result = await db.execute(
        select(QuestionItem).where(
            QuestionItem.question_uid == question_uid,
            QuestionItem.user_id == current_user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="题目不存在")
    item.wrong_book_status = "removed"
    await db.commit()
    return {"message": "已移出错题本"}


def _to_out(item: QuestionItem) -> QuestionItemOut:
    return QuestionItemOut(
        id=item.id,
        question_uid=item.question_uid,
        stage_id=item.stage_id,
        knowledge_point=item.knowledge_point,
        difficulty=item.difficulty,
        question_type=item.question_type,
        question_data=item.question_data or {},
        last_correct=item.last_correct,
        last_score=item.last_score,
        attempt_count=item.attempt_count or 0,
        wrong_book_status=item.wrong_book_status,
    )
