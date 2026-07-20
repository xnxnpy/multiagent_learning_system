"""LangChain 标准文档加载器封装

支持格式：PDF、DOCX、TXT、MD/Markdown
返回 LangChain Document 对象列表。
"""
from typing import List
from langchain_core.documents import Document
from app.core.logger import log


class DocumentLoader:
    """文档加载器，根据文件扩展名自动选择 LangChain Loader"""

    EXTENSION_MAP = {
        ".pdf": "_load_pdf",
        ".docx": "_load_docx",
        ".doc": "_load_docx",
        ".txt": "_load_text",
        ".md": "_load_text",
        ".markdown": "_load_text",
    }

    @classmethod
    def load_document(cls, file_path: str) -> List[Document]:
        """加载单个文档，返回 LangChain Document 列表"""
        import os
        ext = os.path.splitext(file_path)[1].lower()
        loader_method = cls.EXTENSION_MAP.get(ext)

        if not loader_method:
            log.warning(f"不支持的文件格式: {ext}，尝试作为文本加载")
            loader_method = "_load_text"

        try:
            docs = getattr(cls, loader_method)(file_path)
            log.info(f"文档加载成功: {file_path} → {len(docs)} 个片段")
            return docs
        except Exception as e:
            log.error(f"文档加载失败: {file_path}, 错误: {e}")
            raise

    @staticmethod
    def _load_pdf(file_path: str) -> List[Document]:
        from langchain_community.document_loaders import PyPDFLoader
        return PyPDFLoader(file_path).load()

    @staticmethod
    def _load_docx(file_path: str) -> List[Document]:
        from langchain_community.document_loaders import Docx2txtLoader
        return Docx2txtLoader(file_path).load()

    @staticmethod
    def _load_text(file_path: str) -> List[Document]:
        from langchain_community.document_loaders import TextLoader
        return TextLoader(file_path, encoding="utf-8").load()

    @classmethod
    def load_documents_from_directory(cls, dir_path: str) -> List[Document]:
        """从目录加载所有支持的文档"""
        import os
        documents = []
        for file in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file)
            if os.path.isfile(file_path):
                try:
                    docs = cls.load_document(file_path)
                    documents.extend(docs)
                except Exception as e:
                    log.warning(f"跳过文件 {file}: {e}")
        return documents
