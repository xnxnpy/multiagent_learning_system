"""PPT 视频生成器：Playwright 渲染 + 讯飞 TTS + FFmpeg 合成"""
import os
import sys
import asyncio
import subprocess
import tempfile
from typing import Dict, Any, List, Optional, Callable
from app.core.config import settings
from app.core.logger import log
from app.core.ppt_video_config import (
    RENDER_WIDTH, RENDER_HEIGHT,
    FFMPEG_CODEC_VIDEO, FFMPEG_CODEC_AUDIO, FFMPEG_TUNE, FFMPEG_PIX_FMT,
    SUBTITLE_FONT_SIZE, SUBTITLE_FONT_NAME, SUBTITLE_MARGIN_V, SUBTITLE_OUTLINE,
    MIN_PAGES, MAX_PAGES,
)
from app.multimodal.ppt_templates import render_ppt_page
from app.multimodal.tts_client import xunfei_tts
from app.multimodal.subtitle_generator import generate_srt


class PptVideoGenerator:
    """PPT 页面 -> MP4 视频生成器"""

    def __init__(self, temp_dir: str = None):
        self.temp_dir = temp_dir or settings.PPT_VIDEO_TEMP_DIR

    def _ensure_temp_dir(self, work_dir: str):
        os.makedirs(work_dir, exist_ok=True)

    def _build_segments_plan(self, pages: List[Dict]) -> List[Dict]:
        """构建每个页面的文件路径计划"""
        plan = []
        for i, page in enumerate(pages):
            page_id = page.get("page_id", i + 1)
            plan.append({
                "page_id": page_id,
                "template": page.get("template", "title_bullets"),
                "content": page.get("content", {}),
                "script": page.get("script", ""),
                "png_path": f"page_{i}.png",
                "mp3_path": f"page_{i}.mp3",
                "srt_path": f"page_{i}.srt",
                "segment_path": f"segment_{i}.mp4",
            })
        return plan

    def _build_concat_file_content(self, segments: List[Dict]) -> str:
        """构建 FFmpeg concat demuxer 文件内容"""
        lines = []
        for seg in segments:
            abs_path = os.path.abspath(seg["segment_path"]).replace("\\", "/")
            lines.append(f"file '{abs_path}'")
        return "\n".join(lines)

    def _estimate_duration_from_text(self, text: str, chars_per_second: float = 4.0) -> float:
        """根据文本长度估算时长（备用方案）"""
        import re
        clean = re.sub(r"[^一-龥a-zA-Z0-9]", "", text)
        return max(2.0, len(clean) / chars_per_second)

    async def generate(
        self,
        pages: List[Dict],
        output_path: str,
        on_progress: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """生成完整教学视频"""
        if not pages:
            return {"success": False, "error": "PPT 页面列表为空"}

        pages = pages[:MAX_PAGES]

        work_dir = tempfile.mkdtemp(prefix="ppt_video_", dir=self.temp_dir)
        self._ensure_temp_dir(work_dir)

        plan = self._build_segments_plan(pages)
        log.info(f"PPT 视频生成开始: {len(plan)} 页, 工作目录: {work_dir}")

        try:
            # Step 1: 渲染 HTML -> PNG
            if on_progress:
                on_progress("rendering_html", 0.0)
            await self._render_all_html(plan, work_dir)
            if on_progress:
                on_progress("rendering_html", 1.0)

            # Step 2: TTS 生成音频
            if on_progress:
                on_progress("synthesizing_tts", 0.0)
            durations = await self._generate_all_tts(plan, work_dir)
            if on_progress:
                on_progress("synthesizing_tts", 1.0)

            # Step 3: 生成字幕
            if on_progress:
                on_progress("generating_subtitles", 0.0)
            self._generate_all_subtitles(plan, durations, work_dir)
            if on_progress:
                on_progress("generating_subtitles", 1.0)

            # Step 4: 合成每个片段
            if on_progress:
                on_progress("composing_video", 0.0)
            self._compose_all_segments(plan, work_dir)
            if on_progress:
                on_progress("composing_video", 1.0)

            # Step 5: 拼接所有片段
            total_duration = self._concat_segments(plan, output_path, work_dir)

            log.info(f"PPT 视频合成完成: {output_path}, 时长: {total_duration:.1f}秒")
            return {
                "success": True,
                "output_path": output_path,
                "duration_seconds": round(total_duration, 1),
            }

        except Exception as e:
            log.error(f"PPT 视频生成失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _render_all_html(self, plan: List[Dict], work_dir: str):
        """Playwright 渲染所有 HTML 页面为 PNG（在独立线程中运行，绕过 uvicorn 的 SelectorEventLoop）"""
        import asyncio
        import threading

        log.info("Playwright 渲染 HTML -> PNG 开始（独立线程模式）")

        def _render_in_thread():
            """在独立线程中用 ProactorEventLoop 运行 Playwright"""
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._do_render(plan, work_dir))
            finally:
                loop.close()

        await asyncio.get_event_loop().run_in_executor(None, _render_in_thread)
        log.info("Playwright 渲染完成")

    async def _do_render(self, plan: List[Dict], work_dir: str):
        """实际的 Playwright 渲染逻辑"""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                args=["--no-sandbox", "--disable-gpu"]
            )
            page = await browser.new_page(
                viewport={"width": RENDER_WIDTH, "height": RENDER_HEIGHT}
            )

            for i, item in enumerate(plan):
                html = render_ppt_page(item["template"], item["content"])
                png_path = os.path.join(work_dir, item["png_path"])

                await page.set_content(html, wait_until="networkidle")
                await page.screenshot(path=png_path, full_page=False)
                log.debug(f"渲染第 {i+1}/{len(plan)} 页: {item['png_path']}")

            await browser.close()
        log.info("Playwright 渲染完成")

    async def _generate_all_tts(self, plan: List[Dict], work_dir: str) -> List[float]:
        """为所有页面生成 TTS 音频，返回每页音频时长"""
        log.info("TTS 语音合成开始")
        durations = []

        for i, item in enumerate(plan):
            script = item.get("script", "")
            if not script:
                log.warning(f"第 {i+1} 页无讲解文案，使用占位音频")
                durations.append(5.0)
                continue

            try:
                audio_data = await xunfei_tts.synthesize(script)
                mp3_path = os.path.join(work_dir, item["mp3_path"])
                with open(mp3_path, "wb") as f:
                    f.write(audio_data)

                duration = self._get_audio_duration(mp3_path)
                durations.append(duration)
                log.debug(f"第 {i+1} 页 TTS 完成，时长: {duration:.1f}s")

            except Exception as e:
                log.error(f"第 {i+1} 页 TTS 失败: {e}，使用估算时长")
                duration = self._estimate_duration_from_text(script)
                durations.append(duration)

        log.info("TTS 语音合成完成")
        return durations

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长（通过 ffprobe）"""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    audio_path,
                ],
                capture_output=True, text=True, timeout=10,
            )
            return float(result.stdout.strip())
        except Exception:
            file_size = os.path.getsize(audio_path)
            return max(2.0, file_size / 2000)

    def _generate_all_subtitles(self, plan: List[Dict], durations: List[float], work_dir: str):
        """为所有页面生成 SRT 字幕文件"""
        log.info("字幕生成开始")
        for i, (item, duration) in enumerate(zip(plan, durations)):
            script = item.get("script", "")
            srt_content = generate_srt(script, duration)
            srt_path = os.path.join(work_dir, item["srt_path"])
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            log.debug(f"第 {i+1} 页字幕生成完成")
        log.info("字幕生成完成")

    def _compose_all_segments(self, plan: List[Dict], work_dir: str):
        """FFmpeg 合成每个页面的视频片段"""
        log.info("FFmpeg 片段合成开始")

        for i, item in enumerate(plan):
            png_path = os.path.join(work_dir, item["png_path"])
            mp3_path = os.path.join(work_dir, item["mp3_path"])
            srt_path = os.path.join(work_dir, item["srt_path"])
            segment_path = os.path.join(work_dir, item["segment_path"])

            duration = self._get_audio_duration(mp3_path)

            vf_parts = []
            if os.path.exists(srt_path) and os.path.getsize(srt_path) > 10:
                srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
                vf_parts.append(
                    f"subtitles='{srt_escaped}':force_style='"
                    f"FontSize={SUBTITLE_FONT_SIZE},"
                    f"FontName={SUBTITLE_FONT_NAME},"
                    f"MarginV={SUBTITLE_MARGIN_V},"
                    f"Outline={SUBTITLE_OUTLINE}'"
                )

            vf = ",".join(vf_parts) if vf_parts else f"scale={RENDER_WIDTH}:{RENDER_HEIGHT}"

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", png_path,
                "-i", mp3_path,
                "-c:v", FFMPEG_CODEC_VIDEO,
                "-tune", FFMPEG_TUNE,
                "-c:a", FFMPEG_CODEC_AUDIO,
                "-t", str(duration + 0.5),
                "-pix_fmt", FFMPEG_PIX_FMT,
                "-vf", vf,
                "-shortest",
                segment_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                log.error(f"FFmpeg 片段合成失败 (第{i+1}页): {result.stderr[:500]}")
                raise RuntimeError(f"FFmpeg 合成第 {i+1} 页失败: {result.stderr[:200]}")

            log.debug(f"第 {i+1}/{len(plan)} 片段合成完成")

        log.info("FFmpeg 片段合成完成")

    def _concat_segments(self, plan: List[Dict], output_path: str, work_dir: str) -> float:
        """拼接所有视频片段为最终 MP4"""
        log.info("FFmpeg 拼接开始")

        segments_for_concat = []
        for item in plan:
            abs_seg = os.path.join(work_dir, item["segment_path"])
            segments_for_concat.append({"segment_path": abs_seg})

        concat_file = os.path.join(work_dir, "filelist.txt")
        with open(concat_file, "w", encoding="utf-8") as f:
            f.write(self._build_concat_file_content(segments_for_concat))

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg 拼接失败: {result.stderr[:300]}")

        total_duration = self._get_audio_duration(output_path)
        log.info(f"FFmpeg 拼接完成: {output_path}, 时长: {total_duration:.1f}s")
        return total_duration


# 全局实例
ppt_video_generator = PptVideoGenerator()
