from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.agents.utils import extract_json
from app.core.logger import log
from app.sandbox.local_runner import LocalRunner


# 创建全局实例
code_agent = None  # 延迟初始化

class CodeAgent(BaseAgent):
    agent_name = "code"
    """代码生成与执行 Agent"""

    PROMPT_PATH = "prompts/code_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)
        self.local_runner = LocalRunner()

    async def run(self, task_description: str, user_id: int = None) -> Dict[str, Any]:
        """
        执行代码生成任务（先查库，有则返回，无则生成后保存）

        Args:
            task_description: 任务描述
            user_id: 用户 ID（用于缓存到数据库）

        Returns:
            包含代码和说明的字典
        """
        log.info(f"CodeAgent 开始为任务 '{task_description}' 生成代码")

        # 先查库
        if user_id and self.db:
            existing = await self._get_from_db(user_id, task_description)
            if existing:
                log.info(f"命中数据库缓存，任务: {task_description[:50]}")
                return existing

        prompt = self._load_and_format_prompt(task_description)
        response = await self._call_llm(prompt)
        log.info(f"CodeAgent LLM 响应长度: {len(response)}，前200字: {response[:200]}")

        default_result = {
            "title": task_description[:50],
            "description": task_description,
            "code": "# 代码生成失败，请重试",
            "test_cases": [],
            "difficulty": "中等",
            "tags": []
        }

        result = extract_json(response)

        # 如果 JSON 提取失败，尝试从 markdown 代码块中直接提取代码
        if not result or not isinstance(result, dict) or "code" not in result:
            # 尝试从 ```json ... ``` 中手动提取
            import re
            json_match = re.search(r'```json\s*\n(\{[\s\S]*?\})\s*\n```', response)
            if json_match:
                try:
                    import json
                    result = json.loads(json_match.group(1))
                    log.info(f"从 markdown 代码块手动提取 JSON 成功")
                except Exception:
                    result = None

        if not result or not isinstance(result, dict) or "code" not in result:
            # 尝试提取纯代码
            code_content = self._extract_code_from_response(response)
            if code_content:
                log.info(f"LLM 返回了 Python 代码而非 JSON，已提取代码（{len(code_content)} 字符）")
                result = {
                    "title": task_description[:50],
                    "description": task_description,
                    "code": code_content,
                    "test_cases": [],
                    "difficulty": "中等",
                    "tags": []
                }
            else:
                log.warning(f"LLM 响应无法提取代码: {str(response)[:300]}")
                result = default_result
        else:
            # 补全缺失字段
            result.setdefault("title", task_description[:50])
            result.setdefault("description", task_description)
            result.setdefault("test_cases", [])
            result.setdefault("difficulty", "中等")
            result.setdefault("tags", [])

        log.info(f"CodeAgent 完成，代码已生成，长度: {len(result.get('code', ''))} 字符")
        return result

    async def _get_from_db(self, user_id: int, topic: str) -> Optional[Dict[str, Any]]:
        """从数据库获取已生成的代码"""
        from app.models import LearningResource
        result = await self.db.execute(
            select(LearningResource).where(
                LearningResource.user_id == user_id,
                LearningResource.resource_type == "code",
                LearningResource.topic == topic
            ).order_by(LearningResource.created_at.desc()).limit(1)
        )
        record = result.scalar_one_or_none()
        if record:
            content = record.content
            # 跳过无效缓存（之前 API 失败时保存的降级数据）
            if isinstance(content, dict) and content.get("code", "").startswith("# 代码生成失败"):
                log.info(f"跳过无效代码缓存，将重新生成")
                return None

            return content
        return None

    def _load_and_format_prompt(self, task_description: str) -> str:
        """加载并格式化 Prompt"""
        template = self._load_prompt(self.PROMPT_PATH)
        return self._format_prompt(template, task_description=task_description)


    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """
        从 LLM 响应中提取 Python 代码。
        处理情况：
        - ```python ... ``` 代码块
        - ``` ... ``` 无语言标签的代码块
        - 纯 Python 代码（无代码块包裹）
        - LLM 在代码后附带 json_data 等无效内容
        """
        import re
        text = response.strip()

        # 尝试从 markdown 代码块中提取（匹配到最后一个 ```）
        code_block = re.search(r'```(?:python)?\s*\n(.*)```', text, re.DOTALL)
        if code_block:
            code = code_block.group(1).strip()
        else:
            code = text

        # 截断：去掉 LLM 在代码后附加的 json_data / metadata 字典
        # 常见模式：json_data = {  或  # 输出JSON
        cutoff_patterns = [
            r'\njson_data\s*=\s*\{',
            r'\n#\s*输出JSON',
            r'\n#\s*Output JSON',
            r'\nresult\s*=\s*\{\s*\n\s*["\']title["\']',
        ]
        for pattern in cutoff_patterns:
            match = re.search(pattern, code)
            if match:
                code = code[:match.start()].strip()
                log.info(f"截断无效尾部，保留 {len(code)} 字符代码")

        # 检查是否像 Python 代码
        python_keywords = ['def ', 'import ', 'from ', 'class ', 'if ', 'for ', 'while ', 'print(', 'return ']
        if any(kw in code for kw in python_keywords):
            return code

        return None

    async def execute_code(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """
        在沙箱中执行代码

        Args:
            code: 要执行的 Python 代码
            timeout: 超时时间（秒）

        Returns:
            执行结果
        """
        log.info(f"CodeAgent 开始执行代码，代码长度: {len(code)}")

        try:
            self.local_runner.timeout = timeout
            result = self.local_runner.run_python_code(code)
            return result
        except Exception as e:
            log.error(f"代码执行异常: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "error": str(e)
            }


# 创建全局实例
code_agent = CodeAgent()
