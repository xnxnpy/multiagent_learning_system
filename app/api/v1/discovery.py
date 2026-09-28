"""学习发现 — 外部资源检索与个人收藏

- 检索：优先 DuckDuckGo HTML；失败则 LLM 生成可点击的站内搜索链接兜底
- 收藏：DiscoveryItem 按 user_id 隔离，可转入学习上下文
"""
import re
import html as html_mod
from typing import List, Optional
from urllib.parse import quote, urlparse, parse_qs, unquote
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.logger import log
from app.models import User, get_db
from app.models.discovery_item import DiscoveryItem

router = APIRouter(prefix="/discovery", tags=["学习发现"])

RESOURCE_TYPES = ["video", "article", "paper", "repo"]


class DiscoveryItemOut(BaseModel):
    id: int
    title: str
    url: str
    type: str
    summary: str = ""
    source: str = ""
    saved: bool = False


class SaveRequest(BaseModel):
    title: str = Field(..., max_length=300)
    url: str = Field(..., max_length=1000)
    type: str = Field("article")
    summary: str = Field("", max_length=1000)
    source: str = Field("", max_length=120)


def _clean_url(url: str) -> str:
    """DDG 重定向解包"""
    if not url:
        return ""
    if "uddg=" in url:
        try:
            qs = parse_qs(urlparse(url).query)
            if "uddg" in qs:
                return unquote(qs["uddg"][0])
        except Exception:
            pass
    return url


def _ddg_search(query: str, max_results: int = 8) -> List[dict]:
    """同步 DuckDuckGo HTML 搜索（在线时）"""
    req = Request(
        f"https://html.duckduckgo.com/html/?q={quote(query)}",
        headers={"User-Agent": "Mozilla/5.0 (compatible; StudyBot/1.0)"},
    )
    with urlopen(req, timeout=8) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
    results = []
    # 结果块：result__a 标题链接 + result__snippet
    for m in re.finditer(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'(?:class="result__snippet"[^>]*>(.*?)</a>)?',
        raw,
        re.S | re.I,
    ):
        href, title, snip = m.group(1), m.group(2), m.group(3) or ""
        title = html_mod.unescape(re.sub(r"<[^>]+>", "", title)).strip()
        snip = html_mod.unescape(re.sub(r"<[^>]+>", "", snip)).strip()
        url = _clean_url(href)
        if not title or not url.startswith("http"):
            continue
        rtype = _classify(url, title)
        results.append({"title": title[:120], "url": url, "type": rtype, "summary": snip[:200]})
        if len(results) >= max_results:
            break
    return results


def _classify(url: str, title: str) -> str:
    u = (url or "").lower()
    t = (title or "").lower()
    if any(x in u for x in ("github.com", "gitee.com", "gitlab.com")):
        return "repo"
    if any(x in u for x in ("arxiv.org", "scholar.google", "ieee", "acm.org")) or "论文" in title:
        return "paper"
    if any(x in u for x in ("bilibili.com", "youtube.com", "youku", "ixigua")) or "视频" in title:
        return "video"
    return "article"


def _fallback_results(query: str) -> List[dict]:
    """离线/抓取失败：生成真实可点的站内搜索链接"""
    q = quote(query)
    seeds = [
        ("video", "B 站搜索", f"https://search.bilibili.com/all?keyword={q}", f"B 站与「{query}」相关的视频课程"),
        ("article", "CSDN 搜索", f"https://so.csdn.net/so/search?q={q}", f"CSDN 博客与「{query}」相关的教程文章"),
        ("article", "掘金搜索", f"https://juejin.cn/search?query={q}", f"掘金社区与「{query}」相关的前端/工程文章"),
        ("repo", "GitHub 搜索", f"https://github.com/search?q={q}&type=repositories", f"GitHub 上与「{query}」相关的开源仓库"),
        ("paper", "arXiv 搜索", f"https://arxiv.org/search/?query={q}&searchtype=all", f"arXiv 与「{query}」相关的预印本"),
        ("article", "知乎搜索", f"https://www.zhihu.com/search?type=content&q={q}", f"知乎与「{query}」相关的讨论与回答"),
    ]
    return [
        {"title": f"{name}：{query}", "url": url, "type": t, "summary": desc}
        for t, name, url, desc in seeds
    ]


@router.get("/search")
async def search_discovery(
    q: str = Query(..., min_length=1, max_length=80, description="检索词"),
    type: Optional[str] = Query(None, description="video/article/paper/repo"),
    current_user: User = Depends(get_current_user),
):
    """检索外部学习资源（视频/文章/论文/代码仓库）"""
    import asyncio
    log.info(f"学生 {current_user.id} 学习发现检索: {q}")
    results: List[dict] = []
    try:
        results = await asyncio.to_thread(_ddg_search, q, 10)
    except Exception as e:
        log.warning(f"DDG 检索失败，使用搜索链接兜底: {e}")

    if not results:
        results = _fallback_results(q)

    if type:
        results = [r for r in results if r.get("type") == type]
    # 去重
    seen, uniq = set(), []
    for r in results:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        uniq.append(r)
    src = "ddg" if results and "duckduckgo" not in results[0].get("url", "") else "fallback"
    return {"query": q, "items": uniq[:10], "source": src}


@router.get("/saved", response_model=List[DiscoveryItemOut])
async def list_saved(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """我的收藏"""
    rows = (await db.execute(
        select(DiscoveryItem)
        .where(DiscoveryItem.user_id == current_user.id)
        .order_by(DiscoveryItem.created_at.desc())
        .limit(50)
    )).scalars().all()
    return [
        DiscoveryItemOut(
            id=r.id, title=r.title, url=r.url, type=r.type or "article",
            summary=r.summary or "", source=r.source or "", saved=True,
        )
        for r in rows
    ]


@router.post("/save", response_model=DiscoveryItemOut)
async def save_discovery(
    body: SaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """收藏到我的学习库"""
    if body.type not in RESOURCE_TYPES:
        body.type = "article"
    item = DiscoveryItem(
        user_id=current_user.id,
        title=body.title.strip(),
        url=body.url.strip(),
        type=body.type,
        summary=body.summary.strip(),
        source=body.source.strip(),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return DiscoveryItemOut(
        id=item.id, title=item.title, url=item.url, type=item.type,
        summary=item.summary, source=item.source, saved=True,
    )


@router.delete("/saved/{item_id}")
async def unsave_discovery(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        delete(DiscoveryItem).where(
            DiscoveryItem.id == item_id,
            DiscoveryItem.user_id == current_user.id,
        )
    )
    await db.commit()
    if not result.rowcount:
        raise HTTPException(status_code=404, detail="收藏不存在")
    return {"message": "已取消收藏"}
