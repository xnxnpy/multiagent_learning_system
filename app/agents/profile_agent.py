import json
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.agents.utils import extract_json
from app.core.model_manager import ModelManagerChatModel
from app.core.logger import log
from app.models import StudentProfile

# 保持后台任务引用，防止被垃圾回收
_background_tasks: set = set()

# 每个用户的 WS 写锁（防止后台任务与流式输出并发写入）
_ws_write_locks: Dict[int, asyncio.Lock] = {}


def _get_ws_write_lock(user_id: int) -> asyncio.Lock:
    if user_id not in _ws_write_locks:
        _ws_write_locks[user_id] = asyncio.Lock()
    return _ws_write_locks[user_id]


class ProfileAgent(BaseAgent):
    agent_name = "profile"
    """画像构建 Agent"""

    PROMPT_PATH = "prompts/profile_chat_prompt.txt"
    EXTRACT_PROMPT_PATH = "prompts/profile_extract_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)
        self._chat_model = ModelManagerChatModel(agent_name="profile")

    async def run(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("ProfileAgent 使用 run_stream 进行流式对话")

    async def run_stream(
        self, user_id: int, user_input: str, chat_history: List[Dict[str, str]] = None,
        ws=None, frontend_profile: Dict[str, Any] = None,
        profile_id: int = None,
    ) -> AsyncGenerator[str, None]:
        log.info(f"ProfileAgent 流式处理用户 {user_id}: {user_input[:50]}...")

        # 如果未传入 profile_id，获取活跃画像的 id
        if not profile_id:
            active_profile = await self._get_existing_profile(user_id)
            if active_profile:
                profile_id = active_profile.get("id")

        # 合并 DB profile 和前端 profile
        db_profile = await self._get_existing_profile(user_id, profile_id)
        if frontend_profile and db_profile:
            existing_profile = {}
            all_keys = set(list(db_profile.keys()) + list(frontend_profile.keys()))
            for k in all_keys:
                db_val = db_profile.get(k, "")
                fe_val = frontend_profile.get(k, "")
                if fe_val:
                    existing_profile[k] = fe_val
                elif db_val:
                    existing_profile[k] = db_val
                else:
                    existing_profile[k] = db_val
        elif frontend_profile and any(frontend_profile.values()):
            existing_profile = {k: v for k, v in frontend_profile.items() if v}
        else:
            existing_profile = db_profile or {}
        existing_profile_json = json.dumps(existing_profile, ensure_ascii=False) if existing_profile else "{}"

        # 同步快速提取（更新 prompt 用的 profile + 异步写DB）
        quick_extracted = self._quick_extract(user_input, existing_profile)
        if quick_extracted:
            existing_profile.update({k: v for k, v in quick_extracted.items() if v})
            existing_profile_json = json.dumps(existing_profile, ensure_ascii=False)
            async def _quick_save():
                from app.models import AsyncSessionLocal
                async with AsyncSessionLocal() as save_db:
                    saver = ProfileAgent(save_db)
                    await saver._save_profile(user_id, existing_profile, profile_id=profile_id)
            asyncio.create_task(_quick_save())

        # 构建对话上下文（始终调用 LLM，让它根据完整 profile 自然回复）
        chat_prompt = self._load_chat_prompt(existing_profile_json)

        messages = [{"role": "system", "content": chat_prompt}]
        if chat_history:
            for msg in chat_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_input})

        # 流式输出
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        lc_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))

        full_response = ""
        async for chunk in self._chat_model.astream(lc_messages):
            text = chunk if isinstance(chunk, str) else getattr(chunk, 'text', str(chunk))
            full_response += text
            yield text

        # 后台：LLM提取画像 + 通知前端
        async def _bg_extract_and_notify(ws):
            await self._extract_and_save_profile(user_id, user_input, full_response, chat_history, profile_id)
            lock = _get_ws_write_lock(user_id)
            async with lock:
                try:
                    await ws.send_json({"type": "profile_update", "message": "画像已更新"})
                    updated_profile = await self._get_existing_profile(user_id, profile_id)
                    if updated_profile and self._is_profile_sufficient(updated_profile):
                        await ws.send_json({"type": "check_workflow", "message": "检查工作流状态"})
                except Exception:
                    pass

        task = asyncio.create_task(_bg_extract_and_notify(ws))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    async def _extract_and_save_profile(
        self, user_id: int, user_input: str, assistant_reply: str,
        chat_history: List[Dict[str, str]] = None, profile_id: int = None
    ):
        """从对话中提取画像并保存（后台任务）"""
        import os
        from app.models import AsyncSessionLocal
        try:
            async with AsyncSessionLocal() as db:
                agent_reader = ProfileAgent(db)
                latest_profile = await agent_reader._get_existing_profile(user_id, profile_id)

            existing_profile_json = json.dumps(latest_profile, ensure_ascii=False) if latest_profile else "{}"
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            extract_path = os.path.join(base_dir, self.EXTRACT_PROMPT_PATH)
            with open(extract_path, 'r', encoding='utf-8') as f:
                template = f.read()

            conversation_parts = []
            if chat_history:
                for msg in chat_history:
                    role = "学生" if msg.get("role") == "user" else "助手"
                    conversation_parts.append(f"{role}：{msg.get('content', '')}")
            conversation_parts.append(f"学生：{user_input}")
            conversation_parts.append(f"助手：{assistant_reply}")
            conversation = "\n".join(conversation_parts)
            extract_prompt = template.format(conversation=conversation, existing_profile=existing_profile_json)
            response = await self._call_llm(extract_prompt)

            profile_data = extract_json(response)
            if not profile_data or not isinstance(profile_data, dict):
                log.warning(f"ProfileAgent 画像提取失败，使用增量更新")
                profile_data = self._infer_profile_from_conversation(user_input, latest_profile)

            merged_profile = self._merge_profiles(latest_profile, profile_data)
            async with AsyncSessionLocal() as db:
                agent_saver = ProfileAgent(db)
                await agent_saver._save_profile(user_id, merged_profile, profile_id=profile_id)
            log.info(f"ProfileAgent 画像提取完成，用户 {user_id}")
        except Exception as e:
            log.error(f"ProfileAgent 画像提取失败: {e}")

    def _infer_profile_from_conversation(self, user_input: str, existing: Optional[Dict]) -> Dict[str, Any]:
        """LLM 提取失败时的兜底"""
        result = existing.copy() if existing else {
            "major": "", "grade": "", "goal": "", "knowledge_level": "",
            "learning_style": "", "interests": [], "weakness": [], "coding_ability": ""
        }
        text = user_input.lower()
        if any(k in text for k in ["计算机", "软件", "信息", "cs", "计算机科学"]):
            result["major"] = "计算机科学"
        elif any(k in text for k in ["ai", "人工智能", "机器学习"]):
            result["major"] = "数据科学"
        for level, keywords in [("大一", ["大一", "大1"]), ("大二", ["大二", "大2"]),
                                 ("大三", ["大三", "大3"]), ("大四", ["大四", "大4"])]:
            if any(k in text for k in keywords):
                result["grade"] = level
        return result

    def _quick_extract(self, user_input: str, existing: Dict) -> Dict[str, Any]:
        """同步快速提取（不含 goal，交给后台 LLM）"""
        extracted = {}
        text = user_input

        # 专业（排除容易误匹配的词）
        major_keywords = {
            "计算机": "计算机科学", "软件": "软件工程", "信息": "信息工程",
            "电子": "电子工程", "自动化": "自动化", "通信": "通信工程",
            "机械": "机械工程",
        }
        for kw, val in major_keywords.items():
            if kw in text:
                extracted["major"] = val
                break

        # 年级
        grade_map = {
            "大一": "大一", "大1": "大一", "大二": "大二", "大2": "大二",
            "大三": "大三", "大3": "大三", "大四": "大四", "大4": "大四",
            "研一": "研一", "研二": "研二", "研三": "研三",
        }
        for kw, val in grade_map.items():
            if kw in text:
                extracted["grade"] = val
                break

        # 学习目标：只提取明确的学科方向，不含"找工作"等模糊目标
        goal_keywords = {
            "机器学习": "系统学习机器学习", "深度学习": "系统学习深度学习",
            "人工智能": "系统学习人工智能", "数据分析": "系统学习数据分析",
            "web开发": "系统学习Web开发", "前端": "系统学习前端开发",
            "Java": "系统学习Java", "算法": "系统学习算法",
            "计算机视觉": "系统学习计算机视觉",
        }
        for kw, val in goal_keywords.items():
            if kw in text:
                extracted["goal"] = val
                break

        # 知识水平：只匹配用户明确回答"知识水平/学习基础"类问题的表述
        # 注意：不包含单独的"基础"二字，避免"有编程基础"被误判为知识水平
        level_keywords = [
            ("零基础", "零基础"),
            ("没怎么接触过", "没怎么接触过"), ("没接触过", "没怎么接触过"),
            ("没学过", "没学过"), ("不熟悉", "不熟悉"),
            ("入门", "入门"),
            ("学过相关课程", "学过相关课程"), ("相关课程", "学过相关课程"),
            ("有编程语言基础", "有编程语言基础"), ("有语言基础", "有编程语言基础"),
            ("有基础", "有一定基础"), ("有一定基础", "有一定基础"),
            ("比较熟悉", "比较熟悉"), ("熟悉", "比较熟悉"),
            ("精通", "精通"),
        ]
        for kw, val in level_keywords:
            if kw in text:
                extracted["knowledge_level"] = val
                break

        # 兴趣方向：只提取用户明确提到的方向，不要过度推断
        # 例如用户说"AI"，只添加"人工智能"，不要同时添加"机器学习"等
        interest_keywords = [
            ("自然语言处理", "NLP"), ("计算机视觉", "计算机视觉"),
            ("深度学习", "深度学习"), ("机器学习", "机器学习"),
            ("人工智能", "人工智能"), ("AI", "人工智能"),
            ("Web开发", "Web开发"), ("web开发", "Web开发"), ("web", "Web开发"),
            ("前端开发", "前端开发"), ("前端", "前端开发"),
            ("后端开发", "后端开发"), ("后端", "后端开发"),
            ("数据分析", "数据分析"), ("大数据", "大数据"),
            ("网络安全", "网络安全"), ("游戏开发", "游戏开发"), ("游戏", "游戏开发"),
            ("NLP", "NLP"), ("nlp", "NLP"), ("CV", "计算机视觉"), ("cv", "计算机视觉"),
        ]
        found_interests = list(existing.get("interests") or [])
        for kw, val in interest_keywords:
            if kw in text and val not in found_interests:
                found_interests.append(val)
                break  # 只匹配最具体的一个，避免过度推断
        if found_interests != (existing.get("interests") or []):
            extracted["interests"] = found_interests

        # 薄弱点：提取用户明确表达的薄弱点
        # 规则：
        # 1. 如果用户明确提到"薄弱/差/弱/不擅长"等负面上下文，提取对应薄弱点
        # 2. 如果用户只回答一个常见薄弱点词（算法/数学/英语），且输入很短（<=6字），视为回答薄弱点问题
        # 3. 避免"有编程基础"、"学过编程"等中性/正面描述被误判为薄弱点
        weakness_keywords = [
            ("数学", "数学基础"), ("数学基础", "数学基础"), ("数学不好", "数学基础"), ("数学差", "数学基础"),
            ("算法", "算法"), ("算法薄弱", "算法"), ("算法不好", "算法"), ("算法差", "算法"), ("算法弱", "算法"),
            ("英语", "英语"), ("英语不好", "英语"), ("英语差", "英语"), ("英语文献", "英语"),
            ("编程基础差", "编程基础"), ("编程不好", "编程基础"), ("编程薄弱", "编程基础"),
            ("逻辑思维差", "逻辑思维"), ("逻辑不好", "逻辑思维"), ("逻辑", "逻辑思维"),
            ("基础薄弱", "基础薄弱"), ("基础差", "基础薄弱"),
        ]
        short_weakness_keywords = ["算法", "数学", "英语", "编程", "逻辑"]
        negative_context = any(k in text for k in ["薄弱", "弱点", "不足", "不擅长", "差", "弱", "困难", "不好"])
        is_short_answer = len(text.strip()) <= 6
        has_weakness_keyword = any(k in text for k in short_weakness_keywords)
        # 排除明显的正面/中性描述
        positive_context = any(k in text for k in ["有", "会", "学过", "基础", "擅长", "好"])
        should_extract_weakness = negative_context or (is_short_answer and has_weakness_keyword and not positive_context)

        found_weakness = list(existing.get("weakness") or [])
        if should_extract_weakness:
            for kw, val in weakness_keywords:
                if kw in text and val not in found_weakness:
                    found_weakness.append(val)
                    break
        if found_weakness != (existing.get("weakness") or []):
            extracted["weakness"] = found_weakness

        # 学习风格
        style_keywords = {
            "看视频": "看视频", "视频": "看视频", "文档": "看文档",
            "看书": "看文档", "实践": "动手实践", "做题": "做题",
            "练习": "动手实践", "动手": "动手实践",
        }
        for kw, val in style_keywords.items():
            if kw in text:
                extracted["learning_style"] = val
                break

        # 编程能力：必须由用户明确回答编程能力问题时才提取
        # 单独的"基础"、"有基础"不会触发，必须是"编程能力/水平"相关表述
        ability_keywords = [
            ("不会编程", "零基础"), ("没学过编程", "零基础"), ("零基础", "零基础"),
            ("编程入门", "入门"), ("入门", "入门"),
            ("会基础语法", "会基础语法"), ("基础语法", "会基础语法"),
            ("能写简单脚本", "入门"), ("写过项目", "中级"),
            ("中级", "中级"), ("熟练", "熟练"), ("精通", "精通"),
        ]
        # 只有当对话中明确出现"编程"相关词，或用户回答的是最后一个编程能力问题时，才提取
        has_programming_context = any(k in text for k in ["编程", "代码", "程序", "开发"])
        if has_programming_context:
            for kw, val in ability_keywords:
                if kw in text:
                    extracted["coding_ability"] = val
                    break

        return extracted

    def _load_chat_prompt(self, existing_profile: str) -> str:
        template = self._load_prompt(self.PROMPT_PATH)
        return template.format(existing_profile=existing_profile)

    async def _get_existing_profile(self, user_id: int, profile_id: int = None) -> Optional[Dict[str, Any]]:
        """获取用户已有画像"""
        if not self.db:
            return None

        if profile_id:
            result = await self.db.execute(
                select(StudentProfile).where(StudentProfile.id == profile_id)
            )
        else:
            result = await self.db.execute(
                select(StudentProfile).where(
                    StudentProfile.user_id == user_id,
                    StudentProfile.is_active == True,
                    StudentProfile.is_archived == False,
                )
            )
        profile = result.scalar_one_or_none()

        if profile:
            return {
                "id": profile.id,
                "major": profile.major or "",
                "grade": profile.grade or "",
                "goal": profile.goal or "",
                "knowledge_level": profile.knowledge_level or "",
                "learning_style": profile.learning_style or "",
                "interests": profile.interests or [],
                "weakness": profile.weakness or [],
                "coding_ability": profile.coding_ability or ""
            }
        return None

    def _is_profile_sufficient(self, profile: Dict[str, Any]) -> bool:
        required = ["major", "grade", "goal", "knowledge_level", "learning_style", "coding_ability"]
        list_fields = ["interests", "weakness"]
        vague_values = {
            "大学生", "研究生", "在职", "一般", "还行", "还可以",
            "没接触过", "没学过", "想学AI", "想学编程", "不知道",
            "待完善", "待评估", "未知", "其他",
        }
        for field in required:
            value = profile.get(field, "")
            if not value:
                return False
            if value.strip() in vague_values:
                return False
            if len(value.strip()) < 2:
                return False
        for field in list_fields:
            items = profile.get(field, [])
            if not items or len(items) == 0:
                return False
        return True

    def _merge_profiles(self, existing: Optional[Dict], new: Dict) -> Dict[str, Any]:
        if not existing:
            return new
        merged = {}
        fields = ["major", "grade", "goal", "knowledge_level", "learning_style", "coding_ability"]
        for field in fields:
            merged[field] = new.get(field) or existing.get(field) or ""
        merged["interests"] = self._merge_lists(existing.get("interests", []), new.get("interests", []))
        merged["weakness"] = self._merge_lists(existing.get("weakness", []), new.get("weakness", []))
        return merged

    def _merge_lists(self, existing: list, new: list) -> list:
        combined = list(set(existing + new))
        return [item for item in combined if item.strip()]

    async def _save_profile(self, user_id: int, profile_data: Dict[str, Any], profile_id: int = None):
        """保存画像到数据库（用 upsert 确保正确写入）"""
        if not self.db:
            return

        from app.models.upsert import upsert as mysql_upsert

        learning_style = profile_data.get("learning_style")
        if isinstance(learning_style, list):
            learning_style = ", ".join(learning_style)
        elif learning_style is None:
            learning_style = ""

        # 先找目标画像
        if profile_id:
            profile = await self.db.get(StudentProfile, profile_id)
            if not profile:
                log.warning(f"profile_id={profile_id} 不存在，跳过保存")
                return
        else:
            result = await self.db.execute(
                select(StudentProfile).where(
                    StudentProfile.user_id == user_id,
                    StudentProfile.is_active == True,
                )
            )
            profile = result.scalar_one_or_none()

        if profile:
            # 更新已有画像
            profile.major = profile_data.get("major", profile.major)
            profile.grade = profile_data.get("grade", profile.grade)
            profile.goal = profile_data.get("goal", profile.goal)
            profile.knowledge_level = profile_data.get("knowledge_level", profile.knowledge_level)
            profile.learning_style = learning_style or profile.learning_style
            profile.interests = profile_data.get("interests", profile.interests)
            profile.weakness = profile_data.get("weakness", profile.weakness)
            profile.coding_ability = profile_data.get("coding_ability", profile.coding_ability)
            await self.db.commit()
            log.info(f"画像已更新，profile_id={profile.id}，用户 {user_id}")
        else:
            # 没有活跃画像时才用 upsert 创建
            await mysql_upsert(
                self.db, StudentProfile.__table__,
                values={
                    "user_id": user_id,
                    "major": profile_data.get("major"),
                    "grade": profile_data.get("grade"),
                    "goal": profile_data.get("goal"),
                    "knowledge_level": profile_data.get("knowledge_level"),
                    "learning_style": learning_style,
                    "interests": profile_data.get("interests"),
                    "weakness": profile_data.get("weakness"),
                    "coding_ability": profile_data.get("coding_ability"),
                },
            )
            await self.db.commit()
            log.info(f"画像已创建，用户 {user_id}")


profile_agent = ProfileAgent()
