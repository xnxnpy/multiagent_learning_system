from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.core.logger import log


class SummaryAgent(BaseAgent):
    agent_name = "summary"
    """学习总结报告 Agent - 生成阶段性学习总结"""

    PROMPT_PATH = "prompts/summary_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)

    async def run(self, topic: str, user_id: int = None) -> Dict[str, Any]:
        log.info(f"SummaryAgent 开始为主题 '{topic}' 生成学习总结报告")

        if user_id and self.db:
            existing = await self._get_from_db(user_id, topic)
            if existing:
                log.info(f"命中数据库缓存，主题: {topic}")
                return existing

        profile = None
        if user_id and self.db:
            profile = await self._get_profile(user_id)

        prompt = self._load_and_format_prompt(topic, profile)
        content = await self._call_llm(prompt)

        if not content or len(content.strip()) < 100:
            log.warning("SummaryAgent LLM 返回内容过短，使用 mock 兜底")
            content = self._get_mock_summary(topic, profile)

        result = {"topic": topic, "content": content, "type": "summary"}
        log.info(f"SummaryAgent 完成，内容长度: {len(content)} 字符")
        return result

    async def _get_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
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
                    "weakness": profile.weakness or [],
                }
        except Exception as e:
            log.warning(f"获取学生画像失败: {e}")
        return None

    async def _get_from_db(self, user_id: int, topic: str) -> Optional[Dict[str, Any]]:
        from app.models import LearningResource
        result = await self.db.execute(
            select(LearningResource).where(
                LearningResource.user_id == user_id,
                LearningResource.resource_type == "summary",
                LearningResource.topic == topic
            ).order_by(LearningResource.created_at.desc()).limit(1)
        )
        record = result.scalar_one_or_none()
        if record:
            return record.content
        return None

    def _load_and_format_prompt(self, topic: str, profile: Dict = None) -> str:
        template = self._load_prompt(self.PROMPT_PATH)
        if profile:
            weakness_str = ", ".join(profile.get("weakness", [])) or "无"
            profile_context = f"""
## 学生画像信息（用于个性化生成）
- 知识水平：{profile.get('knowledge_level', '未知')}
- 薄弱点：{weakness_str}

**请在"重点难点解析"部分重点展开学生的薄弱点**
"""
        else:
            profile_context = ""
        return self._format_prompt(template, topic=topic, profile_context=profile_context)

    def _get_mock_summary(self, topic: str, profile: Dict = None) -> str:
        weakness = ""
        if profile and profile.get("weakness"):
            weakness = f"\n\n## 重点攻克：{', '.join(profile['weakness'])}\n针对你的薄弱环节，建议多花时间练习这些内容。"
        return f"""# {topic} 学习总结

## 一、核心要点速览
1. {topic} 的核心概念和基本定义
2. {topic} 的工作原理和执行流程
3. {topic} 的常见应用场景

## 二、知识结构梳理
- 基础层：基本概念、术语定义
- 原理层：工作原理、运行机制
- 应用层：实际场景、项目实践

## 三、重点难点解析
### 难点1：核心原理理解
攻克方法：通过具体案例反复练习
### 难点2：实际应用
攻克方法：结合项目实践加深理解
{weakness}

## 四、实践应用指南
1. 从简单示例入手，逐步增加复杂度
2. 结合实际项目场景练习
3. 参考优秀代码示例

## 五、常见误区提醒
1. 概念混淆：注意区分相似术语的差异
2. 忽略基础：扎实基础是进阶的前提
3. 缺乏实践：理论必须与实践结合

## 六、自测清单
1. （选择题-基础）{topic} 的基本定义是什么？
2. （判断题）{topic} 只能用于特定场景？
3. （简答题）请用自己的话描述 {topic} 的核心原理。
4. （选择题-进阶）以下哪个是 {topic} 的最佳实践？
5. （简答题-进阶）请举例说明 {topic} 在实际项目中的应用。

## 七、下一步学习建议
1. 深入学习 {topic} 的高级特性
2. 尝试完成一个综合项目
3. 阅读相关领域的经典文献
"""
