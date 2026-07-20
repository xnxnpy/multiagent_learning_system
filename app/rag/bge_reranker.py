"""BGE 重排序模型

使用 BAAI 的 bge-reranker 模型，对检索结果进行重排序。
基于 sentence-transformers CrossEncoder，中文效果好。
"""
import os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import asyncio
from typing import List, Tuple
from sentence_transformers import CrossEncoder
import numpy as np

from app.core.logger import log


class BgeReranker:
    """BGE 重排序器

    使用交叉编码器（Cross-Encoder）对文档进行精确排序。
    默认使用 bge-reranker-base，速度和效果均衡。
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self._model = None
        log.info(f"BGE 重排序模型初始化（懒加载）: {model_name}")

    @property
    def model(self) -> CrossEncoder:
        if self._model is None:
            self._model = CrossEncoder(self.model_name)
            log.info(f"BGE 重排序模型加载完成: {self.model_name}")
        return self._model

    def preload(self) -> None:
        _ = self.model

    async def apreload(self) -> None:
        if self._model is None:
            await asyncio.to_thread(self.preload)

    def rerank(self, query: str, documents: List[str], top_k: int = None) -> List[int]:
        if not documents:
            return []
        return [idx for idx, _ in self.rerank_with_scores(query, documents, top_k)]

    async def arerank(self, query: str, documents: List[str], top_k: int = None) -> List[int]:
        if not documents:
            return []
        return await asyncio.to_thread(self.rerank, query, documents, top_k)

    def rerank_with_scores(self, query: str, documents: List[str], top_k: int = None) -> List[Tuple[int, float]]:
        if not documents:
            return []

        pairs = [[query, doc] for doc in documents]
        scores = self.model.predict(pairs)

        if isinstance(scores, np.ndarray):
            scores = scores.tolist()

        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: x[1], reverse=True)

        if top_k:
            indexed = indexed[:top_k]

        return indexed

    async def arerank_with_scores(self, query: str, documents: List[str], top_k: int = None) -> List[Tuple[int, float]]:
        if not documents:
            return []
        return await asyncio.to_thread(self.rerank_with_scores, query, documents, top_k)


bge_reranker = BgeReranker()
