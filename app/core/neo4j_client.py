"""
Neo4j 知识图谱客户端
管理 Neo4j 连接池，提供知识图谱的 CRUD 操作
"""
import asyncio
from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logger import log

_driver: Optional[AsyncDriver] = None
_driver_lock = asyncio.Lock()


async def get_neo4j_driver() -> AsyncDriver:
    """获取 Neo4j 异步驱动（单例，双重检查锁）"""
    global _driver
    if _driver is not None:
        return _driver
    async with _driver_lock:
        if _driver is not None:
            return _driver
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        log.info(f"Neo4j 连接成功: {settings.NEO4J_URI}")
        return _driver


async def close_neo4j_driver():
    """关闭 Neo4j 连接"""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None
        log.info("Neo4j 连接已关闭")


class KnowledgeGraphStore:
    """知识图谱 Neo4j 存储操作"""

    @staticmethod
    async def save_graph(user_id: int, stage_id: int, topic: str, graph_data: Dict[str, Any]) -> None:
        """
        将知识图谱保存到 Neo4j（按 user_id + stage_id 隔离）
        使用 MERGE 保证幂等：存在则更新，不存在则创建
        """
        driver = await get_neo4j_driver()
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        label = f"KP_{user_id}"
        rel_type = f"KNOWS_{user_id}"

        async with driver.session() as session:
            tx = await session.begin_transaction()
            try:
                for node in nodes:
                    await tx.run(
                        f"MERGE (n:{label} {{user_id: $user_id, stage_id: $stage_id, nodeId: $nodeId}}) "
                        f"SET n.label = $label_name, n.level = $level, n.description = $description, n.topic = $topic",
                        user_id=user_id,
                        stage_id=stage_id,
                        nodeId=node["id"],
                        label_name=node.get("label", ""),
                        level=node.get("level", 3),
                        description=node.get("description", ""),
                        topic=topic,
                    )

                for edge in edges:
                    rel = edge.get("relationship", "相关")
                    await tx.run(
                        f"MATCH (a:{label} {{user_id: $user_id, stage_id: $stage_id, nodeId: $source}}), "
                        f"     (b:{label} {{user_id: $user_id, stage_id: $stage_id, nodeId: $target}}) "
                        f"MERGE (a)-[r:{rel_type} {{stage_id: $stage_id}}]->(b) "
                        f"SET r.relationship = $rel",
                        user_id=user_id,
                        stage_id=stage_id,
                        source=edge["source"],
                        target=edge["target"],
                        rel=rel,
                    )

                await tx.commit()
            except Exception:
                await tx.rollback()
                raise

        log.info(f"Neo4j 知识图谱已保存，用户 {user_id}，阶段 {stage_id}，{len(nodes)} 节点，{len(edges)} 边")

    @staticmethod
    async def get_graph(user_id: int, stage_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取用户的知识图谱（指定阶段或全部）
        返回 { nodes: [...], edges: [...] }
        """
        driver = await get_neo4j_driver()
        label = f"KP_{user_id}"
        rel_type = f"KNOWS_{user_id}"

        async with driver.session() as session:
            if stage_id is not None:
                result = await session.run(
                    f"MATCH (n:{label} {{stage_id: $stage_id}}) "
                    f"OPTIONAL MATCH (n)-[r:{rel_type} {{stage_id: $stage_id}}]->(m:{label} {{stage_id: $stage_id}}) "
                    f"RETURN n, r, m",
                    stage_id=stage_id,
                )
            else:
                result = await session.run(
                    f"MATCH (n:{label}) "
                    f"OPTIONAL MATCH (n)-[r:{rel_type}]->(m:{label}) "
                    f"RETURN n, r, m"
                )

            nodes_map: Dict[str, Dict] = {}
            edges: List[Dict] = []
            async for record in result:
                n = record["n"]
                nodes_map[n["nodeId"]] = {
                    "id": n["nodeId"],
                    "label": n["label"],
                    "level": n["level"],
                    "description": n["description"],
                    "stage_id": n.get("stage_id"),
                }
                if record["r"] and record["m"]:
                    edges.append({
                        "source": record["r"].nodes[0]["nodeId"],
                        "target": record["r"].nodes[1]["nodeId"],
                        "relationship": record["r"]["relationship"],
                    })

        return {"nodes": list(nodes_map.values()), "edges": edges}

    @staticmethod
    async def get_prerequisites(user_id: int, topic: str, node_label: str) -> List[str]:
        """查询指定知识点的前置依赖"""
        driver = await get_neo4j_driver()
        label = f"KP_{user_id}"
        rel_type = f"KNOWS_{user_id}"

        async with driver.session() as session:
            result = await session.run(
                f"MATCH (m:{label} {{topic: $topic, label: $node_label}})"
                f"<-[r:{rel_type}]-(n:{label} {{topic: $topic}}) "
                f"RETURN n.label AS prereq",
                topic=topic,
                node_label=node_label,
            )
            return [record["prereq"] async for record in result]

    @staticmethod
    async def delete_graph(user_id: int, topic: Optional[str] = None) -> None:
        """删除用户的知识图谱"""
        driver = await get_neo4j_driver()
        label = f"KP_{user_id}"

        async with driver.session() as session:
            if topic:
                await session.run(
                    f"MATCH (n:{label} {{topic: $topic}}) DETACH DELETE n",
                    topic=topic,
                )
            else:
                await session.run(f"MATCH (n:{label}) DETACH DELETE n")

        log.info(f"Neo4j 知识图谱已删除，用户 {user_id}，主题 '{topic or '全部'}'")
