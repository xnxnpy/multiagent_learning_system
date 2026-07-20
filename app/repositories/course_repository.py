from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base_repository import BaseRepository
from app.models import Course


class CourseRepository(BaseRepository):
    """课程仓库"""

    def __init__(self):
        super().__init__(Course)

    async def get_by_teacher_id(
        self, db: AsyncSession, teacher_id: int
    ) -> List[Course]:
        """获取教师的所有课程"""
        result = await db.execute(
            select(Course)
            .where(Course.teacher_id == teacher_id)
            .order_by(Course.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_title(
        self, db: AsyncSession, title: str
    ) -> Optional[Course]:
        """根据课程标题查找课程"""
        result = await db.execute(
            select(Course).where(Course.title == title)
        )
        return result.scalar_one_or_none()

    async def search_courses(
        self, db: AsyncSession, keyword: str
    ) -> List[Course]:
        """搜索课程"""
        result = await db.execute(
            select(Course).where(
                Course.title.ilike(f"%{keyword}%") |
                Course.description.ilike(f"%{keyword}%")
            )
        )
        return list(result.scalars().all())

    async def get_public_courses(
        self, db: AsyncSession, limit: int = 50
    ) -> List[Course]:
        """获取公开课程列表"""
        result = await db.execute(
            select(Course)
            .order_by(Course.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_knowledge_tree(
        self, db: AsyncSession, course_id: int, knowledge_tree: dict
    ) -> Optional[Course]:
        """更新课程知识树"""
        course = await self.get(db, course_id)
        if course:
            course.knowledge_tree = knowledge_tree
            await db.commit()
            await db.refresh(course)
        return course

    async def get_course_count_by_teacher(
        self, db: AsyncSession, teacher_id: int
    ) -> int:
        """获取教师的课程数量"""
        from sqlalchemy import func
        result = await db.execute(
            select(func.count()).select_from(Course).where(
                Course.teacher_id == teacher_id
            )
        )
        return result.scalar() or 0

    async def delete_by_teacher_id(
        self, db: AsyncSession, teacher_id: int
    ) -> bool:
        """删除教师的所有课程"""
        result = await db.execute(
            select(Course).where(Course.teacher_id == teacher_id)
        )
        courses = list(result.scalars().all())
        for course in courses:
            await db.delete(course)
        await db.commit()
        return True
