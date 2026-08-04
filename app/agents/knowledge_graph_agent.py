from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.agents.utils import extract_json, normalize_resource_content
from app.core.logger import log

MAX_CONTENT_LENGTH = 8000


class KnowledgeGraphAgent(BaseAgent):
    agent_name = "knowledge_graph"
    """统一知识图谱 Agent — 支持全局图谱（Neo4j）和单阶段关联图（MySQL）"""

    PROMPT_PATH = "prompts/knowledge_graph_prompt.txt"

    def __init__(self, db: AsyncSession = None, scope: str = "path"):
        """
        Args:
            scope: "path" = 全局知识图谱（存 Neo4j），"stage" = 单阶段关联图（存 MySQL）
        """
        super().__init__(db)
        self.scope = scope

    async def run(self, topic: str, content: str = "", user_id: int = None,
                  stage_id: int = None, force: bool = False) -> Dict[str, Any]:
        if self.scope == "path":
            return await self._run_path_scope(topic, content, user_id, force)
        else:
            return await self._run_stage_scope(topic, user_id, stage_id)

    # ── scope="path"：全局知识图谱（存 Neo4j）─────────────────

    async def _run_path_scope(self, topic: str, content: str, user_id: int, force: bool) -> Dict[str, Any]:
        from app.core.neo4j_client import KnowledgeGraphStore

        effective_stage_id = 0
        log.info(f"KnowledgeGraphAgent [path] 为主题 '{topic}' 生成全局知识图谱")

        if user_id and not force:
            existing = await KnowledgeGraphStore.get_graph(user_id, stage_id=effective_stage_id)
            if existing.get("nodes"):
                log.info(f"Neo4j 命中缓存，{len(existing['nodes'])} 节点")
                return existing

        if content and len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]

        prompt = self._load_prompt(self.PROMPT_PATH)
        scope_instructions = """## 全局知识图谱模式（scope=path）
从所有阶段中提取知识点，构建跨阶段的知识关系图：
- 级别1：学习阶段 — 所有阶段同级，每个阶段都是级别1
- 级别2：阶段内的主要知识模块 — 每个阶段至少2-3个
- 级别3：具体概念或技术 — 每个二级节点下至少2个
- 级别4：细节知识点 — 重要的三级节点下延伸1-2个
- 节点数量 20-40 个，级别3和4应占总数60%以上
- 跨阶段关系用"前置"或"依赖"标注
- 确保图谱连通，所有节点都通过边连接"""
        prompt = self._format_prompt(prompt, scope="path", topic=topic, content=content,
                                     profile_context="", scope_instructions=scope_instructions)
        response = await self._call_llm(prompt)

        graph_data = extract_json(response)
        if not graph_data or not self._validate_graph(graph_data):
            log.warning("知识图谱 JSON 提取失败，使用 mock 兜底")
            graph_data = self._get_mock_path_graph(topic)

        graph_data = self._ensure_edges(graph_data)

        if user_id:
            await KnowledgeGraphStore.save_graph(user_id, effective_stage_id, topic, graph_data)

        log.info(f"KnowledgeGraphAgent [path] 完成，节点数: {len(graph_data.get('nodes', []))}")
        return graph_data

    # ── scope="stage"：单阶段关联图（存 MySQL）────────────────

    async def _run_stage_scope(self, topic: str, user_id: int, stage_id: int = None) -> Dict[str, Any]:
        log.info(f"KnowledgeGraphAgent [stage] 为主题 '{topic}' 生成知识点关联图")

        # 查 MySQL 缓存
        if user_id and self.db:
            from app.models import LearningResource
            result = await self.db.execute(
                select(LearningResource).where(
                    LearningResource.user_id == user_id,
                    LearningResource.resource_type == "knowledge_link",
                    LearningResource.topic == topic
                ).order_by(LearningResource.created_at.desc()).limit(1)
            )
            record = result.scalar_one_or_none()
            if record:
                log.info(f"MySQL 命中缓存，主题: {topic}")
                content = record.content
                if isinstance(content, dict):
                    content = normalize_resource_content(content, "knowledge_link")
                return content

        # 获取学生画像
        profile_context = ""
        if user_id and self.db:
            profile = await self._get_profile(user_id)
            if profile:
                weakness_str = ", ".join(profile.get("weakness", [])) or "无"
                profile_context = f"""
## 学生画像
- 知识水平：{profile.get('knowledge_level', '未知')}
- 薄弱点：{weakness_str}
**请将薄弱点相关的知识点标注为重点**
"""

        prompt = self._load_prompt(self.PROMPT_PATH)
        scope_instructions = """## 单阶段关联图模式（scope=stage）
根据指定的知识点主题，生成知识点关联图：
- **所有节点和边必须与主题强关联**，不要引入无关知识点
- 级别1：核心概念（1-2个）
- 级别2：主要分支（3-5个）
- 级别3：具体知识点（6-10个）
- 级别4：细节/应用（5-8个）
- 节点数量 15-30 个，edges 数量 15-25 条"""
        prompt = self._format_prompt(prompt, scope="stage", topic=topic, content="",
                                     profile_context=profile_context, scope_instructions=scope_instructions)
        response = await self._call_llm(prompt)

        result = extract_json(response)
        if not result or not isinstance(result, dict) or "nodes" not in result:
            log.warning("知识点关联图 JSON 提取失败，使用 mock 兜底")
            result = self._get_mock_stage_graph(topic)

        result = normalize_resource_content(result, "knowledge_link")
        log.info(f"KnowledgeGraphAgent [stage] 完成，节点: {len(result.get('nodes', []))}, 边: {len(result.get('edges', []))}")
        return result

    # ── 共用工具方法 ─────────────────────────────────────────

    def _validate_graph(self, data: Dict) -> bool:
        if not isinstance(data, dict):
            return False
        nodes = data.get("nodes")
        if not isinstance(nodes, list) or len(nodes) == 0:
            return False
        for node in nodes:
            if not isinstance(node, dict) or "id" not in node or "label" not in node:
                return False
        return True

    def _ensure_edges(self, data: Dict) -> Dict:
        if data.get("edges") and len(data["edges"]) > 0:
            return data

        nodes = data.get("nodes", [])
        if len(nodes) < 2:
            return data

        edges = []
        levels: Dict[int, List[str]] = {}
        for node in nodes:
            level = node.get("level", 3)
            levels.setdefault(level, []).append(node["id"])

        sorted_levels = sorted(levels.keys())
        for i in range(len(sorted_levels) - 1):
            for parent_id in levels[sorted_levels[i]]:
                for child_id in levels[sorted_levels[i + 1]][:3]:
                    edges.append({"source": parent_id, "target": child_id, "relationship": "包含"})

        for level_ids in levels.values():
            for i in range(len(level_ids) - 1):
                edges.append({"source": level_ids[i], "target": level_ids[i + 1], "relationship": "相关"})

        data["edges"] = edges
        return data

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
                    "knowledge_level": profile.knowledge_level or "",
                    "weakness": profile.weakness or [],
                }
        except Exception as e:
            log.warning(f"获取学生画像失败: {e}")
        return None

    def _get_mock_path_graph(self, topic: str) -> Dict[str, Any]:
        return {
            "title": f"{topic} 知识图谱",
            "knowledge_point_count": 10,
            "nodes": [
                {"id": "n1", "label": topic, "level": 1, "description": "核心主题"},
                {"id": "n2", "label": "基础概念", "level": 2, "description": "基础理论知识"},
                {"id": "n3", "label": "核心技术", "level": 2, "description": "核心技术要点"},
                {"id": "n4", "label": "实践应用", "level": 2, "description": "实际应用场景"},
                {"id": "n5", "label": "概念定义", "level": 3, "description": "核心概念的定义"},
                {"id": "n6", "label": "原理分析", "level": 3, "description": "基本原理说明"},
                {"id": "n7", "label": "算法实现", "level": 3, "description": "关键算法"},
                {"id": "n8", "label": "应用案例", "level": 3, "description": "典型应用"},
                {"id": "n9", "label": "发展历史", "level": 4, "description": "发展历程"},
                {"id": "n10", "label": "未来趋势", "level": 4, "description": "发展趋势"},
            ],
            "edges": [
                {"source": "n1", "target": "n2", "relationship": "包含"},
                {"source": "n1", "target": "n3", "relationship": "包含"},
                {"source": "n1", "target": "n4", "relationship": "包含"},
                {"source": "n2", "target": "n5", "relationship": "包含"},
                {"source": "n2", "target": "n6", "relationship": "包含"},
                {"source": "n3", "target": "n7", "relationship": "包含"},
                {"source": "n4", "target": "n8", "relationship": "包含"},
                {"source": "n5", "target": "n9", "relationship": "相关"},
                {"source": "n6", "target": "n10", "relationship": "相关"},
                {"source": "n7", "target": "n8", "relationship": "应用"},
            ],
        }

    def _get_mock_stage_graph(self, topic: str) -> Dict[str, Any]:
        return {
            "title": f"{topic} 知识点关联图",
            "nodes": [
                {"id": "n1", "label": topic, "level": 1, "description": "核心概念"},
                {"id": "n2", "label": f"{topic}基础", "level": 1, "description": "基础知识"},
                {"id": "n3", "label": f"{topic}原理", "level": 2, "description": "工作原理"},
                {"id": "n4", "label": f"{topic}应用", "level": 2, "description": "实际应用"},
                {"id": "n5", "label": f"{topic}进阶", "level": 3, "description": "高级特性"},
            ],
            "edges": [
                {"source": "n1", "target": "n2", "relationship": "包含"},
                {"source": "n1", "target": "n3", "relationship": "包含"},
                {"source": "n1", "target": "n4", "relationship": "延伸"},
                {"source": "n2", "target": "n3", "relationship": "前置"},
                {"source": "n3", "target": "n5", "relationship": "延伸"},
            ],
        }


knowledge_graph_agent = KnowledgeGraphAgent()
