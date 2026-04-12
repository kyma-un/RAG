import logging
from typing import List, Optional

from rag.core.document import Document
from rag.core.vectorstore import VectorStore


class MultiSourceRetriever:
    """Recupera chunks semanticamente similares en una o varias fuentes."""

    def __init__(self, vector_store: VectorStore, logger: Optional[logging.Logger] = None):
        self.vector_store = vector_store
        self.logger = logger or logging.getLogger(__name__)

    def retrieve(
        self, query: str, sources: Optional[List[str]] = None, k: int = 5
    ) -> List[Document]:
        filters = None
        if sources:
            filters = {"source": sources}

        return self.vector_store.search(query=query, k=k, filters=filters)
