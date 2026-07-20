from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class VectorStore(ABC):
    """向量存储抽象基类"""

    @abstractmethod
    def add_documents(
        self,
        docs: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """添加文档"""
        pass

    @abstractmethod
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None,
    ) -> List[Dict]:
        """相似性搜索"""
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str):
        """删除集合"""
        pass

    @abstractmethod
    def get_collection(self):
        """获取集合"""
        pass

    @abstractmethod
    def delete_documents(self, ids: List[str]):
        """删除文档"""
        pass
