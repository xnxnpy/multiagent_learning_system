"""LangChain 标准文本分割器封装

使用 RecursiveCharacterTextSplitter，针对中文优化分隔符。
返回 LangChain Document 对象列表。
"""
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.logger import log


class ChineseTextSplitter:
    """中文优化的文本分割器

    使用 RecursiveCharacterTextSplitter，分隔符针对中文标点优化。
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "],
            length_function=len,
        )

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """分割 LangChain Document 列表"""
        if not documents:
            return []
        chunks = self._splitter.split_documents(documents)
        log.info(f"文本分割完成: {len(documents)} 个文档 → {len(chunks)} 个片段")
        return chunks


class MarkdownSplitter:
    """Markdown 优化的文本分割器"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n\n", "\n", " "],
            length_function=len,
        )

    def split_documents(self, documents: List[Document]) -> List[Document]:
        if not documents:
            return []
        return self._splitter.split_documents(documents)


# 向后兼容别名
TextSplitter = ChineseTextSplitter
