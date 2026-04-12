import logging
from typing import List, Optional, Protocol


class MCPSourceRouter(Protocol):
    """Contrato para futura seleccion de fuentes basada en MCP/tools."""

    def select_sources(
        self,
        query: str,
        supported_sources: List[str],
    ) -> Optional[List[str]]:
        """Retorna fuentes seleccionadas o None para buscar en todas."""


class PlaceholderMCPRouter:
    """Router placeholder por defecto hasta conectar herramientas MCP."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def select_sources(
        self,
        query: str,
        supported_sources: List[str],
    ) -> Optional[List[str]]:
        self.logger.info(
            "Se llamo el router placeholder MCP para '%s' con fuentes=%s. Retorna None => todas.",
            query,
            supported_sources,
        )
        return None
