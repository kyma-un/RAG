import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from rag.core.datasource import DataSource
from rag.sources.obsidian import ObsidianSource
from rag.sources.pdf import PDFSource


@dataclass
class SourceRegistration:
    """Configuracion registrada para construir una fuente de datos."""

    source_class: Type[DataSource]
    default_kwargs: Dict[str, Any] = field(default_factory=dict)


class SourceRegistry:
    """Registro central de fuentes para creacion y seleccion dinamica."""

    def __init__(self):
        self._registrations: Dict[str, SourceRegistration] = {}

    def register(
        self,
        name: str,
        source_class: Type[DataSource],
        default_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        normalized = self._normalize_name(name)
        self._registrations[normalized] = SourceRegistration(
            source_class=source_class,
            default_kwargs=default_kwargs or {},
        )

    def supported_sources(self) -> List[str]:
        return sorted(self._registrations.keys())

    def create(self, name: str, **overrides: Any) -> DataSource:
        normalized = self._normalize_name(name)
        registration = self._registrations.get(normalized)
        if not registration:
            raise KeyError(f"Fuente no soportada: {name}")

        kwargs = {**registration.default_kwargs, **overrides}
        return registration.source_class(**kwargs)

    def resolve_selection(self, sources: Optional[List[str]]) -> Dict[str, List[str]]:
        available = self.supported_sources()

        normalized = [
            self._normalize_name(source)
            for source in (sources or [])
            if source and source.strip()
        ]

        if not normalized or "all" in normalized:
            return {"selected": available, "invalid": []}

        selected: List[str] = []
        invalid: List[str] = []

        for source_name in normalized:
            if source_name in self._registrations:
                if source_name not in selected:
                    selected.append(source_name)
            else:
                if source_name not in invalid:
                    invalid.append(source_name)

        return {"selected": selected, "invalid": invalid}

    def create_selected(self, sources: Optional[List[str]]) -> Dict[str, Any]:
        resolution = self.resolve_selection(sources)
        selected_names = resolution["selected"]
        invalid_names = resolution["invalid"]
        instances = [self.create(name) for name in selected_names]

        return {
            "sources": instances,
            "selected": selected_names,
            "invalid": invalid_names,
        }

    @staticmethod
    def _normalize_name(name: str) -> str:
        return (name or "").strip().lower()


def build_default_source_registry() -> SourceRegistry:
    """Crea el registro base de fuentes configurado por variables de entorno."""

    registry = SourceRegistry()
    registry.register(
        name="obsidian",
        source_class=ObsidianSource,
        default_kwargs={
            "vault_dir": os.getenv("OBSIDIAN_VAULT_DIR", "files/obsidian"),
            "encoding": os.getenv("OBSIDIAN_ENCODING", "utf-8"),
        },
    )
    registry.register(
        name="pdf",
        source_class=PDFSource,
        default_kwargs={
            "pdf_dir": os.getenv("PDF_DIR", "files/pdfs"),
        },
    )
    return registry
