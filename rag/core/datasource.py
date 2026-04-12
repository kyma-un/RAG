from abc import ABC, abstractmethod
from typing import List

from .document import Document


class DataSource(ABC):
    """Interfaz abstracta para todas las fuentes documentales."""

    @abstractmethod
    def load_documents(self) -> List[Document]:
        """Carga y normaliza documentos desde la fuente."""

    @abstractmethod
    def get_name(self) -> str:
        """Retorna un nombre corto y unico de la fuente (ej: obsidian, pdf)."""
