"""PPT 教学视频生成 Agent"""
import os
import json
import asyncio
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.agents.utils import extract_json, normalize_resource_content
from app.core.config import settings
from app.core.logger import log
from app.core.ppt_video_config import MIN_PAGES, MAX_PAGES


class PptVideoAgent(BaseAgent):
    """PPT 教学视频生成 Agent

    流程：LLM 生成 PPT 内容 → Playwright 渲染 → TTS 合成 → FFmpeg 合成 → OSS 上传
    """
    agent_name = "ppt_video"
    PROMPT_PATH = "prompts/ppt_video_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)

    async def run(
        self,
        topic: str,
        stage_id: int = None,
        user_id: int = None,
        skip_cache: bool = False,
        on_progress=None,
    ) -> Dict[str, Any]:
        """生成 PPT 教学视频"""
        log.info(f"PptVideoAgent 开始: topic={topic}, user={user_id}")

        # 先查缓存
        if user_id and self.db and not skip_cache:
            existing = await self._get_from_db(user_id, stage_id, topic)
            if existing:
                log.info(f"PPT 视频命中缓存: topic={topic}")
                return existing

        # Step 1: LLM 生成 PPT 内容
        if on_progress:
            on_progress("generating_pages", 0.0)
        pages = await self._generate_pages(topic, user_id)
        if on_progress:
            on_progress("generating_pages", 1.0)

        if not pages:
            return {"success": False, "error": "LLM 未生成有效的 PPT 页面"}

        # 保存调试文件（JSON + HTML）
        self._save_debug_output(pages, user_id, stage_id)

        # Step 2: 视频合成
        output_path = os.path.join(
            settings.PPT_VIDEO_TEMP_DIR,
            f"output_{user_id or 0}_{stage_id or 0}.mp4",
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        from app.multimodal.ppt_video_generator import ppt_video_generator

        def _gen_progress(step, progress):
            step_map = {
                "rendering_html": ("rendering_html", 0.3 + progress * 0.15),
                "synthesizing_tts": ("synthesizing_tts", 0.45 + progress * 0.2),
                "generating_subtitles": ("generating_subtitles", 0.65 + progress * 0.05),
                "composing_video": ("composing_video", 0.7 + progress * 0.25),
            }
            if on_progress and step in step_map:
                on_progress(*step_map[step])

        result = await ppt_video_generator.generate(
            pages=pages,
            output_path=output_path,
            on_progress=_gen_progress,
        )

        if not result.get("success"):
            return result

        # Step 3: 上传 OSS
        if on_progress:
            on_progress("uploading", 0.9)
        from app.multimodal.oss_uploader import oss_uploader
        oss_result = await oss_uploader.upload_video(
            output_path, user_id=user_id or 0, stage_id=stage_id or 0,
        )
        if on_progress:
            on_progress("uploading", 1.0)

        if not oss_result.get("success"):
            log.warning(f"OSS 上传失败: {oss_result.get('error')}，视频保存在本地")
            return {
                "success": True,
                "video_url": f"file://{output_path}",
                "duration_seconds": result["duration_seconds"],
                "pages_count": len(pages),
                "oss_key": "",
            }

        # Step 4: 保存到数据库
        video_url = oss_result["url"]
        etag = oss_result.get("etag", "")
        if etag:
            video_url += f"?v={etag}"

        video_data = {
            "video_url": video_url,
            "duration_seconds": result["duration_seconds"],
            "pages_count": len(pages),
            "oss_key": oss_result["oss_key"],
        }

        if user_id and self.db and stage_id:
            await self._save_to_db(user_id, stage_id, topic, video_data)

        # 清理临时文件
        self._cleanup(output_path)

        log.info(f"PptVideoAgent 完成: {oss_result['url']}")
        return video_data

    async def _generate_pages(self, topic: str, user_id: int = None) -> list:
        """调用 LLM 生成 PPT 页面内容（带重试）"""
        profile = None
        if user_id and self.db:
            try:
                profile = await self._get_profile(user_id)
            except Exception as e:
                log.warning(f"获取画像失败(不影响生成): {e}")

        try:
            prompt = self._load_and_format_prompt(topic, profile)
        except Exception as e:
            log.error(f"PPT prompt 格式化失败: {e}, topic={topic}")
            prompt = self._load_prompt(self.PROMPT_PATH).replace("{topic}", topic).replace("{profile_context}", "")

        for attempt in range(2):
            response = await self._call_llm(prompt)
            pages = self._extract_pages(response)
            if pages:
                break
            log.warning(f"PPT 页面解析失败 (第{attempt+1}次)，响应前500字符: {response[:500]}")

        if not pages:
            log.warning("LLM 输出解析失败，使用 fallback 页面")
            pages = self._get_fallback_pages(topic)

        pages = pages[:MAX_PAGES]
        if len(pages) < MIN_PAGES:
            log.warning(f"LLM 只生成了 {len(pages)} 页，少于最低要求 {MIN_PAGES}")

        return pages

    def _save_debug_output(self, pages: list, user_id, stage_id):
        """保存调试文件：pages.json + html_pages/*.html"""
        try:
            debug_dir = os.path.join(
                settings.PPT_VIDEO_TEMP_DIR,
                "debug",
                f"{user_id or 0}_{stage_id or 0}",
            )
            os.makedirs(debug_dir, exist_ok=True)

            # 保存 pages.json
            json_path = os.path.join(debug_dir, "pages.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(pages, f, ensure_ascii=False, indent=2)
            log.info(f"PPT 调试 pages.json 已保存: {json_path}, {len(pages)} 页")

            # 渲染并保存 HTML
            from app.multimodal.ppt_templates import render_ppt_page
            html_dir = os.path.join(debug_dir, "html_pages")
            os.makedirs(html_dir, exist_ok=True)
            for i, page in enumerate(pages):
                try:
                    html = render_ppt_page(page.get("template", "content"), page.get("content", {}))
                    html_path = os.path.join(html_dir, f"page_{i}.html")
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html)
                except Exception as e:
                    log.warning(f"调试 HTML 渲染失败 (第{i+1}页): {e}")

            log.info(f"PPT 调试文件已保存: {debug_dir}")
        except Exception as e:
            log.warning(f"保存调试文件失败: {e}")

    def _extract_pages(self, response: str) -> list:
        """从 LLM 响应中提取 PPT 页面 JSON 数组"""
        # 兼容旧模板名到新模板名的映射
        template_alias = {
            "title_bullets": "content",
            "title_code": "code_example",
        }

        try:
            data = json.loads(response)
            if isinstance(data, list):
                return self._normalize_pages(data, template_alias)
            if isinstance(data, dict) and "pages" in data:
                return self._normalize_pages(data["pages"], template_alias)
        except json.JSONDecodeError:
            pass

        data = extract_json(response)
        if isinstance(data, list):
            return self._normalize_pages(data, template_alias)
        if isinstance(data, dict) and "pages" in data:
            return self._normalize_pages(data["pages"], template_alias)

        return []

    def _normalize_pages(self, pages: list, template_alias: dict) -> list:
        """标准化页面数据：映射旧模板名、补全缺失字段"""
        valid_templates = {"title_page", "content", "code_example", "comparison", "section_divider", "summary"}
        result = []
        for page in pages:
            if not isinstance(page, dict):
                continue
            try:
                t = page.get("template", "content")
                page["template"] = template_alias.get(t, t)
                if page["template"] not in valid_templates:
                    page["template"] = "content"
                content = page.get("content")
                if not isinstance(content, dict):
                    page["content"] = {
                        "title": page.get("title", ""),
                        "bullets": page.get("bullets", []),
                        "accent_color": page.get("accent_color", "#4F46E5"),
                    }
                if "title" not in page["content"]:
                    page["content"]["title"] = ""
                result.append(page)
            except Exception as e:
                log.warning(f"跳过格式异常的 PPT 页面: {e}, page={str(page)[:200]}")
                continue
        return result

    def _get_fallback_pages(self, topic: str) -> list:
        """LLM 失败时的 fallback 页面"""
        return [
            {
                "page_id": 1,
                "template": "title_page",
                "content": {
                    "title": topic,
                    "subtitle": "AI 个性化学习系统",
                    "accent_color": "#6366f1",
                },
                "script": f"大家好，欢迎来到本节课程。今天我们将一起学习{topic}的相关知识。",
            },
            {
                "page_id": 2,
                "template": "content",
                "content": {
                    "title": f"{topic} — 核心概念",
                    "bullets": [
                        "基本概念与定义",
                        "核心原理与机制",
                        "实际应用场景",
                    ],
                    "accent_color": "#4F46E5",
                },
                "script": f"首先来看{topic}的核心概念。我们将从基本定义出发，逐步深入理解其原理和应用。",
            },
            {
                "page_id": 3,
                "template": "content",
                "content": {
                    "title": f"{topic} — 关键要点",
                    "bullets": [
                        "重点知识梳理",
                        "常见误区与注意事项",
                        "最佳实践建议",
                    ],
                    "accent_color": "#2563eb",
                },
                "script": f"接下来我们梳理{topic}的关键要点，帮助大家建立完整的知识框架。",
            },
            {
                "page_id": 4,
                "template": "summary",
                "content": {
                    "title": "本节小结",
                    "points": [
                        f"{topic}的核心概念",
                        "关键原理与应用",
                        "下节预告：进阶内容",
                    ],
                    "accent_color": "#4F46E5",
                },
                "script": f"本节我们学习了{topic}的基础知识。下节课我们将深入探讨更多细节和实际应用。",
            },
        ]

    async def _get_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取学生画像"""
        from app.models import StudentProfile
        try:
            result = await self.db.execute(
                select(StudentProfile).where(
                    StudentProfile.user_id == user_id,
                    StudentProfile.is_active == True,
                )
            )
            profile = result.scalar_one_or_none()
            if profile:
                return {
                    "major": profile.major or "",
                    "grade": profile.grade or "",
                    "goal": profile.goal or "",
                    "knowledge_level": profile.knowledge_level or "",
                    "learning_style": profile.learning_style or "",
                    "weakness": profile.weakness or [],
                }
        except Exception as e:
            log.warning(f"获取学生画像失败: {e}")
        return None

    def _load_and_format_prompt(self, topic: str, profile: Dict = None) -> str:
        """加载并格式化 Prompt"""
        template = self._load_prompt(self.PROMPT_PATH)

        if profile:
            weakness_str = ", ".join(profile.get("weakness", [])) or "无"
            profile_context = f"""
## 学生画像信息
- 专业：{profile.get('major', '未知')}
- 年级：{profile.get('grade', '未知')}
- 知识水平：{profile.get('knowledge_level', '未知')}
- 学习风格：{profile.get('learning_style', '未知')}
- 薄弱点：{weakness_str}

请根据学生知识水平调整讲解深度和术语使用。
"""
        else:
            profile_context = ""

        return self._format_prompt(template, topic=topic, profile_context=profile_context)

    async def _get_from_db(self, user_id: int, stage_id: int, topic: str) -> Optional[Dict]:
        """从数据库获取已生成的 PPT 视频"""
        from app.models import LearningResource
        try:
            query = select(LearningResource).where(
                LearningResource.user_id == user_id,
                LearningResource.resource_type == "ppt_video",
            )
            if stage_id:
                query = query.where(LearningResource.stage_id == stage_id)
            else:
                query = query.where(LearningResource.topic == topic)

            result = await self.db.execute(query.order_by(LearningResource.created_at.desc()).limit(1))
            record = result.scalar_one_or_none()
            if record and record.content:
                content = record.content
                if isinstance(content, dict):
                    content = normalize_resource_content(content, "ppt_video")
                return content
        except Exception as e:
            log.warning(f"查询 PPT 视频缓存失败: {e}")
        return None

    async def _save_to_db(self, user_id: int, stage_id: int, topic: str, video_data: dict, profile_id: int = None):
        """保存视频记录到数据库（upsert）"""
        from app.models import LearningResource, StudentProfile
        from sqlalchemy import select
        from app.models.upsert import upsert as mysql_upsert
        try:
            if not profile_id and self.db:
                result = await self.db.execute(
                    select(StudentProfile).where(
                        StudentProfile.user_id == user_id,
                        StudentProfile.is_active == True,
                    )
                )
                prof = result.scalar_one_or_none()
                profile_id = prof.id if prof else None
            # 清除旧的 quality_score，确保重新评估
            clean_content = dict(video_data) if isinstance(video_data, dict) else video_data
            if isinstance(clean_content, dict):
                clean_content.pop("quality_score", None)
                clean_content.pop("security_flag", None)
            await mysql_upsert(self.db, LearningResource.__table__, values={
                "user_id": user_id,
                "profile_id": profile_id,
                "stage_id": stage_id,
                "topic": topic,
                "resource_type": "ppt_video",
                "content": clean_content,
            })
            await self.db.commit()
            log.info(f"PPT 视频记录已保存: user={user_id}, stage={stage_id}")
        except Exception as e:
            log.error(f"保存 PPT 视频记录失败: {e}")
            await self.db.rollback()

    def _cleanup(self, output_path: str):
        """清理临时文件"""
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
                log.debug(f"清理临时文件: {output_path}")
        except Exception as e:
            log.warning(f"清理临时文件失败: {e}")
