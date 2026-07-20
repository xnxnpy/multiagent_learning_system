"""PPT HTML 模板系统：6 种模板，专业视觉设计"""
from typing import Dict, Any

# 模板类型常量
TITLE_PAGE = "title_page"
CONTENT = "content"
CODE_EXAMPLE = "code_example"
COMPARISON = "comparison"
SECTION_DIVIDER = "section_divider"
SUMMARY = "summary"

_TEMPLATE_MAP = {
    TITLE_PAGE: "_render_title_page",
    CONTENT: "_render_content",
    CODE_EXAMPLE: "_render_code_example",
    COMPARISON: "_render_comparison",
    SECTION_DIVIDER: "_render_section_divider",
    SUMMARY: "_render_summary",
}

# ── 共享基础样式 ──
_BASE_STYLE = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1280px; height: 720px;
    font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif;
    overflow: hidden;
  }
</style>
"""


def _safe_html(text: str) -> str:
    """HTML 转义"""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_code_block(code: str, language: str) -> str:
    """统一的代码块渲染，正确处理换行和转义"""
    escaped = _safe_html(code)
    # JSON 中的 \\n → <br>，实际换行 → <br>
    escaped = escaped.replace("\\n", "<br>").replace("\n", "<br>")
    # 多个连续 br 合并
    while "<br><br>" in escaped:
        escaped = escaped.replace("<br><br>", "<br>")
    return escaped


# ── 1. 标题页 ──
def _render_title_page(content: Dict[str, Any]) -> str:
    title = _safe_html(content.get("title", ""))
    subtitle = _safe_html(content.get("subtitle", ""))
    accent = content.get("accent_color", "#6366f1")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">{_BASE_STYLE}
<style>
  .slide {{
    width: 1280px; height: 720px;
    background: linear-gradient(135deg, {accent} 0%, #1e1b4b 100%);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    position: relative; overflow: hidden;
  }}
  .bg-circle-1 {{
    position: absolute; width: 400px; height: 400px; border-radius: 50%;
    background: rgba(255,255,255,0.06); top: -120px; right: -80px;
  }}
  .bg-circle-2 {{
    position: absolute; width: 300px; height: 300px; border-radius: 50%;
    background: rgba(255,255,255,0.04); bottom: -100px; left: -60px;
  }}
  .line {{ width: 80px; height: 4px; border-radius: 2px; background: rgba(255,255,255,0.6); margin-bottom: 36px; }}
  .title {{
    font-size: 52px; font-weight: 900; color: #fff; text-align: center;
    line-height: 1.3; max-width: 1000px; letter-spacing: 2px;
  }}
  .subtitle {{
    font-size: 22px; color: rgba(255,255,255,0.75); text-align: center;
    margin-top: 28px; max-width: 800px; line-height: 1.6;
  }}
  .bottom-tag {{
    position: absolute; bottom: 36px; font-size: 14px;
    color: rgba(255,255,255,0.4); letter-spacing: 4px; text-transform: uppercase;
  }}
</style></head>
<body>
<div class="slide">
  <div class="bg-circle-1"></div>
  <div class="bg-circle-2"></div>
  <div class="line"></div>
  <div class="title">{title}</div>
  {"<div class='subtitle'>" + subtitle + "</div>" if subtitle else ""}
  <div class="bottom-tag">AI 个性化学习系统</div>
</div>
</body></html>"""


# ── 2. 内容页（标题 + 要点列表） ──
def _render_content(content: Dict[str, Any]) -> str:
    title = _safe_html(content.get("title", ""))
    bullets = content.get("bullets", [])
    accent = content.get("accent_color", "#4F46E5")

    bullets_html = "\n".join(
        f'<div class="bullet-item">'
        f'<span class="bullet-dot" style="background:{accent}"></span>'
        f'<span class="bullet-text">{_safe_html(b)}</span>'
        f'</div>'
        for b in bullets
    ) if bullets else '<div class="empty-hint">本页暂无要点</div>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">{_BASE_STYLE}
<style>
  .slide {{
    width: 1280px; height: 720px; background: #f8fafc;
    display: flex; position: relative; overflow: hidden;
  }}
  .left-bar {{ width: 8px; background: {accent}; border-radius: 0 4px 4px 0; }}
  .main {{ flex: 1; padding: 52px 60px 40px 56px; display: flex; flex-direction: column; }}
  .top-line {{ width: 60px; height: 4px; border-radius: 2px; background: {accent}; margin-bottom: 18px; }}
  .title {{ font-size: 34px; font-weight: 700; color: #1e293b; margin-bottom: 36px; line-height: 1.3; }}
  .bullets {{ display: flex; flex-direction: column; gap: 18px; }}
  .bullet-item {{ display: flex; align-items: flex-start; gap: 16px; }}
  .bullet-dot {{
    width: 10px; height: 10px; border-radius: 50%; margin-top: 9px; flex-shrink: 0;
  }}
  .bullet-text {{ font-size: 22px; color: #334155; line-height: 1.75; }}
  .empty-hint {{ font-size: 18px; color: #94a3b8; font-style: italic; }}
  .bg-deco {{
    position: absolute; bottom: 0; right: 0; width: 200px; height: 200px;
    border-radius: 50% 0 0 0; background: {accent}; opacity: 0.04;
  }}
  .page-num {{
    position: absolute; bottom: 20px; right: 30px;
    font-size: 13px; color: #94a3b8;
  }}
</style></head>
<body>
<div class="slide">
  <div class="left-bar"></div>
  <div class="main">
    <div class="top-line"></div>
    <div class="title">{title}</div>
    <div class="bullets">{bullets_html}</div>
  </div>
  <div class="bg-deco"></div>
</div>
</body></html>"""


# ── 3. 代码示例页 ──
def _render_code_example(content: Dict[str, Any]) -> str:
    title = _safe_html(content.get("title", ""))
    code = content.get("code", "")
    language = _safe_html(content.get("language", "python"))
    caption = _safe_html(content.get("caption", ""))
    code_html = _render_code_block(code, language)

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">{_BASE_STYLE}
<style>
  .slide {{
    width: 1280px; height: 720px; background: #f8fafc;
    display: flex; position: relative; overflow: hidden;
  }}
  .left-bar {{ width: 8px; background: #059669; border-radius: 0 4px 4px 0; }}
  .main {{ flex: 1; padding: 44px 50px 30px 48px; display: flex; flex-direction: column; }}
  .top-line {{ width: 60px; height: 4px; border-radius: 2px; background: #059669; margin-bottom: 14px; }}
  .title {{ font-size: 30px; font-weight: 700; color: #1e293b; margin-bottom: 20px; line-height: 1.3; }}
  .code-block {{
    background: #1e1e2e; border-radius: 12px; padding: 22px 26px;
    flex: 1; overflow: hidden; position: relative;
    border: 1px solid #313244;
  }}
  .code-header {{
    display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
    padding-bottom: 10px; border-bottom: 1px solid #313244;
  }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; }}
  .dot-r {{ background: #f38ba8; }}
  .dot-y {{ background: #f9e2af; }}
  .dot-g {{ background: #a6e3a1; }}
  .code-lang {{
    margin-left: 10px; font-size: 12px; color: #6c7086;
    font-family: monospace; text-transform: uppercase; letter-spacing: 1px;
  }}
  .code-content {{
    color: #cdd6f4; font-family: "Cascadia Code", "Fira Code", Consolas, monospace;
    font-size: 15px; line-height: 1.65; white-space: pre-wrap; word-break: normal;
    overflow: hidden;
  }}
  .code-content br {{ margin-bottom: 2px; }}
  .caption {{
    font-size: 13px; color: #94a3b8; margin-top: 12px; text-align: right;
    font-style: italic;
  }}
  .bg-deco {{
    position: absolute; bottom: 0; right: 0; width: 180px; height: 180px;
    border-radius: 50% 0 0 0; background: #059669; opacity: 0.04;
  }}
</style></head>
<body>
<div class="slide">
  <div class="left-bar"></div>
  <div class="main">
    <div class="top-line"></div>
    <div class="title">{title}</div>
    <div class="code-block">
      <div class="code-header">
        <div class="dot dot-r"></div><div class="dot dot-y"></div><div class="dot dot-g"></div>
        <span class="code-lang">{language}</span>
      </div>
      <div class="code-content">{code_html}</div>
    </div>
    {"<div class='caption'>" + caption + "</div>" if caption else ""}
  </div>
  <div class="bg-deco"></div>
</div>
</body></html>"""


# ── 4. 对比页 ──
def _render_comparison(content: Dict[str, Any]) -> str:
    title = _safe_html(content.get("title", ""))
    left_title = _safe_html(content.get("left_title", ""))
    right_title = _safe_html(content.get("right_title", ""))
    left_items = content.get("left_items", [])
    right_items = content.get("right_items", [])

    def _col_items(items, color):
        return "\n".join(
            f'<div class="col-item"><span class="col-dot" style="background:{color}"></span>'
            f'<span>{_safe_html(item)}</span></div>'
            for item in items
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">{_BASE_STYLE}
<style>
  .slide {{
    width: 1280px; height: 720px; background: #f8fafc;
    display: flex; flex-direction: column; position: relative; overflow: hidden;
  }}
  .header {{ padding: 40px 60px 0; }}
  .top-line {{ width: 60px; height: 4px; border-radius: 2px; background: #4F46E5; margin-bottom: 14px; }}
  .title {{ font-size: 32px; font-weight: 700; color: #1e293b; margin-bottom: 28px; }}
  .cols {{ display: flex; gap: 32px; padding: 0 60px; flex: 1; }}
  .col {{
    flex: 1; border-radius: 16px; padding: 28px 26px;
    display: flex; flex-direction: column;
  }}
  .col-left {{ background: #eff6ff; border: 1px solid #bfdbfe; }}
  .col-right {{ background: #f0fdf4; border: 1px solid #bbf7d0; }}
  .col-title {{
    font-size: 20px; font-weight: 700; margin-bottom: 20px;
    padding-bottom: 12px; border-bottom: 2px solid rgba(0,0,0,0.08);
  }}
  .col-left .col-title {{ color: #2563eb; }}
  .col-right .col-title {{ color: #16a34a; }}
  .col-items {{ display: flex; flex-direction: column; gap: 14px; flex: 1; }}
  .col-item {{
    display: flex; align-items: flex-start; gap: 10px;
    font-size: 17px; color: #475569; line-height: 1.7;
  }}
  .col-dot {{ width: 7px; height: 7px; border-radius: 50%; margin-top: 8px; flex-shrink: 0; }}
  .vs-badge {{
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    width: 52px; height: 52px; border-radius: 50%;
    background: #fff; border: 2px solid #e2e8f0;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; font-weight: 700; color: #64748b; z-index: 10;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  }}
  .bottom-pad {{ height: 24px; }}
</style></head>
<body>
<div class="slide">
  <div class="header">
    <div class="top-line"></div>
    <div class="title">{title}</div>
  </div>
  <div class="cols">
    <div class="col col-left">
      <div class="col-title">{left_title}</div>
      <div class="col-items">{_col_items(left_items, "#2563eb")}</div>
    </div>
    <div class="col col-right">
      <div class="col-title">{right_title}</div>
      <div class="col-items">{_col_items(right_items, "#16a34a")}</div>
    </div>
  </div>
  <div class="vs-badge">VS</div>
  <div class="bottom-pad"></div>
</div>
</body></html>"""


# ── 5. 章节过渡页 ──
def _render_section_divider(content: Dict[str, Any]) -> str:
    title = _safe_html(content.get("title", ""))
    number = content.get("number", "")
    subtitle = _safe_html(content.get("subtitle", ""))
    accent = content.get("accent_color", "#6366f1")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">{_BASE_STYLE}
<style>
  .slide {{
    width: 1280px; height: 720px;
    background: linear-gradient(160deg, {accent} 0%, #1e1b4b 100%);
    display: flex; align-items: center; justify-content: center;
    position: relative; overflow: hidden;
  }}
  .bg-line {{
    position: absolute; width: 1px; height: 100%; background: rgba(255,255,255,0.06);
  }}
  .bg-line:nth-child(1) {{ left: 25%; }}
  .bg-line:nth-child(2) {{ left: 50%; }}
  .bg-line:nth-child(3) {{ left: 75%; }}
  .content {{ text-align: center; position: relative; z-index: 2; }}
  .number {{
    font-size: 90px; font-weight: 900; color: rgba(255,255,255,0.1);
    line-height: 1; margin-bottom: -10px;
  }}
  .title {{
    font-size: 42px; font-weight: 700; color: #fff; line-height: 1.3;
  }}
  .subtitle {{
    font-size: 20px; color: rgba(255,255,255,0.6); margin-top: 18px;
  }}
  .line {{ width: 60px; height: 3px; background: rgba(255,255,255,0.4); margin: 24px auto 0; border-radius: 2px; }}
</style></head>
<body>
<div class="slide">
  <div class="bg-line"></div><div class="bg-line"></div><div class="bg-line"></div>
  <div class="content">
    {"<div class='number'>" + str(number) + "</div>" if number else ""}
    <div class="title">{title}</div>
    {"<div class='subtitle'>" + subtitle + "</div>" if subtitle else ""}
    <div class="line"></div>
  </div>
</div>
</body></html>"""


# ── 6. 总结页 ──
def _render_summary(content: Dict[str, Any]) -> str:
    title = _safe_html(content.get("title", "本节小结"))
    points = content.get("points", content.get("bullets", []))
    accent = content.get("accent_color", "#4F46E5")

    points_html = "\n".join(
        f'<div class="sum-item">'
        f'<span class="sum-icon" style="background:{accent}">✓</span>'
        f'<span class="sum-text">{_safe_html(p)}</span>'
        f'</div>'
        for p in points
    ) if points else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">{_BASE_STYLE}
<style>
  .slide {{
    width: 1280px; height: 720px; background: #f8fafc;
    display: flex; flex-direction: column; position: relative; overflow: hidden;
  }}
  .header {{
    padding: 50px 60px 0;
  }}
  .top-line {{ width: 60px; height: 4px; border-radius: 2px; background: {accent}; margin-bottom: 14px; }}
  .title {{ font-size: 34px; font-weight: 700; color: #1e293b; margin-bottom: 40px; }}
  .sum-list {{
    display: flex; flex-direction: column; gap: 22px; padding: 0 60px; flex: 1;
  }}
  .sum-item {{ display: flex; align-items: center; gap: 18px; }}
  .sum-icon {{
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 16px; font-weight: 700; flex-shrink: 0;
  }}
  .sum-text {{ font-size: 22px; color: #334155; line-height: 1.6; }}
  .bg-deco {{
    position: absolute; top: -60px; right: -60px; width: 220px; height: 220px;
    border-radius: 50%; background: {accent}; opacity: 0.04;
  }}
</style></head>
<body>
<div class="slide">
  <div class="header">
    <div class="top-line"></div>
    <div class="title">{title}</div>
  </div>
  <div class="sum-list">{points_html}</div>
  <div class="bg-deco"></div>
</div>
</body></html>"""


def render_ppt_page(template: str, content: Dict[str, Any]) -> str:
    """渲染 PPT 页面 HTML"""
    # 兼容旧模板名
    alias_map = {
        "title_bullets": CONTENT,
        "title_code": CODE_EXAMPLE,
    }
    template = alias_map.get(template, template)

    if template not in _TEMPLATE_MAP:
        raise ValueError(f"未知模板: {template}，可用: {list(_TEMPLATE_MAP.keys())}")

    render_fn = globals()[_TEMPLATE_MAP[template]]
    return render_fn(content)
