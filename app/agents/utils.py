"""Agent 共享工具函数"""
import json
import re
import logging

log = logging.getLogger(__name__)


def _find_json_by_braces(text: str, start_pos: int = 0) -> tuple[str | None, int]:
    """
    从 text[start_pos:] 中找到第一个完整的 {...} 或 [...] 并返回 (json_str, end_pos)
    使用花括号计数 + 字符串转义感知。
    """
    for open_ch, close_ch in [('{', '}'), ('[', ']')]:
        idx = text.find(open_ch, start_pos)
        if idx == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for i in range(idx, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == '\\' and in_string:
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return text[idx:i + 1], i + 1
    return None, start_pos


def _strip_markdown_fences(text: str) -> str:
    """
    去掉 LLM 响应中的 markdown 代码块包裹。
    核心难点：JSON 的 code 字段内可能包含 ``` 导致正则提前截断。
    策略：找第一个 ``` 开头行，然后逐行扫描找关闭的 ```（用 json.loads 验证）。
    """
    clean = text.strip()

    # 找第一个 ``` 开头行（如 ```json、```、```python）
    first_fence = re.search(r'```[\w]*\s*\n', clean)
    if not first_fence:
        # 没有代码块，直接返回
        return clean

    # 取第一个 fence 之后的全部内容
    after_first = clean[first_fence.end():]
    lines = after_first.split('\n')

    # 逐行扫描，找能关闭 JSON 的 ```
    # 当遇到一行只有 ``` 时，尝试把之前的内容当 JSON 解析
    # 如果成功，说明这是真正的关闭 fence；如果失败，继续扫描
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == '```' or stripped.startswith('```'):
            candidate = '\n'.join(lines[:i]).strip()
            if not candidate:
                continue
            try:
                json.loads(candidate)
                # 解析成功，这就是关闭 fence
                return candidate
            except (json.JSONDecodeError, ValueError):
                # 解析失败，这个 ``` 在 JSON 内部，继续扫描
                continue

    # 找不到有效关闭 fence，尝试整个内容（可能没有尾部 ```）
    full_content = '\n'.join(lines).strip()
    if full_content.endswith('```'):
        full_content = full_content[:-3].strip()
    return full_content


def _extract_json_from_markdown(text: str) -> str | None:
    """
    从 markdown 代码块中提取 JSON 内容。
    支持 ```json ... ``` 格式，且 JSON 内部可包含 ``` 字符。
    使用括号计数找到完整的 JSON 对象。
    """
    lines = text.split('\n')
    in_fence = False
    json_lines = []

    for line in lines:
        stripped = line.strip()

        # 进入代码块
        if not in_fence and (stripped.startswith('```json') or stripped == '```'):
            in_fence = True
            continue

        # 遇到关闭 fence
        if in_fence and stripped.startswith('```'):
            # 先检查当前收集的内容是否是完整 JSON
            candidate = '\n'.join(json_lines).strip()
            if candidate:
                try:
                    json.loads(candidate)
                    return candidate
                except (json.JSONDecodeError, ValueError):
                    # 不是完整 JSON，这个 ``` 可能在 JSON 内部
                    json_lines.append(line)
                    continue

        # 在 fence 内，持续收集
        if in_fence:
            json_lines.append(line)

    # 没找到关闭 fence 或 JSON 不完整，尝试整个收集的内容
    if json_lines:
        candidate = '\n'.join(json_lines).strip()
        # 去掉末尾可能残留的 ```
        if candidate.endswith('```'):
            candidate = candidate[:-3].strip()
        if candidate:
            try:
                json.loads(candidate)
                return candidate
            except (json.JSONDecodeError, ValueError):
                pass

    return None



def extract_json(text: str) -> dict | list | None:
    """
    从 LLM 响应中提取 JSON。
    策略（按优先级）：
    1. 直接解析原始文本
    2. 从 markdown 代码块中提取
    3. 去掉 markdown 代码块后解析
    4. 清理不可见字符后解析
    5. 花括号/方括号扫描候选，按大小降序，返回第一个能解析的
    """
    if not text:
        return None

    # 0. 预处理：统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 1. 直接尝试解析（LLM 可能直接输出纯 JSON）
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. 从 markdown 代码块中提取 JSON
    json_from_markdown = _extract_json_from_markdown(text)
    if json_from_markdown:
        try:
            return json.loads(json_from_markdown)
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. 去掉 markdown 代码块后解析
    clean = _strip_markdown_fences(text)
    try:
        return json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        pass

    # 4. 清理不可见字符后解析（BOM、零宽字符等）
    import unicodedata
    sanitized = ''.join(
        ch for ch in clean
        if unicodedata.category(ch) not in ('Cf', 'Cc', 'Cs')  # 跳过格式/控制/代理字符
    ).strip()
    try:
        return json.loads(sanitized)
    except (json.JSONDecodeError, ValueError):
        pass

    # 5. 花括号/方括号扫描候选
    candidates = []
    for scan_text in [sanitized, clean, text]:
        pos = 0
        while pos < len(scan_text):
            json_str, next_pos = _find_json_by_braces(scan_text, pos)
            if json_str is None:
                break
            if len(json_str) > 10:
                candidates.append(json_str)
            pos = next_pos

    # 去重，按长度降序
    candidates = list(dict.fromkeys(candidates))
    candidates.sort(key=len, reverse=True)

    # 5a. 先尝试能解析且是 dict/list 的候选
    for json_str in candidates:
        try:
            result = json.loads(json_str)
            if isinstance(result, (dict, list)):
                return result
        except (json.JSONDecodeError, ValueError):
            continue

    # 5b. 最后一轮：不检查类型
    for json_str in candidates:
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            continue

    log.warning(f"无法从 LLM 响应中提取 JSON: {text[:300]}...")
    return None
