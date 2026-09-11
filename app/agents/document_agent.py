from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.core.logger import log


class DocumentAgent(BaseAgent):
    agent_name = "document"
    """文档生成 Agent - 支持个性化 + AI配图"""

    PROMPT_PATH = "prompts/document_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)

    async def run(self, topic: str, user_id: int = None, force: bool = False,
                  extra_instructions: str = "") -> Dict[str, Any]:
        """
        执行文档生成任务

        Args:
            topic: 知识点主题
            user_id: 用户 ID（用于缓存和个性化）
            force: True 时跳过 DB 缓存强制重新生成（Supervisor 重做/学生手动重生成）
            extra_instructions: 追加到 prompt 的接地材料/修正指令

        Returns:
            包含 Markdown 文档和配图的字典
        """
        log.info(f"DocumentAgent 开始为主题 '{topic}' 生成文档")

        # 先查库（force 时跳过，保证 Supervisor 重做能真正重新生成）
        if user_id and self.db and not force:
            existing = await self._get_from_db(user_id, topic)
            if existing:
                log.info(f"命中数据库缓存，主题: {topic}")
                return existing

        # 获取学生画像用于个性化
        profile = None
        if user_id and self.db:
            profile = await self._get_profile(user_id)

        prompt = self._load_and_format_prompt(topic, profile)
        if extra_instructions:
            prompt += extra_instructions
        markdown_content = await self._call_llm(prompt)

        # 校验内容
        if not markdown_content or len(markdown_content.strip()) < 50:
            log.warning(f"DocumentAgent LLM 返回内容过短，使用 mock 兜底")
            markdown_content = self._get_mock_document(topic, profile)

        # 生成 AI 配图
        images = await self._generate_illustrations(topic, profile)

        result = {
            "topic": topic,
            "content": markdown_content,
            "images": images
        }

        log.info(f"DocumentAgent 完成，文档已生成，长度：{len(markdown_content)} 字符，配图：{len(images)} 张")
        return result

    async def _generate_illustrations(self, topic: str, profile: Dict = None) -> list:
        """为文档生成配图（通过 model_manager 路由图片模型）"""
        from app.multimodal.generators import ImageGenerator
        from app.core.model_manager import IMAGE_MODELS

        images = []
        prompts = [
            f"Educational illustration showing the core concepts of {topic}, clean minimal flat design, suitable for teaching",
            f"Educational illustration showing practical applications of {topic}, with code and flowchart elements, flat design",
        ]

        # 使用 model_manager 中配置的默认图片模型
        default_model_key = "z_image_turbo"

        try:
            generator = ImageGenerator(provider=default_model_key)
            for i, prompt_text in enumerate(prompts):
                try:
                    result = await generator.generate_image(
                        prompt=prompt_text,
                        model_key=default_model_key,
                    )
                    if result.get("success") and result.get("image_base64"):
                        images.append({
                            "index": i + 1,
                            "description": f"{topic} {'核心概念' if i == 0 else '应用场景'}",
                            "base64": result["image_base64"],
                        })
                except Exception as e:
                    log.warning(f"配图 {i+1} 生成失败: {e}")
        except Exception as e:
            log.warning(f"图片生成器初始化失败: {e}")

        return images

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
                    "interests": profile.interests or []
                }
        except Exception as e:
            log.warning(f"获取学生画像失败: {e}")
        return None

    async def _get_from_db(self, user_id: int, topic: str) -> Optional[Dict[str, Any]]:
        """从数据库获取已生成的文档"""
        from app.models import LearningResource
        result = await self.db.execute(
            select(LearningResource).where(
                LearningResource.user_id == user_id,
                LearningResource.resource_type == "document",
                LearningResource.topic == topic
            ).order_by(LearningResource.created_at.desc()).limit(1)
        )
        record = result.scalar_one_or_none()
        if record:
            return record.content
        return None

    def _load_and_format_prompt(self, topic: str, profile: Dict = None) -> str:
        """加载并格式化 Prompt（注入学生画像）"""
        template = self._load_prompt(self.PROMPT_PATH)

        # 构建个性化上下文
        if profile:
            weakness_str = ", ".join(profile.get("weakness", [])) or "无"
            interests_str = ", ".join(profile.get("interests", [])) or "无"
            profile_context = f"""
## 学生画像信息（用于个性化文档生成）
- 专业：{profile.get('major', '未知')}
- 年级：{profile.get('grade', '未知')}
- 知识水平：{profile.get('knowledge_level', '未知')}
- 学习风格：{profile.get('learning_style', '未知')}
- 学习目标：{profile.get('goal', '未知')}
- 薄弱点：{weakness_str}
- 兴趣方向：{interests_str}

**请根据学生画像调整文档**：
- 根据学生知识水平调整内容深度
- 根据学习风格调整表达方式
- 重点讲解学生的薄弱点相关内容
- 使用学生专业相关的案例
"""
        else:
            profile_context = ""

        return self._format_prompt(template, topic=topic, profile_context=profile_context)

    def _get_mock_document(self, topic: str, profile: Dict = None) -> str:
        """生成 mock 文档内容"""
        level = "基础入门"
        if profile:
            kl = profile.get("knowledge_level", "")
            if "进阶" in kl or "高级" in kl:
                level = "进阶"
            elif "有基础" in kl or "中级" in kl:
                level = "中级"

        return f"""# {topic}

## 📖 简介

本文档将系统地介绍 **{topic}** 的核心概念和实践应用。

## 🎯 核心概念

### 1. 基本定义

{topic} 是一个重要的知识点，广泛应用于实际开发中。

### 2. 关键特性

- 特性一：高效性
- 特性二：可扩展性
- 特性三：易用性

## 💡 代码示例

```python
# {topic} 示例代码
def example():
    # 示例函数
    print("Hello from {topic}")
    return True

# 运行示例
result = example()
print("结果:", result)
```

## 📝 最佳实践

1. **实践一**：遵循单一职责原则
2. **实践二**：编写清晰的文档
3. **实践三**：编写单元测试

## 🎓 总结

通过本节学习，你应该掌握了 {topic} 的核心概念和基本用法。

---

*当前难度级别：{level}*
"""



# 创建全局实例
document_agent = DocumentAgent()
