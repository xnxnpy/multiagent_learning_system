import json
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.agents.utils import extract_json
from app.core.model_manager import ModelManagerChatModel
from app.core.logger import log
from app.models import StudentProfile, LearningPath, AsyncSessionLocal

# 保持后台任务引用，防止被垃圾回收
_background_tasks: set = set()

# 每个用户的 WS 写锁（防止后台任务并发写入）
_ws_write_locks: Dict[int, asyncio.Lock] = {}

# 画像维度定义：(字段名, 中文标签, 类型)
# 顺序即提问优先级
DIMENSIONS: List[Tuple[str, str, str]] = [
    ("major", "专业", "str"),
    ("grade", "年级", "str"),
    ("goal", "学习目标", "str"),
    ("knowledge_level", "知识水平", "str"),
    ("learning_style", "学习风格", "str"),
    ("coding_ability", "编程能力", "str"),
    ("interests", "兴趣方向", "list"),
    ("weakness", "薄弱点", "list"),
]

DIM_LABELS = {field: label for field, label, _ in DIMENSIONS}
DIM_TYPES = {field: dtype for field, _, dtype in DIMENSIONS}

# 枚举维度的合法候选值（提取校验用）
GRADE_CANDIDATES = {"大一", "大二", "大三", "大四", "研一", "研二", "研三", "博士"}
STYLE_CANDIDATES = {"看视频", "看文档", "动手实践", "做题"}
CODING_CANDIDATES = {"零基础", "入门", "会基础语法", "中级", "熟练", "精通"}

# 模糊/无信息值：不算有效收集
VAGUE_VALUES = {
    "", " ", "未知", "待完善", "待评估", "其他", "不知道", "一般", "还行", "还可以",
    "大学生", "研究生", "在职", "没接触过", "没学过", "无",
}

# 确认关键词（awaiting_confirm 状态下用户输入匹配任一即视为确认）
CONFIRM_KEYWORDS = {"确认", "确定", "确认无误", "没问题", "好的", "好的确认", "开始", "可以", "ok", "OK", "Ok", "开始生成", "确认完成"}

# 收集状态在 Redis 中的 TTL（7 天）
COLLECT_STATE_TTL = 7 * 24 * 3600


def _get_ws_write_lock(user_id: int) -> asyncio.Lock:
    if user_id not in _ws_write_locks:
        _ws_write_locks[user_id] = asyncio.Lock()
    return _ws_write_locks[user_id]


class ProfileAgent(BaseAgent):
    agent_name = "profile"
    """画像构建 Agent（单维度聚焦收集 + 用户显式确认门闩）"""

    PROMPT_PATH = "prompts/profile_chat_prompt.txt"
    EXTRACT_PROMPT_PATH = "prompts/profile_extract_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)
        self._chat_model = ModelManagerChatModel(agent_name="profile")

    # ── 收集状态（Redis）────────────────────────────────────

    def _state_key(self, user_id: int) -> str:
        return f"profile:collect:{user_id}"

    async def _load_collect_state(self, user_id: int) -> Dict[str, Any]:
        """加载收集状态；不存在时根据现有画像初始化"""
        from app.core.redis_client import get_redis
        try:
            r = await get_redis()
            if r:
                raw = await r.get(self._state_key(user_id))
                if raw:
                    return json.loads(raw)
        except Exception as e:
            log.warning(f"读取画像收集状态失败: {e}")
        return await self._init_collect_state(user_id)

    async def _init_collect_state(self, user_id: int) -> Dict[str, Any]:
        """初始化收集状态。

        迁移策略：现有画像中非模糊值预置为已确认维度；
        若 8 维齐全且已有学习路径，视为已确认（老用户不重复走流程）。
        """
        profile = await self._get_existing_profile(user_id) if self.db else {}
        profile = profile or {}
        confirmed = [field for field, _, dtype in DIMENSIONS if self._is_valid_value(field, profile.get(field), dtype)]

        state = {"confirmed_dims": confirmed, "awaiting_confirm": False, "confirmed": False}
        if len(confirmed) == len(DIMENSIONS):
            has_path = await self._user_has_path(user_id)
            if has_path:
                state["confirmed"] = True
            else:
                state["awaiting_confirm"] = True
        await self._save_collect_state(user_id, state)
        return state

    async def _save_collect_state(self, user_id: int, state: Dict[str, Any]) -> None:
        from app.core.redis_client import get_redis
        try:
            r = await get_redis()
            if r:
                await r.set(self._state_key(user_id), json.dumps(state, ensure_ascii=False), ex=COLLECT_STATE_TTL)
        except Exception as e:
            log.warning(f"保存画像收集状态失败: {e}")

    async def _user_has_path(self, user_id: int) -> bool:
        if not self.db:
            return False
        try:
            result = await self.db.execute(
                select(LearningPath).where(LearningPath.user_id == user_id).limit(1)
            )
            return result.scalar_one_or_none() is not None
        except Exception:
            return False

    # ── 值校验 ─────────────────────────────────────────────

    def _is_valid_value(self, field: str, value: Any, dtype: str) -> bool:
        """值是否算「有效收集」（非空且非模糊）"""
        if dtype == "list":
            if not value or not isinstance(value, list):
                return False
            items = [str(v).strip() for v in value if v and str(v).strip()]
            return any(v not in VAGUE_VALUES for v in items)
        if value is None:
            return False
        v = str(value).strip()
        return bool(v) and v not in VAGUE_VALUES and len(v) >= 2

    def _validate_extracted(self, field: str, value: Any) -> Any:
        """校验并归一化提取结果；非法返回 None"""
        dtype = DIM_TYPES[field]
        if dtype == "list":
            if not isinstance(value, list):
                return None
            items = [str(v).strip() for v in value if v and str(v).strip() and str(v).strip() not in VAGUE_VALUES]
            return items or None
        if value is None:
            return None
        v = str(value).strip()
        if not v or v in VAGUE_VALUES or len(v) < 2:
            return None
        # 枚举维度归一化
        if field == "grade":
            v2 = v.replace("1", "一").replace("2", "二").replace("3", "三").replace("4", "四")
            return v2 if v2 in GRADE_CANDIDATES else (v if v in GRADE_CANDIDATES else v)
        if field == "learning_style":
            for kw, canonical in [("视频", "看视频"), ("文档", "看文档"), ("看书", "看文档"),
                                  ("实践", "动手实践"), ("动手", "动手实践"), ("做题", "做题"), ("练习", "做题")]:
                if kw in v:
                    return canonical
            return v if v in STYLE_CANDIDATES else v
        if field == "coding_ability":
            for kw, canonical in [("零基础", "零基础"), ("没学过", "零基础"), ("不会", "零基础"),
                                  ("入门", "入门"), ("基础语法", "会基础语法"), ("中级", "中级"),
                                  ("熟练", "熟练"), ("精通", "精通")]:
                if kw in v:
                    return canonical
            return v
        return v

    # ── 主流程：流式对话 ───────────────────────────────────

    async def run(self, **kwargs) -> Dict[str, Any]:
        """工作流入口：返回现有画像；不存在则报错（画像必须先经引导式对话收集）"""
        user_id = kwargs.get("user_id")
        profile = await self._get_existing_profile(user_id)
        if not profile or not self._is_valid_value("major", profile.get("major"), "str"):
            raise ValueError("学生画像不存在或未完成，请先通过引导式对话收集画像")
        return profile

    async def run_stream(
        self, user_id: int, user_input: str, chat_history: List[Dict[str, str]] = None,
        ws=None, frontend_profile: Dict[str, Any] = None,
        profile_id: int = None,
    ) -> AsyncGenerator[str, None]:
        log.info(f"ProfileAgent 流式处理用户 {user_id}: {user_input[:50]}...")

        if not profile_id:
            active_profile = await self._get_existing_profile(user_id)
            if active_profile:
                profile_id = active_profile.get("id")

        db_profile = await self._get_existing_profile(user_id, profile_id)
        existing_profile = self._merge_view(db_profile, frontend_profile)

        state = await self._load_collect_state(user_id)
        confirmed_dims = state.get("confirmed_dims", [])
        missing = [field for field, _, _ in DIMENSIONS if field not in confirmed_dims]

        # ── 状态机 ──
        # 已确认：不再提取，提示走编辑入口
        if state.get("confirmed"):
            yield "画像已确认，学习方案已基于此生成。如需修改某项信息，请使用「编辑画像」功能。"
            return

        # 全部维度已收集，等待用户显式确认
        if not missing:
            if self._is_confirmation(user_input):
                state["confirmed"] = True
                state["awaiting_confirm"] = False
                await self._save_collect_state(user_id, state)
                yield "好的，画像已确认，正在为您生成个性化学习方案！"
                if ws:
                    lock = _get_ws_write_lock(user_id)
                    async with lock:
                        try:
                            await ws.send_json({"type": "profile_update", "message": "画像已确认"})
                            await ws.send_json({"type": "check_workflow", "message": "画像已确认，启动学习工作流"})
                        except Exception:
                            pass
                return
            # 非确认输入：引导回复确认
            summary = self._format_summary(existing_profile)
            yield f"画像信息已采集完毕：\n{summary}\n\n请回复「确认」开始生成学习方案。"
            return

        # ── 收集中：单维度提问 + 单维度提取 ──
        current_dim = missing[0]

        chat_prompt = self._load_chat_prompt(existing_profile, current_dim)
        messages = [{"role": "system", "content": chat_prompt}]
        if chat_history:
            for msg in chat_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_input})

        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        lc_messages = []
        for msg in messages:
            role, content = msg["role"], msg["content"]
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

        # 后台：单维度提取 → 保存 → 更新状态 → 通知
        async def _bg_extract_and_notify():
            try:
                extracted = await self._extract_single_dimension(user_input, current_dim)
                value = self._validate_extracted(current_dim, extracted) if extracted is not None else None
                if value is not None:
                    existing_profile[current_dim] = value
                    async with AsyncSessionLocal() as save_db:
                        saver = ProfileAgent(save_db)
                        await saver._save_profile(user_id, existing_profile, profile_id=profile_id)
                    if current_dim not in confirmed_dims:
                        confirmed_dims.append(current_dim)
                else:
                    log.info(f"用户 {user_id} 对维度 {current_dim} 的回答未提取到有效值，等待重答")

                state["confirmed_dims"] = confirmed_dims
                now_missing = [f for f, _, _ in DIMENSIONS if f not in confirmed_dims]
                if not now_missing:
                    state["awaiting_confirm"] = True
                await self._save_collect_state(user_id, state)

                if ws:
                    lock = _get_ws_write_lock(user_id)
                    async with lock:
                        try:
                            await ws.send_json({"type": "profile_update", "message": "画像已更新"})
                            if not now_missing:
                                summary = self._format_summary(existing_profile)
                                await ws.send_json({
                                    "type": "profile_ready",
                                    "message": "画像采集完成，请确认",
                                    "summary": summary,
                                })
                        except Exception:
                            pass
            except Exception as e:
                log.error(f"ProfileAgent 后台提取失败: {e}")

        task = asyncio.create_task(_bg_extract_and_notify())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    # ── 单维度提取 ─────────────────────────────────────────

    async def _extract_single_dimension(self, user_input: str, field: str) -> Any:
        """从用户回答中只提取当前提问的维度；其他维度禁止输出"""
        import os
        label = DIM_LABELS[field]
        dtype = DIM_TYPES[field]

        spec = self._dimension_spec(field)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        with open(os.path.join(base_dir, self.EXTRACT_PROMPT_PATH), 'r', encoding='utf-8') as f:
            template = f.read()
        prompt = template.format(
            dimension=field,
            dimension_label=label,
            dimension_type=dtype,
            dimension_spec=spec,
            user_input=user_input,
        )
        response = await self._call_llm(prompt)
        data = extract_json(response)
        if not isinstance(data, dict):
            log.warning(f"单维度提取 JSON 解析失败: {response[:200]}")
            return None
        return data.get(field)

    def _dimension_spec(self, field: str) -> str:
        specs = {
            "major": "原样保留学生对自己专业的表述。",
            "grade": f"归一化到候选集合：{('、'.join(sorted(GRADE_CANDIDATES)))}。如「大2」归一化为「大二」。",
            "goal": "原样保留学生对学习目标的表述。",
            "knowledge_level": "原样保留学生对知识水平的表述。",
            "learning_style": f"归一化到候选集合：{('、'.join(sorted(STYLE_CANDIDATES)))}。",
            "coding_ability": f"归一化到候选集合：{('、'.join(sorted(CODING_CANDIDATES)))}。",
            "interests": "输出 JSON 数组，只提取学生明确提到的方向，每个元素为字符串。",
            "weakness": "输出 JSON 数组，只提取学生明确表示薄弱/不擅长的内容，每个元素为字符串。",
        }
        return specs.get(field, "")

    # ── 确认判定（确定性，无 LLM）─────────────────────────

    def _is_confirmation(self, user_input: str) -> bool:
        text = user_input.strip()
        if text in CONFIRM_KEYWORDS:
            return True
        # 短回复包含「确认」也接受
        return len(text) <= 6 and "确认" in text

    def _format_summary(self, profile: Dict[str, Any]) -> str:
        parts = []
        for field, label, dtype in DIMENSIONS:
            value = profile.get(field)
            if dtype == "list":
                shown = "、".join(value) if value else "（空）"
            else:
                shown = value or "（空）"
            parts.append(f"{label}：{shown}")
        return "\n".join(parts)

    # ── 画像读写 ───────────────────────────────────────────

    def _merge_view(self, db_profile: Optional[Dict], frontend_profile: Optional[Dict]) -> Dict[str, Any]:
        """合并 DB 画像与前端画像为一个视图（前端值优先，仅非空覆盖）"""
        if frontend_profile and db_profile:
            merged = {}
            for field, _, _ in DIMENSIONS:
                fe_val = frontend_profile.get(field)
                db_val = db_profile.get(field)
                if fe_val and (not isinstance(fe_val, list) or fe_val):
                    merged[field] = fe_val
                else:
                    merged[field] = db_val
            merged["id"] = db_profile.get("id")
            return merged
        if frontend_profile and any(frontend_profile.values()):
            return {k: v for k, v in frontend_profile.items() if v and k in DIM_LABELS}
        return db_profile or {}

    def _load_chat_prompt(self, existing_profile: Dict, current_dim: str) -> str:
        template = self._load_prompt(self.PROMPT_PATH)
        profile_json = json.dumps(existing_profile, ensure_ascii=False) if existing_profile else "{}"
        return template.format(
            existing_profile=profile_json,
            current_dimension=current_dim,
            current_dimension_label=DIM_LABELS[current_dim],
        )

    async def _get_existing_profile(self, user_id: int, profile_id: int = None) -> Optional[Dict[str, Any]]:
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

    async def _save_profile(self, user_id: int, profile_data: Dict[str, Any], profile_id: int = None):
        """保存画像到数据库（upsert）"""
        if not self.db:
            return

        from app.models.upsert import upsert as mysql_upsert

        learning_style = profile_data.get("learning_style")
        if isinstance(learning_style, list):
            learning_style = ", ".join(learning_style)
        elif learning_style is None:
            learning_style = ""

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
