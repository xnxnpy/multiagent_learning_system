# -*- coding: utf-8 -*-
"""
PPT 视频生成 - 独立测试脚本
用法：
  conda activate multi_agent
  python test_ppt_video.py                       # 默认主题
  python test_ppt_video.py "Python列表推导式"      # 指定主题

前置条件：
  - .env 文件已配置（讯飞 API 密钥）
  - playwright install chromium
  - FFmpeg 已安装并在 PATH 中
"""
import asyncio
import os
import json
import time

# ── 初始化路径 ──
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from app.core.logger import log
from app.core.model_manager import model_manager
from app.agents.utils import extract_json
from app.multimodal.ppt_templates import render_ppt_page
from app.multimodal.ppt_video_generator import ppt_video_generator
from app.core.ppt_video_config import MIN_PAGES, MAX_PAGES

DEFAULT_TOPIC = "Python列表推导式"
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "test_output")
TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_step(text):
    print(f"\n>> {text}")


# ─────────────────────────────────────────────────────
# Step 1: 调用 LLM 生成 PPT 页面
# ─────────────────────────────────────────────────────
async def step1_generate_pages(topic):
    print_step("Step 1: 调用 LLM 生成 PPT 页面...")

    prompt_path = os.path.join(PROJECT_ROOT, "prompts", "ppt_video_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    prompt = template.replace("{topic}", topic).replace("{profile_context}", "")
    print(f"  主题: {topic}")
    print(f"  正在调用 LLM (agent=ppt_video)...")

    t0 = time.time()
    messages = [{"role": "user", "content": prompt}]
    response = await model_manager.chat(
        messages,
        agent_name="ppt_video",
        temperature=0.7,
        max_tokens=8192,
    )
    elapsed = time.time() - t0
    print(f"  LLM 响应耗时: {elapsed:.1f}s，长度: {len(response)} 字符")

    # 解析 JSON
    pages = None
    try:
        parsed = json.loads(response)
        pages = parsed if isinstance(parsed, list) else parsed.get("pages", [])
    except json.JSONDecodeError:
        pages = extract_json(response)

    if not isinstance(pages, list) or not pages:
        print("\n  [ERROR] JSON 解析失败，LLM 原始响应：")
        print(response[:3000])
        return []

    # 兼容旧模板名 + 校验
    alias = {"title_bullets": "content", "title_code": "code_example"}
    valid = {"title_page", "content", "code_example", "comparison", "section_divider", "summary"}
    for p in pages:
        if not isinstance(p, dict):
            continue
        t = p.get("template", "content")
        p["template"] = alias.get(t, t)
        if p["template"] not in valid:
            p["template"] = "content"
        if "content" not in p or not isinstance(p["content"], dict):
            p["content"] = {"title": "", "bullets": [], "accent_color": "#4F46E5"}

    pages = pages[:MAX_PAGES]
    print(f"  成功解析 {len(pages)} 页：")
    for i, p in enumerate(pages):
        t = p.get("template", "?")
        title = p.get("content", {}).get("title", "(无)")
        extra = ""
        if t == "code_example":
            code = p["content"].get("code", "")
            lines = code.count("\\n") + 1 if "\\n" in code else code.count("\n") + 1
            extra = f"  [代码 {lines} 行]"
        elif t in ("content", "summary"):
            items = p["content"].get("bullets") or p["content"].get("points", [])
            extra = f"  [{len(items)} 条]"
        print(f"    [{i+1}] {t:20s} | {title}{extra}")

    return pages


# ─────────────────────────────────────────────────────
# Step 2: 保存 HTML + PNG（方便浏览器预览）
# ─────────────────────────────────────────────────────
def step2_save_html(pages):
    print_step("Step 2: 渲染 HTML 页面...")
    html_dir = os.path.join(OUTPUT_DIR, "html_pages")
    os.makedirs(html_dir, exist_ok=True)

    paths = []
    for i, page in enumerate(pages):
        template = page.get("template", "content")
        content = page.get("content", {})
        try:
            html = render_ppt_page(template, content)
        except Exception as e:
            print(f"  [WARN] 第{i+1}页渲染失败: {e}")
            continue
        html_path = os.path.join(html_dir, f"page_{i}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        paths.append(html_path)

    print(f"  已保存 {len(paths)} 个 HTML 到: {html_dir}")
    print("  >>> 用浏览器打开 HTML 文件可直接预览效果 <<<")
    return paths


async def step3_render_png(pages):
    print_step("Step 3: Playwright 渲染 PNG...")
    os.makedirs(TEMP_DIR, exist_ok=True)

    plan = []
    for i, page in enumerate(pages):
        plan.append({
            "page_id": page.get("page_id", i + 1),
            "template": page.get("template", "content"),
            "content": page.get("content", {}),
            "script": page.get("script", ""),
            "png_path": f"page_{i}.png",
            "mp3_path": f"page_{i}.mp3",
            "srt_path": f"page_{i}.srt",
            "segment_path": f"segment_{i}.mp4",
        })

    t0 = time.time()
    await ppt_video_generator._render_all_html(plan, TEMP_DIR)
    print(f"  渲染完成 ({time.time()-t0:.1f}s)")

    for item in plan:
        png = os.path.join(TEMP_DIR, item["png_path"])
        if os.path.exists(png):
            print(f"    {item['png_path']}  {os.path.getsize(png)/1024:.0f} KB")
        else:
            print(f"    [MISS] {item['png_path']}")
    return plan


# ─────────────────────────────────────────────────────
# Step 4: TTS 语音合成
# ─────────────────────────────────────────────────────
async def step4_tts(plan):
    print_step("Step 4: TTS 语音合成...")
    t0 = time.time()
    durations = await ppt_video_generator._generate_all_tts(plan, TEMP_DIR)
    print(f"  TTS 完成 ({time.time()-t0:.1f}s)")
    total = 0
    for i, d in enumerate(durations):
        total += d
        print(f"    第{i+1}页: {d:.1f}s")
    print(f"  总时长: {total:.1f}s")
    return durations


# ─────────────────────────────────────────────────────
# Step 5: 字幕生成
# ─────────────────────────────────────────────────────
def step5_subtitles(plan, durations):
    print_step("Step 5: 生成字幕...")
    ppt_video_generator._generate_all_subtitles(plan, durations, TEMP_DIR)
    for item in plan:
        srt = os.path.join(TEMP_DIR, item["srt_path"])
        if os.path.exists(srt):
            print(f"    {item['srt_path']}  {os.path.getsize(srt)} bytes")
    print("  字幕生成完成")


# ─────────────────────────────────────────────────────
# Step 6: FFmpeg 合成视频
# ─────────────────────────────────────────────────────
def step6_compose(plan):
    print_step("Step 6: FFmpeg 合成视频片段...")
    t0 = time.time()
    ppt_video_generator._compose_all_segments(plan, TEMP_DIR)
    print(f"  片段合成完成 ({time.time()-t0:.1f}s)")

    print_step("Step 7: 拼接最终视频...")
    output_path = os.path.join(OUTPUT_DIR, "output.mp4")
    t0 = time.time()
    total_duration = ppt_video_generator._concat_segments(plan, output_path, TEMP_DIR)
    elapsed = time.time() - t0
    print(f"  拼接完成 ({elapsed:.1f}s)")
    print(f"  总时长: {total_duration:.1f}s")

    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  文件大小: {size_mb:.1f} MB")
    return output_path


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────
async def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOPIC

    print_header("PPT 视频生成测试")
    print(f"  主题: {topic}")
    print(f"  输出: {OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    t_start = time.time()

    # 1. LLM 生成页面
    pages = await step1_generate_pages(topic)
    if not pages:
        print("\n[FAIL] LLM 未生成有效页面，退出")
        return

    # 保存 JSON（方便调试）
    pages_json = os.path.join(OUTPUT_DIR, "pages.json")
    with open(pages_json, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    print(f"\n  页面 JSON -> {pages_json}")

    # 2. HTML 预览
    step2_save_html(pages)

    # 3. PNG 渲染
    plan = await step3_render_png(pages)

    # 4. TTS
    durations = await step4_tts(plan)

    # 5. 字幕
    step5_subtitles(plan, durations)

    # 6. 合成视频
    output = step6_compose(plan)

    total_elapsed = time.time() - t_start
    print_header("完成！")
    print(f"  视频文件:    {output}")
    print(f"  HTML 预览:   {os.path.join(OUTPUT_DIR, 'html_pages')}")
    print(f"  页面 JSON:   {pages_json}")
    print(f"  总耗时:      {total_elapsed:.1f}s")
    print(f"\n  提示: 先打开 html_pages/page_0.html 确认视觉效果，")
    print(f"        满意后再生成完整视频（LLM + TTS 耗时较长）")


if __name__ == "__main__":
    asyncio.run(main())
