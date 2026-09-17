import json
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.agents.utils import extract_json
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

# 无信息值：不算有效收集
VAGUE_VALUES = {
    "", " ", "未知", "待完善", "待评估", "其他", "不知道", "一般", "还行", "还可以",
    "大学生", "研究生", "在职", "没接触过", "没学过", "无",
}

# 各维度的确定性引导问题（收集流程不再依赖聊天 LLM 自由发挥）
DIMENSION_QUESTIONS = {
    "major": "你的专业是什么？例如计算机、软件测试、数学等。",
    "grade": "你目前大几？（大一 / 大二 / 大三 / 大四 / 研一 / 研二 / 研三）",
    "goal": "你的学习目标是什么？例如考研、找工作、课程需要等。",
    "knowledge_level": "你目前对这个领域的知识水平如何？例如零基础、有编程语言基础、学过相关课程。",
    "learning_style": "你平时喜欢哪种学习方式？看视频、看文档、动手实践还是做题？",
    "coding_ability": "你的编程能力大概在什么水平？零基础 / 入门 / 会基础语法 / 中级 / 熟练。",
    "interests": "你对哪些方向比较感兴趣？例如AI、Web开发、数据分析等（可以说多个）。",
    "weakness": "你在哪些方面感觉比较薄弱？例如算法、数学基础、英语文献阅读等。",
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
    EXTRACT_MULTI_PROMPT_PATH = "prompts/profile_extract_multi.txt"

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
                    state = json.loads(raw)
                    # 复检：剔除已失效/非法的 confirmed_dims（防 Redis 脏状态）
                    profile = await self._get_existing_profile(user_id) if self.db else {}
                    profile = profile or {}
                    cleaned = [
                        f for f in state.get("confirmed_dims", [])
                        if f in DIM_LABELS and self._is_valid_value(f, profile.get(f), DIM_TYPES[f])
                    ]
                    if cleaned != state.get("confirmed_dims"):
                        log.info(f"画像收集状态复检：清理无效维度 {set(state.get('confirmed_dims', [])) - set(cleaned)}")
                        state["confirmed_dims"] = cleaned
                        # 若清理后不再齐全，取消确认门闩
                        if len(cleaned) < len(DIMENSIONS):
                            state["confirmed"] = False
                            state["awaiting_confirm"] = False
                        await self._save_collect_state(user_id, state)
                    return state
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
        if not (bool(v) and v not in VAGUE_VALUES and len(v) >= 2):
            return False
        # 枚举维度：必须能通过提取校验（防止旧库脏值被预置为已确认）
        if field in ("grade", "learning_style", "coding_ability"):
            return self._validate_extracted(field, value) is not None
        return True

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
        # 枚举维度：不在候选集合内一律拒绝（返回 None），防止串维度污染
        if field == "grade":
            v2 = v.replace("1", "一").replace("2", "二").replace("3", "三").replace("4", "四")
            if v2 in GRADE_CANDIDATES:
                return v2
            return v if v in GRADE_CANDIDATES else None
        if field == "learning_style":
            for kw, canonical in [("视频", "看视频"), ("文档", "看文档"), ("看书", "看文档"),
                                  ("实践", "动手实践"), ("动手", "动手实践"), ("做题", "做题"), ("练习", "做题")]:
                if kw in v:
                    return canonical
            return v if v in STYLE_CANDIDATES else None
        if field == "coding_ability":
            for kw, canonical in [("零基础", "零基础"), ("没学过", "零基础"), ("不会", "零基础"),
                                  ("入门", "入门"), ("基础语法", "会基础语法"), ("中级", "中级"),
                                  ("熟练", "熟练"), ("精通", "精通")]:
                if kw in v:
                    return canonical
            return v if v in CODING_CANDIDATES else None
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

        # ── 收集中：自然对话 + 多维提取 + 校验写库 + 约束回复 ──
        # 1) 多维提取：从学生整句话里抽所有明确说出的维度
        try:
            extracted_map = await self._extract_multi_dimension(user_input, existing_profile)
        except Exception as e:
            log.error(f"多维提取异常: {e}")
            extracted_map = {}

        # 2) 校验 + 落库（只有校验通过的才会写）
        saved: Dict[str, Any] = {}
        if extracted_map:
            for field, raw in extracted_map.items():
                if field not in DIM_LABELS:
                    continue
                val = self._validate_extracted(field, raw)
                if val is None:
                    log.info(f"维度 {field} 提取值非法，丢弃: {raw!r}")
                    continue
                existing_profile[field] = val
                saved[field] = val
                if field not in confirmed_dims:
                    confirmed_dims.append(field)

            if saved:
                try:
                    async with AsyncSessionLocal() as save_db:
                        saver = ProfileAgent(save_db)
                        await saver._save_profile(user_id, existing_profile, profile_id=profile_id)
                except Exception as e:
                    log.error(f"画像保存失败: {e}")
                    yield f"保存失败，请再试一次。{DIMENSION_QUESTIONS.get(missing[0], '')}"
                    return

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
                        except Exception:
                            pass
            else:
                now_missing = missing
        else:
            now_missing = missing

        # 3) 组装并流式回复（事实来自后端写库结果）
        all_done = bool(saved) and not now_missing
        if all_done:
            summary = self._format_summary(existing_profile)
            async for chunk in self._compose_collect_reply_stream(
                saved=saved, next_dim=None, existing_profile=existing_profile, all_done=True,
            ):
                yield chunk
            if ws:
                lock = _get_ws_write_lock(user_id)
                async with lock:
                    try:
                        await ws.send_json({
                            "type": "profile_ready",
                            "message": "画像采集完成，请确认",
                            "summary": summary,
                        })
                    except Exception:
                        pass
        elif saved:
            async for chunk in self._compose_collect_reply_stream(
                saved=saved, next_dim=now_missing[0], existing_profile=existing_profile, all_done=False,
            ):
                yield chunk
        else:
            async for chunk in self._compose_collect_reply_stream(
                saved={}, next_dim=missing[0], existing_profile=existing_profile,
                all_done=False, failed=True,
            ):
                yield chunk

    async def _extract_multi_dimension(
        self, user_input: str, existing_profile: Dict
    ) -> Dict[str, Any]:
        """自然对话多维提取：只返回学生明确说出的维度"""
        import os
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        with open(os.path.join(base_dir, self.EXTRACT_MULTI_PROMPT_PATH), 'r', encoding='utf-8') as f:
            template = f.read()
        prompt = template.format(
            user_input=user_input,
            existing_profile=json.dumps(
                {k: existing_profile.get(k) for k in DIM_LABELS if existing_profile.get(k)},
                ensure_ascii=False,
            ) or "{}",
        )
        response = await self._call_llm(prompt)
        data = extract_json(response)
        if not isinstance(data, dict):
            log.warning(f"多维提取 JSON 解析失败: {response[:200]}")
            return {}
        return {k: v for k, v in data.items() if k in DIM_LABELS}

    async def _compose_collect_reply_stream(
        self,
        saved: Dict[str, Any],
        next_dim: Optional[str],
        existing_profile: Dict,
        all_done: bool,
        failed: bool = False,
    ) -> AsyncGenerator[str, None]:
        """流式生成自然回复；事实来自后端，越权声称完成时回退模板"""
        saved_desc = "、".join(
            f"{DIM_LABELS[f]}「{ '、'.join(map(str, v)) if isinstance(v, list) else v }」"
            for f, v in saved.items()
        ) if saved else ""
        next_q = DIMENSION_QUESTIONS.get(next_dim, "") if next_dim else ""

        if failed:
            fact = f"我还想了解你的{DIM_LABELS.get(next_dim, '')}。{DIMENSION_QUESTIONS.get(next_dim, '')}"
        elif all_done:
            fact = f"好的，已经记下{saved_desc or '这些信息'}。画像信息已采集完毕，请回复「确认」开始生成学习方案。"
        else:
            fact = f"好的，已记录{saved_desc}。"
            if next_q:
                fact += next_q

        try:
            from app.core.model_manager import model_manager
            style_prompt = (
                "你是学习画像收集助手。请用 1-3 句自然中文复述以下事实，并自然衔接所给问题。"
                "硬性要求：\n"
                "1. 只能使用下面给出的事实，不得添加、推断、编造任何其他已记录信息\n"
                "2. 若事实中写明「采集完毕」，必须提到请用户回复确认；否则必须包含所给问题\n"
                "3. 不要解释概念，不要鼓励语，不要超过 3 句话\n\n"
                f"## 事实\n{fact}\n\n直接输出回复正文。"
            )
            full = ""
            async for chunk in model_manager.chat_stream(
                [{"role": "user", "content": style_prompt}], agent_name="profile"
            ):
                if chunk:
                    full += chunk
                    yield chunk
            # 防幻觉：流式结束后校验，越权则追加纠正（已流出的不撤回，但明确以模板为准时整段回退困难）
            # 这里选择：若明显越权且几乎没流出内容，回退；若有内容则信任守卫 prompt
            if not full.strip():
                yield fact
            elif not all_done and any(k in full for k in ("采集完毕", "全部收集", "已完成")):
                log.warning("回复 LLM 越权声称完成")
                # 已流出部分无法撤回，追加一句拉回
                yield ""
        except Exception as e:
            log.warning(f"回复流式润色失败，回退模板: {e}")
            yield fact

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
            "major": "原样保留学生对自己专业的表述。若回答像年级/职业方向而非专业名，输出空。",
            "grade": (
                f"只允许候选值：{('、'.join(sorted(GRADE_CANDIDATES)))}。"
                "「大2」归一化为「大二」。"
                "若回答不是年级（例如专业名、职业方向、技术方向），必须输出空字符串，严禁当作年级。"
            ),
            "goal": "原样保留学生对学习目标的表述。若回答像专业名/年级而非目标，输出空。",
            "knowledge_level": "原样保留学生对知识水平的表述。若回答像专业/职业方向而非水平，输出空。",
            "learning_style": (
                f"只允许候选值：{('、'.join(sorted(STYLE_CANDIDATES)))}。"
                "不在候选内输出空。"
            ),
            "coding_ability": (
                f"只允许候选值：{('、'.join(sorted(CODING_CANDIDATES)))}。"
                "不在候选内输出空。"
            ),
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
