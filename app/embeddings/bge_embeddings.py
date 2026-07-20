"""BGE 中文嵌入模型 - LangChain Embeddings 封装

使用 BAAI 的 bge-small-zh 模型，中文效果比 Chroma 默认的 all-MiniLM 好。
模型会自动下载到本地缓存。
"""
import os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import asyncio
from typing import List
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
import numpy as np

from app.core.logger import log


class BgeEmbeddings(Embeddings):
    """BGE 中文嵌入模型

    基于 sentence-transformers 的 BGE 系列模型，针对中文优化。
    默认使用 bge-small-zh-v1.5，体积小速度快。
    """

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        self.model_name = model_name
        self._model = None
        log.info(f"BGE 嵌入模型初始化（懒加载）: {model_name}")

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
            log.info(f"BGE 嵌入模型加载完成: {self.model_name}")
        return self._model

    def preload(self) -> None:
        _ = self.model

    async def apreload(self) -> None:
        if self._model is None:
            await asyncio.to_thread(self.preload)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        if isinstance(embeddings, np.ndarray):
            embeddings = embeddings.tolist()
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        return embedding

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return await asyncio.to_thread(self.embed_documents, texts)

    async def aembed_query(self, text: str) -> List[float]:
        return await asyncio.to_thread(self.embed_query, text)


bge_embeddings = BgeEmbeddings()
