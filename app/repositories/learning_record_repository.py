from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.repositories.base_repository import BaseRepository
from app.models import LearningRecord


class LearningRecordRepository(BaseRepository):
    """学习记录仓库"""

    def __init__(self):
        super().__init__(LearningRecord)

    async def create_record(
        self,
        db: AsyncSession,
        user_id: int,
        resource_type: str,
        resource_id: Optional[int] = None,
        correct: bool = None,
        score: float = None,
        duration_seconds: int = None,
        behavior_data: dict = None
    ) -> LearningRecord:
        """创建学习记录"""
        record_data = {
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "correct": correct,
            "score": score,
            "duration_seconds": duration_seconds,
            "behavior_data": behavior_data
        }
        return await self.create(db, obj_in=record_data)

    async def get_by_user_id(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 100
    ) -> List[LearningRecord]:
        """获取用户的学习记录"""
        result = await db.execute(
            select(LearningRecord)
            .where(LearningRecord.user_id == user_id)
            .order_by(LearningRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_resource(
        self, db: AsyncSession, resource_type: str, resource_id: int
    ) -> List[LearningRecord]:
        """获取特定资源的学习记录"""
        result = await db.execute(
            select(LearningRecord).where(
                and_(
                    LearningRecord.resource_type == resource_type,
                    LearningRecord.resource_id == resource_id
                )
            )
        )
        return list(result.scalars().all())

    async def get_recent_records(
        self, db: AsyncSession, user_id: int, days: int = 7
    ) -> List[LearningRecord]:
        """获取最近的学习记录"""
        since_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        from datetime import timedelta
        since_date = since_date - timedelta(days=days)
        
        result = await db.execute(
            select(LearningRecord).where(
                and_(
                    LearningRecord.user_id == user_id,
                    LearningRecord.created_at >= since_date
                )
            ).order_by(LearningRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_statistics(
        self, db: AsyncSession, user_id: int
    ) -> dict:
        """获取学习统计"""
        records = await self.get_by_user_id(db, user_id, limit=1000)
        
        total = len(records)
        correct_count = sum(1 for r in records if r.correct)
        total_score = sum(r.score or 0 for r in records)
        total_duration = sum(r.duration_seconds or 0 for r in records)
        
        return {
            "total_records": total,
            "correct_count": correct_count,
            "accuracy": correct_count / total if total > 0 else 0,
            "average_score": total_score / total if total > 0 else 0,
            "total_duration_seconds": total_duration
        }

    async def get_records_by_type(
        self, db: AsyncSession, user_id: int, resource_type: str
    ) -> List[LearningRecord]:
        """按资源类型获取学习记录"""
        result = await db.execute(
            select(LearningRecord).where(
                and_(
                    LearningRecord.user_id == user_id,
                    LearningRecord.resource_type == resource_type
                )
            ).order_by(LearningRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_daily_records(
        self, db: AsyncSession, user_id: int, date: datetime
    ) -> List[LearningRecord]:
        """获取指定日期的学习记录"""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        result = await db.execute(
            select(LearningRecord).where(
                and_(
                    LearningRecord.user_id == user_id,
                    LearningRecord.created_at >= start_of_day,
                    LearningRecord.created_at <= end_of_day
                )
            )
        )
        return list(result.scalars().all())
