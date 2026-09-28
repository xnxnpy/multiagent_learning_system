"""学习广场 — 社区分享（发帖 / 点赞 / 浏览）"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.logger import log
from app.models import User, get_db
from app.models.plaza_post import PlazaPost, PlazaLike

router = APIRouter(prefix="/plaza", tags=["学习广场"])


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    tags: str = Field("", max_length=200)


class PostOut(BaseModel):
    id: int
    title: str
    content: str
    tags: str = ""
    like_count: int = 0
    author: str = ""
    user_id: int = 0
    liked: bool = False
    created_at: Optional[str] = None


async def _decorate(db: AsyncSession, posts: List[PlazaPost], user_id: int) -> List[PostOut]:
    if not posts:
        return []
    ids = [p.id for p in posts]
    uids = {p.user_id for p in posts}
    users = (await db.execute(select(User.id, User.real_name, User.username).where(User.id.in_(uids)))).all()
    names = {i: (r or u or str(i)) for i, r, u in users}
    liked_rows = (await db.execute(
        select(PlazaLike.post_id).where(PlazaLike.user_id == user_id, PlazaLike.post_id.in_(ids))
    )).scalars().all()
    liked_set = set(liked_rows)
    return [
        PostOut(
            id=p.id, title=p.title, content=p.content, tags=p.tags or "",
            like_count=p.like_count or 0, author=names.get(p.user_id, str(p.user_id)),
            user_id=p.user_id,
            liked=p.id in liked_set,
            created_at=p.created_at.isoformat() if p.created_at else None,
        )
        for p in posts
    ]


@router.get("/posts", response_model=List[PostOut])
async def list_posts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    posts = (await db.execute(
        select(PlazaPost).order_by(PlazaPost.created_at.desc()).limit(50)
    )).scalars().all()
    return await _decorate(db, posts, current_user.id)


@router.post("/posts", response_model=PostOut)
async def create_post(
    body: PostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = PlazaPost(
        user_id=current_user.id,
        title=body.title.strip(),
        content=body.content.strip(),
        tags=body.tags.strip(),
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    log.info(f"学生 {current_user.id} 发布广场帖子 {post.id}")
    out = await _decorate(db, [post], current_user.id)
    return out[0]


@router.post("/posts/{post_id}/like")
async def toggle_like(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = (await db.execute(select(PlazaPost).where(PlazaPost.id == post_id))).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    existing = (await db.execute(
        select(PlazaLike).where(PlazaLike.user_id == current_user.id, PlazaLike.post_id == post_id)
    )).scalar_one_or_none()
    if existing:
        await db.delete(existing)
        post.like_count = max(0, (post.like_count or 0) - 1)
        liked = False
    else:
        db.add(PlazaLike(user_id=current_user.id, post_id=post_id))
        post.like_count = (post.like_count or 0) + 1
        liked = True
    await db.commit()
    return {"liked": liked, "like_count": post.like_count}


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = (await db.execute(select(PlazaPost).where(PlazaPost.id == post_id))).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只能删除自己的帖子")
    await db.execute(delete(PlazaLike).where(PlazaLike.post_id == post_id))
    await db.delete(post)
    await db.commit()
    return {"message": "已删除"}
