import logging
from typing import Any, Dict, List, Optional

from rag.query.mcp_router import MCPSourceRouter
from rag.retrieval.retriever import MultiSourceRetriever


class QueryHandler:
    """Coordina la seleccion del modo de consulta y la recuperacion."""

    def __init__(
        self,
        retriever: MultiSourceRetriever,
        supported_sources: Optional[List[str]] = None,
        auto_router: Optional[MCPSourceRouter] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.retriever = retriever
        self.supported_sources = supported_sources or []
        self.auto_router = auto_router
        self.logger = logger or logging.getLogger(__name__)

    def handle(
        self,
        query: str,
        mode: str = "manual",
        sources: Optional[List[str]] = None,
        k: int = 5,
    ) -> Dict[str, Any]:
        mode = (mode or "manual").lower()
        if mode not in {"manual", "auto"}:
            raise ValueError("mode debe ser 'manual' o 'auto'")

        if mode == "manual":
            selected_sources = self._normalize_sources(sources)
        else:
            selected_sources = self._auto_select_sources(query)

        docs = self.retriever.retrieve(query=query, sources=selected_sources, k=k)

        return {
            "query": query,
            "mode": mode,
            "selected_sources": selected_sources,
            "results": [
                {"content": doc.content, "metadata": doc.metadata} for doc in docs
            ],
        }

    def _auto_select_sources(self, query: str) -> Optional[List[str]]:
        """Punto de entrada para seleccion automatica de fuentes via MCP/tools."""
        if self.auto_router:
            selected = self.auto_router.select_sources(
                query=query,
                supported_sources=self.supported_sources,
            )
            return self._normalize_sources(selected)

        self.logger.info(
            "Se llamo el placeholder de auto para '%s'. Se retorna None => todas las fuentes.",
            query,
        )
        return None

    def _normalize_sources(self, sources: Optional[List[str]]) -> Optional[List[str]]:
        if not sources:
            return None

        normalized = [source.strip().lower() for source in sources if source and source.strip()]
        if not normalized:
            return None
        if "all" in normalized:
            return None
        return sorted(set(normalized))
