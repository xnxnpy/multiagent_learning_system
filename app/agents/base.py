from abc import ABC, abstractmethod
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession


class BaseAgent(ABC):
    """Agent 抽象基类"""

    # 子类可以覆盖这个属性来指定 agent 名称
    agent_name: str = "default"

    def __init__(self, db: AsyncSession = None):
        self.db = db

    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """执行 Agent 任务"""
        pass

    def _load_prompt(self, prompt_path: str) -> str:
        """加载 Prompt 模板"""
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Failed to load prompt from {prompt_path}: {e}")

    def _format_prompt(self, template: str, **kwargs) -> str:
        """格式化 Prompt 模板"""
        return template.format(**kwargs)

    async def _call_llm(self, prompt: str, **kwargs) -> str:
        """调用大模型（通过 model_manager 路由到正确的模型）"""
        from app.core.model_manager import model_manager
        messages = [{"role": "user", "content": prompt}]
        return await model_manager.chat(
            messages,
            agent_name=self.agent_name,
            **kwargs
        )

    async def _call_llm_messages(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """调用大模型（直接传入消息列表）"""
        from app.core.model_manager import model_manager
        return await model_manager.chat(
            messages,
            agent_name=self.agent_name,
            **kwargs
        )

