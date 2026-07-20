from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from app.models import User, LearningRecord, StudentProfile, LearningPath
from app.core.exceptions import NotFoundException


class StatsService:
    """统计服务"""

    async def get_user_stats(
        self, db: AsyncSession, user_id: int
    ) -> Dict:
        """获取用户学习统计"""
        query = select(LearningRecord).where(LearningRecord.user_id == user_id)
        result = await db.execute(query)
        records = list(result.scalars().all())
        
        total_records = len(records)
        correct_count = sum(1 for r in records if r.correct)
        total_score = sum(r.score or 0 for r in records)
        
        return {
            "total_records": total_records,
            "correct_count": correct_count,
            "accuracy": correct_count / total_records if total_records > 0 else 0,
            "average_score": total_score / total_records if total_records > 0 else 0,
            "total_duration": sum(r.duration_seconds or 0 for r in records)
        }

    async def get_class_stats(
        self, db: AsyncSession, teacher_id: int
    ) -> Dict:
        """获取班级统计"""
        course_query = select(func.count()).select_from(User).where(User.role == "student")
        total_result = await db.execute(course_query)
        total_students = total_result.scalar() or 0
        
        record_query = select(LearningRecord).join(User).where(User.role == "student")
        record_result = await db.execute(record_query)
        records = list(record_result.scalars().all())
        
        return {
            "total_students": total_students,
            "total_learning_records": len(records),
            "average_accuracy": sum(1 for r in records if r.correct) / len(records) if records else 0
        }

    async def get_teacher_course_stats(
        self, db: AsyncSession, teacher_id: int
    ) -> List[Dict]:
        """获取教师课程统计"""
        course_query = select(User).where(
            and_(User.role == "student")
        )
        result = await db.execute(course_query)
        students = list(result.scalars().all())
        
        stats = []
        for student in students:
            record_query = select(LearningRecord).where(
                LearningRecord.user_id == student.id
            )
            record_result = await db.execute(record_query)
            records = list(record_result.scalars().all())
            
            if records:
                stats.append({
                    "student_id": student.id,
                    "student_name": student.real_name or student.username,
                    "total_records": len(records),
                    "accuracy": sum(1 for r in records if r.correct) / len(records)
                })
        
        return stats

    async def get_system_stats(self, db: AsyncSession) -> Dict:
        """获取系统统计"""
        user_count_query = select(func.count()).select_from(User)
        user_result = await db.execute(user_count_query)
        total_users = user_result.scalar() or 0
        
        student_count_query = select(func.count()).select_from(User).where(User.role == "student")
        student_result = await db.execute(student_count_query)
        total_students = student_result.scalar() or 0
        
        teacher_count_query = select(func.count()).select_from(User).where(User.role == "teacher")
        teacher_result = await db.execute(teacher_count_query)
        total_teachers = teacher_result.scalar() or 0
        
        profile_count_query = select(func.count()).select_from(StudentProfile)
        profile_result = await db.execute(profile_count_query)
        total_profiles = profile_result.scalar() or 0
        
        path_count_query = select(func.count()).select_from(LearningPath)
        path_result = await db.execute(path_count_query)
        total_paths = path_result.scalar() or 0
        
        return {
            "total_users": total_users,
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_profiles": total_profiles,
            "total_learning_paths": total_paths
        }

    async def get_daily_stats(
        self, db: AsyncSession, days: int = 7
    ) -> List[Dict]:
        """获取每日统计"""
        stats = []
        for i in range(days):
            date = datetime.utcnow().date() - timedelta(days=i)
            start_date = datetime.combine(date, datetime.min.time())
            end_date = datetime.combine(date, datetime.max.time())
            
            query = select(func.count()).select_from(LearningRecord).where(
                and_(
                    LearningRecord.created_at >= start_date,
                    LearningRecord.created_at <= end_date
                )
            )
            result = await db.execute(query)
            count = result.scalar() or 0
            
            stats.append({
                "date": date.isoformat(),
                "count": count
            })
        
        return list(reversed(stats))


stats_service = StatsService()
