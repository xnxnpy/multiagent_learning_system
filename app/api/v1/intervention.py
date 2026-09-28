"""教师干预中心 — 风险学生识别与干预建议"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_roles
from app.core.logger import log
from app.models import User, get_db, LearningRecord, QuestionItem, StudentProfile, LearningPath

router = APIRouter(prefix="/intervention", tags=["干预中心"])


class RiskStudent(BaseModel):
    student_id: int
    username: str
    real_name: str
    accuracy: Optional[float] = None
    questions_7d: int = 0
    wrong_active: int = 0
    study_minutes_7d: float = 0
    streak: int = 0
    risk_level: str  # high / medium / low
    reasons: List[str] = []
    suggestions: List[str] = []


@router.get("/students", response_model=List[RiskStudent])
async def list_risk_students(
    current_user: User = Depends(require_roles(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """按风险排序的学生列表 + 干预建议"""
    from datetime import date, timedelta as td
    since = date.today() - td(days=7)

    students = (await db.execute(
        select(User).where(User.role == "student").limit(200)
    )).scalars().all()

    out: List[RiskStudent] = []
    for u in students:
        recs = (await db.execute(
            select(LearningRecord).where(
                LearningRecord.user_id == u.id,
                LearningRecord.created_at >= datetime.combine(since, datetime.min.time()),
            )
        )).scalars().all()
        qs = [r for r in recs if r.resource_type == "question"]
        correct = sum(1 for r in qs if r.correct)
        acc = round(correct / len(qs) * 100, 1) if qs else None
        minutes = round(sum(r.duration_seconds or 0 for r in recs) / 60, 1)

        wrong = (await db.execute(
            select(func.count(QuestionItem.id)).where(
                QuestionItem.user_id == u.id,
                QuestionItem.wrong_book_status == "active",
            )
        )).scalar() or 0

        active_dates = sorted({r.created_at.date() for r in recs if r.created_at}, reverse=True)
        streak = 0
        if active_dates:
            expected = date.today()
            if active_dates[0] < expected:
                expected = active_dates[0]
            for d in active_dates:
                if d == expected:
                    streak += 1
                    expected = expected - td(days=1)
                elif d < expected:
                    break

        reasons, suggestions = [], []
        if acc is not None and acc < 50 and len(qs) >= 3:
            reasons.append(f"近7天正确率仅 {acc}%")
            suggestions.append("安排基础知识点重练，降低题目难度")
        if wrong >= 5:
            reasons.append(f"错题本积压 {wrong} 题")
            suggestions.append("提醒完成错题重练，可一键布置错题复习")
        if minutes < 30 and len(qs) == 0:
            reasons.append("近7天几乎无学习行为")
            suggestions.append("推送学习提醒，检查路径是否过难")
        if streak == 0 and active_dates:
            reasons.append("连续学习中断")
            suggestions.append("发送回归学习激励通知")

        if any("正确率仅" in r and "仅" in r for r in reasons) and wrong >= 5:
            level = "high"
        elif reasons:
            level = "medium"
        else:
            level = "low"
            if not reasons:
                reasons.append("状态正常")
                suggestions.append("保持当前节奏，可挑战拓展资源")

        out.append(RiskStudent(
            student_id=u.id,
            username=u.username,
            real_name=u.real_name or u.username,
            accuracy=acc,
            questions_7d=len(qs),
            wrong_active=wrong,
            study_minutes_7d=minutes,
            streak=streak,
            risk_level=level,
            reasons=reasons,
            suggestions=suggestions,
        ))

    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda x: (order.get(x.risk_level, 3), -(x.wrong_active or 0)))
    return out
