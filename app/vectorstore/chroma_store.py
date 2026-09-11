"""ChromaDB 向量存储 - LangChain 版本

使用 langchain_chroma.Chroma 封装，兼容 LangChain 的 VectorStore 接口。
默认使用 BGE 中文嵌入模型，中文效果远优于 Chroma 默认的 all-MiniLM。
"""
import os
import asyncio
from typing import List, Dict, Optional, Any

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logger import log
from app.embeddings.bge_embeddings import bge_embeddings


class ChromaVectorStore:
    """Chroma 向量存储（LangChain 版本）

    封装 langchain_chroma.Chroma，提供业务接口和 LangChain 原生接口。
    同时保留旧 API（similarity_search 返回 dict），保证其他 Agent 不受影响。
    """

    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
        embeddings=None,
    ):
        self.collection_name = collection_name or settings.CHROMA_COLLECTION
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        self.embeddings = embeddings or bge_embeddings

        os.makedirs(self.persist_directory, exist_ok=True)

        log.info(
            f"初始化 Chroma 向量存储: collection={self.collection_name}, "
            f"persist_dir={self.persist_directory}"
        )

        self._chroma = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
        )

        log.info("Chroma 向量存储初始化完成")

    @property
    def native(self) -> Chroma:
        """返回原生 LangChain Chroma 实例，用于 LCEL 等场景"""
        return self._chroma

    async def preload(self) -> None:
        """预加载嵌入模型（异步，不阻塞事件循环）"""
        log.info("预加载嵌入模型...")
        await self.embeddings.apreload()
        log.info("嵌入模型预加载完成")

    # ── LangChain 原生接口（供 RAGRetriever 使用）──────────

    def add_documents_langchain(self, documents: List[Document], ids: Optional[List[str]] = None) -> List[str]:
        if not documents:
            return []
        doc_ids = self._chroma.add_documents(documents=documents, ids=ids)
        log.info(f"成功添加 {len(documents)} 个文档到向量库")
        return doc_ids

    async def asimilarity_search(self, query: str, k: int = 5, filter: Optional[dict] = None) -> List[Document]:
        """异步相似度搜索（BGE 嵌入是同步的，通过线程池执行避免阻塞事件循环）"""
        log.info(f"开始相似度搜索: query='{query[:50]}', k={k}")
        return await asyncio.to_thread(self._chroma.similarity_search, query, k, filter)

    def as_retriever(self, search_kwargs: Optional[dict] = None):
        return self._chroma.as_retriever(search_kwargs=search_kwargs or {"k": 3})

    # ── 旧 API（保证 teacher.py / student.py 不受影响）──────

    def similarity_search(self, query: str, k: int = 5, filter: Optional[Dict] = None) -> List[Dict]:
        """相似性搜索（旧接口，返回 dict 格式）"""
        results = self._chroma.similarity_search(query=query, k=k, filter=filter)
        return [
            {
                "id": doc.metadata.get("id", str(i)),
                "document": doc.page_content,
                "metadata": doc.metadata,
                "distance": doc.metadata.get("distance", None),
            }
            for i, doc in enumerate(results)
        ]

    def add_documents(self, docs: List[str], metadatas: Optional[List[Dict]] = None, ids: Optional[List[str]] = None) -> List[str]:
        """添加文档（旧接口，接收字符串列表）"""
        if not docs:
            return []
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(docs))]
        if metadatas is None:
            metadatas = [{} for _ in range(len(docs))]
        documents = [
            Document(page_content=doc, metadata=meta)
            for doc, meta in zip(docs, metadatas)
        ]
        return self._chroma.add_documents(documents=documents, ids=ids)

    def delete_collection(self, collection_name: Optional[str] = None):
        """删除集合"""
        try:
            self._chroma.delete_collection()
            log.info(f"集合 {self.collection_name} 已删除")
        except Exception as e:
            log.warning(f"删除集合失败: {e}")

    def get_collection(self):
        """获取原生 ChromaDB collection（兼容旧代码）"""
        return self._chroma._collection

    def delete_documents(self, ids: List[str]):
        if ids:
            self._chroma.delete(ids=ids)
            log.info(f"成功删除 {len(ids)} 个文档")

    def delete_documents_by_filter(self, where: Dict) -> int:
        """按 metadata 过滤删除文档（资源重生成时清旧分块）

        Returns:
            删除的文档数量（尽力而为，Chroma 底层不总返回计数时为 -1）
        """
        if not where:
            return -1
        try:
            coll = self._chroma._collection
            existing = coll.get(where=where)
            ids = existing.get("ids") or []
            if ids:
                coll.delete(ids=ids)
                log.info(f"按过滤条件删除 {len(ids)} 个文档块: {where}")
                return len(ids)
            return 0
        except Exception as e:
            log.warning(f"按过滤条件删除文档失败: {e}")
            return -1


vector_store = ChromaVectorStore()
