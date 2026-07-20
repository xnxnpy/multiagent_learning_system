"""RAG 检索器 - LangChain 版本

基于 Chroma 向量存储的检索器，支持基础检索、BGE 重排序。
完全兼容 LangChain 的 Retriever 接口，可直接用于 LCEL。
"""
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun, AsyncCallbackManagerForRetrieverRun
from pydantic import Field, ConfigDict

from app.vectorstore.chroma_store import vector_store as _default_vector_store
from app.rag.bge_reranker import bge_reranker
from app.core.logger import log


class RAGRetriever(BaseRetriever):
    """RAG 检索器

    基于 Chroma 向量存储 + BGE 重排序的检索器。
    可直接用于 LCEL 链式调用：retriever | prompt | llm | output_parser
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    chroma_store: Any = Field(default=None)
    collection_name: str = "knowledge_base"
    top_k: int = 5
    use_rerank: bool = True

    def __init__(self, collection_name: str = "knowledge_base", top_k: int = 5, use_rerank: bool = True, **kwargs):
        super().__init__(
            chroma_store=_default_vector_store,
            collection_name=collection_name,
            top_k=top_k,
            use_rerank=use_rerank,
            **kwargs,
        )

    @property
    def vector_store(self):
        """兼容旧代码中 retriever.vector_store.xxx 的写法"""
        return self.chroma_store

    async def preload(self) -> None:
        """预加载嵌入模型和重排序模型"""
        log.info("预加载 RAG 检索模型...")
        await self.chroma_store.preload()
        if self.use_rerank:
            await bge_reranker.apreload()
        log.info("RAG 检索模型预加载完成")

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        import asyncio
        return asyncio.run(self._aget_relevant_documents(query, run_manager=run_manager))

    async def _aget_relevant_documents(self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun) -> List[Document]:
        if self.use_rerank:
            return await self.retrieve_with_rerank(query, top_k=self.top_k)
        return await self.retrieve(query, top_k=self.top_k)

    async def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        """基础向量检索"""
        log.info(f"开始向量检索: '{query[:50]}', top_k={top_k}")
        try:
            results = await self.chroma_store.asimilarity_search(query, k=top_k)
            log.info(f"检索完成，找到 {len(results)} 条相关文档")
            return results
        except Exception as e:
            log.error(f"检索失败: {e}")
            return []

    async def retrieve_with_rerank(self, query: str, top_k: int = 5) -> List[Document]:
        """带 BGE 重排序的检索：先取 2 倍候选，再用交叉编码器精排"""
        candidates = await self.retrieve(query, top_k=top_k * 2)
        if not candidates:
            return []
        if len(candidates) <= top_k:
            return candidates
        return await self._rerank_with_bge(query, candidates, top_k)

    async def add_documents(self, documents, ids: Optional[List[str]] = None) -> List[str]:
        """添加文档（兼容 LangChain Document 和旧的 dict 格式）"""
        converted = []
        for doc in documents:
            if isinstance(doc, Document):
                converted.append(doc)
            elif isinstance(doc, dict):
                content = doc.get("content", "") or doc.get("page_content", "")
                meta = {k: v for k, v in doc.items() if k not in ("content", "page_content")}
                converted.append(Document(page_content=content, metadata=meta))
        return self.chroma_store.add_documents_langchain(converted, ids=ids)

    async def delete_documents(self, ids: List[str]) -> None:
        self.chroma_store.delete_documents(ids)

    async def clear_collection(self) -> None:
        self.chroma_store.delete_collection()

    def get_collection_stats(self) -> Dict[str, Any]:
        try:
            collection = self.chroma_store.get_collection()
            if collection:
                count = collection.count()
                return {"document_count": count, "count": count}
        except Exception:
            pass
        return {"document_count": 0, "count": 0}

    async def _rerank_with_bge(self, query: str, docs: List[Document], top_k: int) -> List[Document]:
        doc_texts = [doc.page_content for doc in docs]
        scored_indices = await bge_reranker.arerank_with_scores(query, doc_texts, top_k=top_k)
        reranked = []
        for idx, score in scored_indices:
            doc = docs[idx]
            doc.metadata["rerank_score"] = float(score)
            reranked.append(doc)
        log.info(f"BGE 重排序完成，候选 {len(docs)} 条，返回 {len(reranked)} 条")
        return reranked


retriever = RAGRetriever()
