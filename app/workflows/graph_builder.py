import json
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from app.core.logger import log
from app.core.redis_client import get_redis
from app.agents.profile_agent import ProfileAgent
from app.agents.learning_path_agent import LearningPathAgent
from app.agents.document_agent import DocumentAgent
from app.agents.question_agent import QuestionAgent
from app.agents.code_agent import CodeAgent
from app.agents.mindmap_agent import MindmapAgent
from app.agents.evaluation_agent import create_evaluation_agent
from sqlalchemy.ext.asyncio import AsyncSession

# 每个用户的进度回调（用于步骤内发送中间进度到前端）
_progress_callbacks: Dict[int, Any] = {}


class AgentState(BaseModel):
    """工作流状态"""
    user_id: int = Field(..., description="用户 ID")
    db: Optional[AsyncSession] = Field(None, description="数据库会话（运行时注入，不序列化）")
    session_id: str = Field(..., description="会话 ID")

    # 阶段状态
    profile_built: bool = Field(False, description="画像是否已构建")
    path_generated: bool = Field(False, description="学习路径是否已生成")
    document_generated: bool = Field(False, description="文档是否已生成")
    questions_generated: bool = Field(False, description="题目是否已生成")
    code_generated: bool = Field(False, description="代码是否已生成")
    mindmap_generated: bool = Field(False, description="思维导图是否已生成")
    reading_generated: bool = Field(False, description="拓展阅读是否已生成")
    glossary_generated: bool = Field(False, description="术语词汇是否已生成")
    summary_generated: bool = Field(False, description="学习总结是否已生成")
    ppt_video_generated: bool = Field(False, description="PPT视频是否已生成")
    evaluated: bool = Field(False, description="是否已评估")

    # 输出结果
    profile: Optional[Dict] = Field(None, description="学生画像")
    learning_path: Optional[Dict] = Field(None, description="学习路径")
    ppt_video: Optional[Dict] = Field(None, description="PPT教学视频")
    evaluation: Optional[Dict] = Field(None, description="评估结果")
    
    # 当前步骤和历史
    current_step: str = Field("start", description="当前步骤")
    steps_history: list = Field([], description="步骤历史")
    progress: float = Field(0.0, description="进度 0-1")
    
    # 错误信息
    error: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        arbitrary_types_allowed = True


# 模块级 db 缓存，解决 LangGraph 序列化丢失 db 的问题
_db_sessions: Dict[int, AsyncSession] = {}


def get_user_db(user_id: int) -> AsyncSession:
    """获取当前工作流用户的 db session"""
    return _db_sessions.get(user_id)


class WorkflowBuilder:
    """工作流构建器"""
    
    def __init__(self):
        self.graph = None
        self.total_steps = 3

    def build_workflow(self):
        """构建学习路径工作流（画像 → 路径 → 全局知识图谱）

        资源生成已迁移到 stage_workflow.py 的 Supervisor 学习环，
        由学生进入具体阶段时按需增量触发，不再在此一次性全量生成。
        """
        log.info("开始构建学习路径工作流")

        workflow = StateGraph(AgentState)

        workflow.add_node("build_profile", self._build_profile)
        workflow.add_node("generate_path", self._generate_path)
        workflow.add_node("generate_knowledge_graph", self._generate_knowledge_graph)

        workflow.set_entry_point("build_profile")

        workflow.add_edge("build_profile", "generate_path")
        workflow.add_edge("generate_path", "generate_knowledge_graph")
        workflow.add_edge("generate_knowledge_graph", END)

        self.graph = workflow.compile()
        log.info("学习路径工作流构建完成")
        return self.graph
    
    async def _build_profile(self, state: AgentState) -> Dict[str, Any]:
        """构建学生画像（已存在则跳过）"""
        log.info(f"工作流步骤：构建学生画像，用户 {state.user_id}")
        db = get_user_db(state.user_id)

        step_info = {"step": "build_profile", "status": "started", "timestamp": self._get_timestamp()}
        state.steps_history.append(step_info)
        state.current_step = "build_profile"
        state.progress = 1 / self.total_steps

        if not db:
            log.error(f"工作流：用户 {state.user_id} 的 db session 未找到")
            step_info["status"] = "failed"
            step_info["error"] = "数据库会话未初始化"
            return {
                **state.dict(),
                "error": "数据库会话未初始化",
                "steps_history": state.steps_history,
                "current_step": "build_profile",
                "progress": 1 / self.total_steps
            }

        # 检查是否已有画像
        from sqlalchemy import select as sa_select
        from app.models import StudentProfile
        result = await db.execute(
            sa_select(StudentProfile).where(
                StudentProfile.user_id == state.user_id,
                StudentProfile.is_active == True,
            )
        )
        existing = result.scalar_one_or_none()
        log.info(f"工作流：用户 {state.user_id} 画像查询结果: {'存在' if existing else '不存在'}, major={existing.major if existing else 'N/A'}")
        if existing and existing.major:
            log.info(f"用户 {state.user_id} 已有画像，跳过构建")
            step_info["status"] = "skipped"
            profile = {
                "major": existing.major or "",
                "grade": existing.grade or "",
                "goal": existing.goal or "",
                "knowledge_level": existing.knowledge_level or "",
                "learning_style": existing.learning_style or "",
                "interests": existing.interests or [],
                "weakness": existing.weakness or [],
                "coding_ability": existing.coding_ability or ""
            }
            return {
                **state.dict(),
                "profile": profile,
                "profile_built": True,
                "steps_history": state.steps_history,
                "current_step": "build_profile",
                "progress": 1 / self.total_steps
            }

        try:
            profile_agent = ProfileAgent(db)
            profile = await profile_agent.run(user_id=state.user_id)

            step_info["status"] = "completed"
            return {
                **state.dict(),
                "profile": profile,
                "profile_built": True,
                "steps_history": state.steps_history,
                "current_step": "build_profile",
                "progress": 1 / self.total_steps
            }
        except Exception as e:
            log.error(f"构建画像失败: {e}", exc_info=True)
            step_info["status"] = "failed"
            step_info["error"] = str(e)
            return {
                **state.dict(),
                "error": str(e),
                "steps_history": state.steps_history,
                "current_step": "build_profile",
                "progress": 1 / self.total_steps
            }
    
    async def _generate_path(self, state: AgentState) -> Dict[str, Any]:
        """生成学习路径（已存在则跳过）"""
        log.info(f"工作流步骤：生成学习路径，用户 {state.user_id}")
        db = get_user_db(state.user_id)

        step_info = {"step": "generate_path", "status": "started", "timestamp": self._get_timestamp()}
        state.steps_history.append(step_info)
        state.current_step = "generate_path"
        state.progress = 2 / self.total_steps

        # 检查是否已有学习路径（按当前活跃画像）
        from sqlalchemy import select as sa_select
        from app.models import LearningPath, StudentProfile
        # 获取活跃 profile_id
        prof_result = await db.execute(
            sa_select(StudentProfile).where(
                StudentProfile.user_id == state.user_id,
                StudentProfile.is_active == True,
            )
        )
        prof = prof_result.scalar_one_or_none()
        path_query = sa_select(LearningPath).where(LearningPath.user_id == state.user_id)
        if prof:
            path_query = path_query.where(LearningPath.profile_id == prof.id)
        result = await db.execute(
            path_query.order_by(LearningPath.created_at.desc()).limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing and existing.stages:
            log.info(f"用户 {state.user_id} 已有学习路径，跳过生成")
            step_info["status"] = "skipped"

            return {
                **state.dict(),
                "learning_path": {"stages": existing.stages, "title": existing.title},
                "path_generated": True,
                "steps_history": state.steps_history,
                "current_step": "generate_path",
                "progress": 2 / self.total_steps
            }

        try:
            path_agent = LearningPathAgent(db)
            path = await path_agent.run(state.user_id)

            step_info["status"] = "completed"
            return {
                **state.dict(),
                "learning_path": path,
                "path_generated": True,
                "steps_history": state.steps_history,
                "current_step": "generate_path",
                "progress": 2 / self.total_steps
            }
        except Exception as e:
            log.error(f"生成学习路径失败: {e}")
            step_info["status"] = "failed"
            step_info["error"] = str(e)
            return {
                **state.dict(),
                "error": str(e),
                "steps_history": state.steps_history
            }

    async def _generate_knowledge_graph(self, state: AgentState) -> Dict[str, Any]:
        """基于学习路径生成全局知识图谱（存 Neo4j）"""
        log.info(f"工作流步骤：生成知识图谱，用户 {state.user_id}")
        db = get_user_db(state.user_id)
        step_info = {"step": "generate_knowledge_graph", "status": "started", "timestamp": self._get_timestamp()}
        state.steps_history.append(step_info)
        state.current_step = "generate_knowledge_graph"
        state.progress = 3 / self.total_steps

        try:
            # 从学习路径中提取所有阶段信息作为图谱素材
            content_text = ""
            if state.learning_path and state.learning_path.get("stages"):
                for stage in state.learning_path["stages"]:
                    title = stage.get("title", "")
                    desc = stage.get("description", "")
                    kps = stage.get("knowledge_points", [])
                    kp_names = []
                    for kp in kps:
                        if isinstance(kp, dict):
                            kp_names.append(kp.get("name", ""))
                        else:
                            kp_names.append(str(kp))
                    content_text += f"## {title}\n{desc}\n知识点：{'、'.join(kp_names)}\n\n"

            topic = self._extract_topic(state)

            from app.agents.knowledge_graph_agent import KnowledgeGraphAgent
            kg_agent = KnowledgeGraphAgent(db)
            await kg_agent.run(topic, content=content_text, user_id=state.user_id, stage_id=None, force=True)

            step_info["status"] = "completed"
            return {
                **state.dict(),
                "steps_history": state.steps_history,
                "current_step": "generate_knowledge_graph",
                "progress": 3 / self.total_steps
            }
        except Exception as e:
            log.warning(f"知识图谱生成失败（不影响后续流程）: {e}")
            step_info["status"] = "failed"
            step_info["error"] = str(e)
            return {
                **state.dict(),
                "steps_history": state.steps_history,
                "current_step": "generate_knowledge_graph",
                "progress": 3 / self.total_steps
            }

    def _extract_topic(self, state: AgentState) -> str:
        """从学习路径阶段中提取主题（资源 topic 必须来自阶段，不能用画像目标）"""
        kps = self._get_stage_kp_names(state)
        if kps:
            # 限制知识点数量，避免过多导致 topic 过长
            limited_kps = kps[:5]
            # 每个知识点名称截断到20字以内
            safe_kps = [kp[:20] if len(kp) > 20 else kp for kp in limited_kps]
            topic = "、".join(safe_kps)
            # 最终限制 topic 总长度
            if len(topic) > 80:
                topic = "、".join(safe_kps[:3])
                if len(topic) > 80:
                    topic = safe_kps[0][:40] if safe_kps else "学习基础"
            return topic
        # 知识节点为空时用阶段标题
        if state.learning_path and state.learning_path.get("stages"):
            stage_title = state.learning_path["stages"][0].get("title", "")
            if stage_title.strip():
                return stage_title[:40]
        return "学习基础"

    def _get_stage_kp_names(self, state: AgentState) -> list:
        """从学习路径阶段提取知识点名称列表"""
        if state.learning_path and state.learning_path.get("stages"):
            stage = state.learning_path["stages"][0]
            kps = stage.get("knowledge_points", [])
            if not kps:
                return []
            if isinstance(kps[0], dict):
                return [kp.get("name", "") for kp in kps if kp.get("name")]
            return [str(kp) for kp in kps if kp]
        return []

    async def _evaluate(self, state: AgentState) -> Dict[str, Any]:
        """执行评估"""
        log.info(f"工作流步骤：执行评估，用户 {state.user_id}")
        db = get_user_db(state.user_id)

        step_info = {"step": "evaluate", "status": "started", "timestamp": self._get_timestamp()}
        state.steps_history.append(step_info)
        state.current_step = "evaluate"
        state.progress = 11 / self.total_steps
        
        try:
            evaluation_agent = create_evaluation_agent(db)
            evaluation = await evaluation_agent.run(state.user_id)
            
            step_info["status"] = "completed"
            return {
                **state.dict(),
                "evaluation": evaluation,
                "evaluated": True,
                "steps_history": state.steps_history,
                "current_step": "evaluate",
                "progress": 1.0
            }
        except Exception as e:
            log.error(f"评估失败: {e}")
            step_info["status"] = "failed"
            step_info["error"] = str(e)
            return {
                **state.dict(),
                "error": str(e),
                "steps_history": state.steps_history
            }
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


class WorkflowManager:
    """工作流管理器"""

    def __init__(self):
        self.builder = WorkflowBuilder()
        self.workflow = None
        self.state_expire_time = 3600 * 24 * 7

    def set_progress_callback(self, user_id: int, callback):
        """设置用户的工作流进度回调（用于步骤内发送中间进度）"""
        _progress_callbacks[user_id] = callback

    def clear_progress_callback(self, user_id: int):
        """清除用户的进度回调"""
        _progress_callbacks.pop(user_id, None)
    
    async def start_workflow(self, user_id: int, db: AsyncSession) -> str:
        """启动工作流"""
        session_id = f"workflow_{user_id}_{self._generate_session_id()}"

        if not self.workflow:
            self.workflow = self.builder.build_workflow()

        # 检查画像是否已完善，避免重复构建
        profile_built = False
        try:
            from sqlalchemy import select as sa_select
            from app.models import StudentProfile
            result = await db.execute(sa_select(StudentProfile).where(
                StudentProfile.user_id == user_id,
                StudentProfile.is_active == True,
            ))
            profile = result.scalar_one_or_none()
            if profile and profile.major and profile.grade and profile.goal:
                profile_built = True
        except Exception:
            pass

        initial_state = AgentState(
            user_id=user_id,
            db=db,
            session_id=session_id,
            profile_built=profile_built,
        )
        
        await self._save_state(session_id, initial_state)
        
        return session_id
    
    async def run_workflow(self, session_id: str, db: AsyncSession):
        """运行工作流（逐节点手动执行，避免 astream 缓冲）"""
        state = await self._load_state(session_id)

        if not state:
            raise ValueError(f"工作流状态不存在: {session_id}")

        state.db = db
        _db_sessions[state.user_id] = db

        # 路径规划三步（资源生成已迁移到 stage_workflow Supervisor 学习环）
        steps = [
            "build_profile", "generate_path", "generate_knowledge_graph",
        ]

        try:
            current_input = state.dict()
            for step_name in steps:
                node_fn = getattr(self.builder, f"_{step_name}")
                result = await node_fn(AgentState(**current_input))

                step_state = AgentState(**result)
                step_state.db = db
                await self._save_state(session_id, step_state)
                current_input = step_state.dict()

                yield step_state

                if step_state.error:
                    log.warning(f"工作流步骤 {step_name} 出错: {step_state.error}，停止执行")
                    break
        finally:
            _db_sessions.pop(state.user_id, None)
    
    async def get_state(self, session_id: str) -> Optional[AgentState]:
        """获取工作流状态"""
        return await self._load_state(session_id)
    
    async def resume_workflow(self, session_id: str, db: AsyncSession):
        """恢复工作流"""
        state = await self._load_state(session_id)

        if not state:
            raise ValueError(f"工作流状态不存在: {session_id}")

        state.db = db
        _db_sessions[state.user_id] = db

        steps = [
            "build_profile", "generate_path", "generate_knowledge_graph",
        ]

        try:
            if state.progress >= 1.0:
                yield state
                return

            # 从上次完成的步骤之后继续
            completed_steps = set()
            for sh in state.steps_history:
                if sh.get("status") in ("completed", "skipped"):
                    completed_steps.add(sh["step"])

            current_input = state.dict()
            for step_name in steps:
                if step_name in completed_steps:
                    continue

                node_fn = getattr(self.builder, f"_{step_name}")
                result = await node_fn(AgentState(**current_input))

                step_state = AgentState(**result)
                step_state.db = db
                await self._save_state(session_id, step_state)
                current_input = step_state.dict()

                yield step_state

                if step_state.error:
                    break
        finally:
            _db_sessions.pop(state.user_id, None)

    async def cancel_workflow(self, session_id: str):
        """取消工作流（Redis + MySQL 都清理）"""
        # 清 MySQL
        try:
            from app.models import WorkflowState, AsyncSessionLocal
            from sqlalchemy import delete as sa_delete
            async with AsyncSessionLocal() as db:
                await db.execute(
                    sa_delete(WorkflowState).where(WorkflowState.session_id == session_id)
                )
                await db.commit()
        except Exception as e:
            log.warning(f"MySQL 清除工作流状态失败: {e}")

        # 清 Redis
        try:
            r = await get_redis()
            if r:
                await r.delete(session_id)
        except Exception as e:
            log.warning(f"Redis 清除工作流状态失败: {e}")

        log.info(f"工作流已取消: {session_id}")

    async def _save_state(self, session_id: str, state: AgentState):
        """保存状态到 MySQL + Redis"""
        state_dict = state.dict()
        state_dict.pop('db', None)
        state_json = json.dumps(state_dict, default=str)

        # 1. 写 MySQL（永久保存）
        try:
            from app.models import WorkflowState, AsyncSessionLocal
            from sqlalchemy import select as sa_select
            async with AsyncSessionLocal() as db:
                existing = await db.execute(
                    sa_select(WorkflowState).where(WorkflowState.session_id == session_id)
                )
                record = existing.scalar_one_or_none()
                if record:
                    record.state_data = state_dict
                else:
                    db.add(WorkflowState(
                        session_id=session_id,
                        user_id=state.user_id,
                        state_data=state_dict,
                    ))
                await db.commit()
        except Exception as e:
            log.error(f"MySQL 保存工作流状态失败: {e}")

        # 2. 写 Redis 缓存（最佳努力）
        try:
            r = await get_redis()
            if r:
                await r.set(session_id, state_json, ex=self.state_expire_time)
        except Exception as e:
            log.warning(f"Redis 缓存工作流状态失败（MySQL 已保存）: {e}")

    async def _load_state(self, session_id: str) -> Optional[AgentState]:
        """加载状态：Redis 优先，MySQL 兜底"""
        # 1. 尝试 Redis
        try:
            r = await get_redis()
            if r:
                state_str = await r.get(session_id)
                if state_str:
                    state_dict = json.loads(state_str)
                    return AgentState(**state_dict)
        except Exception as e:
            log.warning(f"Redis 读取工作流状态失败，降级到 MySQL: {e}")

        # 2. MySQL 兜底
        try:
            from app.models import WorkflowState, AsyncSessionLocal
            from sqlalchemy import select as sa_select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    sa_select(WorkflowState).where(WorkflowState.session_id == session_id)
                )
                record = result.scalar_one_or_none()
                if record and record.state_data:
                    state = AgentState(**record.state_data)
                    # 回写 Redis（最佳努力）
                    try:
                        r = await get_redis()
                        if r:
                            await r.set(session_id, json.dumps(record.state_data, default=str), ex=self.state_expire_time)
                    except Exception:
                        pass
                    return state
        except Exception as e:
            log.error(f"MySQL 读取工作流状态失败: {e}")

        return None
    
    def _generate_session_id(self) -> str:
        """生成会话 ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_current_node(self, step_result: Dict) -> str:
        """获取当前节点名称"""
        return next(iter(step_result.keys()))


# 创建全局实例
workflow_manager = WorkflowManager()
