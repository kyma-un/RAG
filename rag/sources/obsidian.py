import logging
from typing import List, Optional

from rag.core.datasource import DataSource
from rag.core.document import Document


class ObsidianSource(DataSource):
    """Placeholder de Obsidian mientras se define la logica final de carga."""

    def __init__(
        self,
        vault_dir: str,
        encoding: str = "utf-8",
        logger: Optional[logging.Logger] = None,
    ):
        self.vault_dir = vault_dir
        self.encoding = encoding
        self.logger = logger or logging.getLogger(__name__)

    def get_name(self) -> str:
        return "obsidian"

    def load_documents(self) -> List[Document]:
        self.logger.info(
            "ObsidianSource esta deshabilitado temporalmente. vault_dir=%s",
            self.vault_dir,
        )
        return []
