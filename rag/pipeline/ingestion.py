import logging
from typing import Any, Dict, List, Optional, Sequence

from rag.core.chunking import TextChunker
from rag.core.datasource import DataSource
from rag.core.document import Document
from rag.core.embedding import Embedder
from rag.core.vectorstore import VectorStore


class IngestionPipeline:
    """Orquesta la ingesta de multiples fuentes hacia el vector store."""

    def __init__(
        self,
        sources: Sequence[DataSource],
        chunker: TextChunker,
        embedder: Embedder,
        vector_store: VectorStore,
        logger: Optional[logging.Logger] = None,
    ):
        self.sources = list(sources)
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.logger = logger or logging.getLogger(__name__)

    def run(self) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "sources": {},
            "documents_loaded": 0,
            "chunks_created": 0,
            "indexed_chunks": 0,
        }

        loaded_docs: List[Document] = []

        for source in self.sources:
            source_name = source.get_name()
            try:
                docs = source.load_documents()
                loaded_docs.extend(docs)
                summary["sources"][source_name] = {
                    "status": "ok",
                    "documents": len(docs),
                }
            except Exception as exc:
                self.logger.exception("Fallo de ingesta para la fuente %s", source_name)
                summary["sources"][source_name] = {
                    "status": "error",
                    "documents": 0,
                    "error": str(exc),
                }

        summary["documents_loaded"] = len(loaded_docs)
        if not loaded_docs:
            return summary

        chunks = self.chunker.chunk_documents(loaded_docs)
        summary["chunks_created"] = len(chunks)

        if not chunks:
            return summary

        embeddings = self.embedder.embed([chunk.content for chunk in chunks])
        self.vector_store.add(chunks, embeddings)
        summary["indexed_chunks"] = len(chunks)

        return summary
