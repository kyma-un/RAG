from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Document:
    """Modelo de documento unificado para todas las fuentes y etapas del pipeline."""

    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
