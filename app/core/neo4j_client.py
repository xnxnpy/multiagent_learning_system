"""
Neo4j 知识图谱客户端
管理 Neo4j 连接池，提供知识图谱的 CRUD 操作。

存储规范（P4 统一）：
- 固定标签：节点 KnowledgePoint、关系 KNOWS（不再为每个用户动态建标签）
- 用户隔离：靠 user_id 属性过滤，而非动态标签
- 重新生成：先删后写，杜绝 MERGE 脏合并残留
"""
import asyncio
from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logger import log

_driver: Optional[AsyncDriver] = None
_driver_lock = asyncio.Lock()

NODE_LABEL = "KnowledgePoint"
REL_TYPE = "KNOWS"


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
    """知识图谱 Neo4j 存储操作（固定标签 + user_id 隔离）"""

    @staticmethod
    async def save_graph(user_id: int, topic: str, graph_data: Dict[str, Any]) -> None:
        """保存用户全局知识图谱：先删后写，保证图是原子替换而非脏合并"""
        driver = await get_neo4j_driver()
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        async with driver.session() as session:
            # 1. 先删该用户旧图（原子替换）
            await session.run(
                f"MATCH (n:{NODE_LABEL} {{user_id: $user_id}}) DETACH DELETE n",
                user_id=user_id,
            )

            tx = await session.begin_transaction()
            try:
                for node in nodes:
                    await tx.run(
                        f"MERGE (n:{NODE_LABEL} {{user_id: $user_id, nodeId: $nodeId}}) "
                        f"SET n.label = $label_name, n.level = $level, "
                        f"n.description = $description, n.topic = $topic, "
                        f"n.source = $source, n.seed = $seed",
                        user_id=user_id,
                        nodeId=str(node.get("id", "")),
                        label_name=node.get("label", ""),
                        level=int(node.get("level", 3) or 3),
                        description=node.get("description", ""),
                        topic=topic,
                        source=node.get("source", "llm"),
                        seed=bool(node.get("seed", False)),
                    )

                for edge in edges:
                    rel = edge.get("relationship", "相关")
                    await tx.run(
                        f"MATCH (a:{NODE_LABEL} {{user_id: $user_id, nodeId: $source}}), "
                        f"     (b:{NODE_LABEL} {{user_id: $user_id, nodeId: $target}}) "
                        f"MERGE (a)-[r:{REL_TYPE}]->(b) "
                        f"SET r.relationship = $rel, r.user_id = $user_id",
                        user_id=user_id,
                        source=str(edge.get("source", "")),
                        target=str(edge.get("target", "")),
                        rel=rel,
                    )

                await tx.commit()
            except Exception:
                await tx.rollback()
                raise

        log.info(
            f"Neo4j 知识图谱已保存（先删后写），用户 {user_id}，"
            f"{len(nodes)} 节点，{len(edges)} 边"
        )

    @staticmethod
    async def get_graph(user_id: int) -> Dict[str, Any]:
        """获取用户全局知识图谱；返回 { nodes, edges }"""
        driver = await get_neo4j_driver()

        async with driver.session() as session:
            result = await session.run(
                f"MATCH (n:{NODE_LABEL} {{user_id: $user_id}}) "
                f"OPTIONAL MATCH (n)-[r:{REL_TYPE}]->(m:{NODE_LABEL} {{user_id: $user_id}}) "
                f"RETURN n, r, m",
                user_id=user_id,
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
                    "source": n.get("source", "llm"),
                    "seed": bool(n.get("seed", False)),
                }
                if record["r"] and record["m"]:
                    edges.append({
                        "source": record["r"].nodes[0]["nodeId"],
                        "target": record["r"].nodes[1]["nodeId"],
                        "relationship": record["r"]["relationship"],
                    })

        return {"nodes": list(nodes_map.values()), "edges": edges}

    @staticmethod
    async def get_prerequisites(user_id: int, node_label: str) -> List[str]:
        """查询指定知识点的前置依赖（入边来源节点）"""
        driver = await get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(
                f"MATCH (m:{NODE_LABEL} {{user_id: $user_id, label: $node_label}})"
                f"<-[r:{REL_TYPE}]-(n:{NODE_LABEL} {{user_id: $user_id}}) "
                f"RETURN n.label AS prereq",
                user_id=user_id,
                node_label=node_label,
            )
            return [record["prereq"] async for record in result]

    @staticmethod
    async def delete_graph(user_id: int) -> None:
        """删除用户的全部知识图谱"""
        driver = await get_neo4j_driver()
        async with driver.session() as session:
            await session.run(
                f"MATCH (n:{NODE_LABEL} {{user_id: $user_id}}) DETACH DELETE n",
                user_id=user_id,
            )
        log.info(f"Neo4j 知识图谱已删除，用户 {user_id}")
