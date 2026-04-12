import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Sequence

from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

from .document import Document
from .embedding import Embedder


class VectorStore(ABC):
    """Contrato de almacenamiento para vectores y metadata."""

    @abstractmethod
    def add(self, docs: List[Document], embeddings: List[List[float]]) -> None:
        """Agrega documentos y embeddings al almacenamiento."""

    @abstractmethod
    def search(
        self, query: str, k: int, filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Busca documentos similares usando filtros opcionales de metadata."""

    @abstractmethod
    def all_documents(self, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Retorna todos los documentos indexados, con filtros opcionales."""


class _EmbedderAdapter(Embeddings):
    """Adaptador para exponer Embedder con la interfaz Embeddings de LangChain."""

    def __init__(self, embedder: Embedder):
        self.embedder = embedder

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self.embedder.embed_query(text)


class FaissVectorStore(VectorStore):
    """Vector store con FAISS y persistencia opcional en disco."""

    def __init__(
        self,
        embedder: Embedder,
        persist_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.persist_path = persist_path
        self._embedding_adapter = _EmbedderAdapter(embedder)
        self._db: Optional[FAISS] = None

        if self.persist_path and self._has_persisted_index():
            self._db = FAISS.load_local(
                self.persist_path,
                self._embedding_adapter,
                allow_dangerous_deserialization=True,
            )

    def add(self, docs: List[Document], embeddings: List[List[float]]) -> None:
        if not docs:
            return

        texts = [doc.content for doc in docs]
        metadatas = [doc.metadata for doc in docs]

        if self._db is None:
            self._db = self._create_index(texts, metadatas, embeddings)
        else:
            self._append_to_index(texts, metadatas, embeddings)

        self._save()

    def search(
        self, query: str, k: int, filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        if self._db is None:
            return []

        if k <= 0:
            return []

        filter_fn = self._build_filter(filters)
        fetch_k = max(k * 4, k)

        if filter_fn is None:
            hits = self._db.similarity_search(query=query, k=k)
        else:
            hits = self._db.similarity_search(query=query, k=fetch_k, filter=filter_fn)
            hits = hits[:k]

        return [
            Document(content=hit.page_content, metadata=hit.metadata or {}) for hit in hits
        ]

    def all_documents(self, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        if self._db is None:
            return []

        filter_fn = self._build_filter(filters)
        docs: List[Document] = []

        for langchain_doc in self._db.docstore._dict.values():
            metadata = langchain_doc.metadata or {}
            if filter_fn and not filter_fn(metadata):
                continue
            docs.append(Document(content=langchain_doc.page_content, metadata=metadata))

        return docs

    def _create_index(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: Sequence[Sequence[float]],
    ) -> FAISS:
        if embeddings and len(embeddings) == len(texts):
            text_embeddings = list(zip(texts, embeddings))
            try:
                return FAISS.from_embeddings(
                    text_embeddings=text_embeddings,
                    embedding=self._embedding_adapter,
                    metadatas=metadatas,
                )
            except Exception as exc:
                self.logger.warning(
                    "Fallo en from_embeddings; se usa calculo interno de embeddings: %s", exc
                )

        return FAISS.from_texts(
            texts=texts,
            embedding=self._embedding_adapter,
            metadatas=metadatas,
        )

    def _append_to_index(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if embeddings and len(embeddings) == len(texts):
            text_embeddings = list(zip(texts, embeddings))
            try:
                self._db.add_embeddings(
                    text_embeddings=text_embeddings,
                    metadatas=metadatas,
                )
                return
            except Exception as exc:
                self.logger.warning(
                    "Fallo al agregar embeddings; se agrega por texto: %s",
                    exc,
                )

        self._db.add_texts(texts=texts, metadatas=metadatas)

    def _build_filter(
        self, filters: Optional[Dict[str, Any]]
    ) -> Optional[Callable[[Dict[str, Any]], bool]]:
        if not filters:
            return None

        def _matches(metadata: Dict[str, Any]) -> bool:
            metadata = metadata or {}
            for key, expected in filters.items():
                current = metadata.get(key)
                if isinstance(expected, (list, tuple, set)):
                    if current not in expected:
                        return False
                elif current != expected:
                    return False
            return True

        return _matches

    def _has_persisted_index(self) -> bool:
        if not self.persist_path:
            return False
        return os.path.isfile(os.path.join(self.persist_path, "index.faiss")) and os.path.isfile(
            os.path.join(self.persist_path, "index.pkl")
        )

    def _save(self) -> None:
        if not self.persist_path or self._db is None:
            return
        os.makedirs(self.persist_path, exist_ok=True)
        self._db.save_local(self.persist_path)
