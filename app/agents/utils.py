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


def normalize_field(value, expected_type, field_name: str = ""):
    """
    规范化 LLM 返回的字段值，处理 JSON 字符串被塞入字段的问题。

    Args:
        value: 原始字段值
        expected_type: 期望类型 (dict, list, str)
        field_name: 字段名（仅用于日志）

    Returns:
        规范化后的值
    """
    if value is None:
        return None

    # 如果已经是期望类型，直接返回
    if expected_type == dict and isinstance(value, dict):
        return value
    if expected_type == list and isinstance(value, list):
        return value
    if expected_type == str and isinstance(value, str):
        return value

    # 如果是字符串但期望 dict/list，尝试 JSON 解析
    if isinstance(value, str) and expected_type in (dict, list):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, expected_type):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

    # 如果期望 list 但收到 dict，尝试提取
    if expected_type == list and isinstance(value, dict):
        # 常见模式: {"items": [...]} 或 {"terms": [...]}
        for key in ("items", "terms", "list", "data", "questions"):
            if key in value and isinstance(value[key], list):
                return value[key]
        return []

    # 如果期望 str 但收到 dict/list，序列化
    if expected_type == str and isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)

    # 类型不匹配但无法修复，返回空值
    if expected_type == dict:
        return {}
    if expected_type == list:
        return []

    return value


def normalize_resource_content(content: dict, resource_type: str) -> dict:
    """
    根据资源类型规范化 content 中的字段类型。
    处理 LLM 将 JSON 字符串塞入 dict/list 字段的问题。

    Args:
        content: 资源内容字典
        resource_type: 资源类型 (code/question/mindmap/glossary/knowledge_link/ppt_video)

    Returns:
        规范化后的 content 字典
    """
    if not isinstance(content, dict):
        return content

    if resource_type == "code":
        # code 字段可能被塞入 JSON 字符串
        code_val = content.get("code", "")
        if isinstance(code_val, str) and code_val.strip().startswith("{") and '"code"' in code_val:
            try:
                parsed = json.loads(code_val.strip())
                if isinstance(parsed, dict) and "code" in parsed:
                    inner_code = parsed.get("code", "")
                    python_kw = ["def ", "import ", "from ", "class ", "if ", "for ", "while ", "print(", "return "]
                    if isinstance(inner_code, str) and any(kw in inner_code for kw in python_kw):
                        for key in ("title", "description", "input_example", "expected_output",
                                    "test_cases", "difficulty", "tags"):
                            if key in parsed and parsed[key]:
                                content[key] = parsed[key]
                        content["code"] = inner_code
            except (json.JSONDecodeError, ValueError):
                pass
        content["test_cases"] = normalize_field(content.get("test_cases"), list, "test_cases")
        content["tags"] = normalize_field(content.get("tags"), list, "tags")

    elif resource_type == "question":
        questions = content.get("questions", [])
        if isinstance(questions, str):
            questions = normalize_field(questions, list, "questions")
        if not isinstance(questions, list):
            questions = []
        for q in questions:
            if not isinstance(q, dict):
                continue
            q["options"] = normalize_field(q.get("options"), list, "options")
            q["test_cases"] = normalize_field(q.get("test_cases"), list, "test_cases")
            if "rubric" in q:
                q["rubric"] = normalize_field(q.get("rubric"), dict, "rubric")
        content["questions"] = questions

    elif resource_type == "mindmap":
        md = content.get("mindmap_markdown", "")
        if isinstance(md, str) and md.strip().startswith("{") and '"mindmap_markdown"' in md:
            try:
                parsed = json.loads(md.strip())
                if isinstance(parsed, dict) and "mindmap_markdown" in parsed:
                    inner_md = parsed.get("mindmap_markdown", "")
                    if isinstance(inner_md, str) and inner_md:
                        content["mindmap_markdown"] = inner_md
                        if "mindmap_html" in parsed:
                            content["mindmap_html"] = parsed["mindmap_html"]
            except (json.JSONDecodeError, ValueError):
                pass

    elif resource_type == "glossary":
        terms = content.get("terms", [])
        terms = normalize_field(terms, list, "terms")
        for term in terms:
            if not isinstance(term, dict):
                continue
            term["related_terms"] = normalize_field(term.get("related_terms"), list, "related_terms")
        content["terms"] = terms

    elif resource_type == "knowledge_link":
        nodes = content.get("nodes", [])
        nodes = normalize_field(nodes, list, "nodes")
        for node in nodes:
            if not isinstance(node, dict):
                continue
            level = node.get("level")
            if isinstance(level, str) and level.isdigit():
                node["level"] = int(level)
            elif not isinstance(level, int):
                node["level"] = 3
        content["nodes"] = nodes
        content["edges"] = normalize_field(content.get("edges"), list, "edges")

    elif resource_type == "ppt_video":
        pages = content.get("pages", [])
        pages = normalize_field(pages, list, "pages")
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_content = page.get("content")
            if isinstance(page_content, dict):
                if page.get("template") == "code_example":
                    code_val = page_content.get("code", "")
                    if isinstance(code_val, str) and code_val.strip().startswith("{") and '"code"' in code_val:
                        try:
                            parsed = json.loads(code_val.strip())
                            if isinstance(parsed, dict) and "code" in parsed:
                                inner_code = parsed.get("code", "")
                                python_kw = ["def ", "import ", "from ", "class ", "if ", "for ", "while ", "print(", "return "]
                                if isinstance(inner_code, str) and any(kw in inner_code for kw in python_kw):
                                    page_content["code"] = inner_code
                        except (json.JSONDecodeError, ValueError):
                            pass
                page_content["bullets"] = normalize_field(page_content.get("bullets"), list, "bullets")
        content["pages"] = pages

    return content
