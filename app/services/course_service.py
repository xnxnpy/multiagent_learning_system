from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import Course
from app.core.exceptions import NotFoundException, ConflictException
from app.repositories.base_repository import BaseRepository


class CourseService:
    """课程服务"""

    def __init__(self):
        self.course_repo = BaseRepository(Course)

    async def get_by_id(self, db: AsyncSession, course_id: int) -> Optional[Course]:
        """根据 ID 获取课程"""
        course = await self.course_repo.get(db, course_id)
        if not course:
            raise NotFoundException(detail=f"Course with id {course_id} not found")
        return course

    async def get_by_teacher(
        self, db: AsyncSession, teacher_id: int
    ) -> List[Course]:
        """获取教师的所有课程"""
        query = select(Course).where(Course.teacher_id == teacher_id)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        teacher_id: int,
        title: str,
        description: str,
        knowledge_tree: dict = None
    ) -> Course:
        """创建课程"""
        course = Course(
            teacher_id=teacher_id,
            title=title,
            description=description,
            knowledge_tree=knowledge_tree
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course

    async def update(
        self,
        db: AsyncSession,
        course_id: int,
        title: str = None,
        description: str = None,
        knowledge_tree: dict = None
    ) -> Course:
        """更新课程"""
        course = await self.get_by_id(db, course_id)
        
        if title is not None:
            course.title = title
        if description is not None:
            course.description = description
        if knowledge_tree is not None:
            course.knowledge_tree = knowledge_tree
        
        await db.commit()
        await db.refresh(course)
        return course

    async def delete(self, db: AsyncSession, course_id: int) -> bool:
        """删除课程"""
        course = await self.get_by_id(db, course_id)
        await self.course_repo.remove(db, id=course_id)
        return True

    async def get_courses_paginated(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        search: str = None,
        teacher_id: int = None
    ) -> tuple[List[Course], int]:
        """分页获取课程列表"""
        query = select(Course)

        if search:
            query = query.where(
                Course.title.ilike(f"%{search}%") |
                Course.description.ilike(f"%{search}%")
            )

        if teacher_id:
            query = query.where(Course.teacher_id == teacher_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        query = query.offset(skip).limit(limit).order_by(Course.id.desc())
        result = await db.execute(query)
        courses = list(result.scalars().all())

        return courses, total

    async def get_all_courses(self, db: AsyncSession) -> List[Course]:
        """获取所有课程"""
        query = select(Course).order_by(Course.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())


course_service = CourseService()
