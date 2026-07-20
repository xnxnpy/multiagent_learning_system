from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from app.models import ResourceReview
from app.core.exceptions import NotFoundException
from app.repositories.base_repository import BaseRepository


class ResourceReviewService:
    """资源审核服务"""

    def __init__(self):
        self.review_repo = BaseRepository(ResourceReview)

    async def get_by_id(self, db: AsyncSession, review_id: int) -> Optional[ResourceReview]:
        """根据 ID 获取审核记录"""
        review = await self.review_repo.get(db, review_id)
        if not review:
            raise NotFoundException(detail=f"Resource review with id {review_id} not found")
        return review

    async def create(
        self,
        db: AsyncSession,
        resource_type: str,
        resource_content: str,
        creator_id: int
    ) -> ResourceReview:
        """创建资源审核记录"""
        review = ResourceReview(
            resource_type=resource_type,
            resource_content=resource_content,
            creator_id=creator_id,
            status="pending"
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)
        return review

    async def approve(
        self,
        db: AsyncSession,
        review_id: int,
        reviewer_id: int,
        comment: str = None
    ) -> ResourceReview:
        """审核通过"""
        review = await self.get_by_id(db, review_id)
        review.status = "approved"
        review.reviewer_id = reviewer_id
        review.review_comment = comment
        review.reviewed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(review)
        return review

    async def reject(
        self,
        db: AsyncSession,
        review_id: int,
        reviewer_id: int,
        comment: str
    ) -> ResourceReview:
        """审核拒绝"""
        review = await self.get_by_id(db, review_id)
        review.status = "rejected"
        review.reviewer_id = reviewer_id
        review.review_comment = comment
        review.reviewed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(review)
        return review

    async def get_pending_reviews(
        self, db: AsyncSession
    ) -> List[ResourceReview]:
        """获取待审核资源列表"""
        query = select(ResourceReview).where(
            ResourceReview.status == "pending"
        ).order_by(ResourceReview.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_reviews_by_reviewer(
        self, db: AsyncSession, reviewer_id: int
    ) -> List[ResourceReview]:
        """获取审核员已审核的资源列表"""
        query = select(ResourceReview).where(
            ResourceReview.reviewer_id == reviewer_id
        ).order_by(ResourceReview.reviewed_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_reviews_paginated(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        status: str = None,
        resource_type: str = None
    ) -> tuple[List[ResourceReview], int]:
        """分页获取审核记录"""
        query = select(ResourceReview)

        if status:
            query = query.where(ResourceReview.status == status)
        if resource_type:
            query = query.where(ResourceReview.resource_type == resource_type)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        query = query.offset(skip).limit(limit).order_by(ResourceReview.created_at.desc())
        result = await db.execute(query)
        reviews = list(result.scalars().all())

        return reviews, total

    async def get_user_resources(
        self, db: AsyncSession, user_id: int
    ) -> List[ResourceReview]:
        """获取用户提交的资源列表"""
        query = select(ResourceReview).where(
            ResourceReview.creator_id == user_id
        ).order_by(ResourceReview.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())


resource_review_service = ResourceReviewService()
