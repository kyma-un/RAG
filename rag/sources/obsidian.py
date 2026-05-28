import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import re

from rag.core.datasource import DataSource
from rag.core.document import Document

# Importar yaml solo si está disponible (mejor práctica)
try:
    import yaml
except ImportError:
    yaml = None


class ObsidianSource(DataSource):
    """Carga notas desde un vault de Obsidian."""

    def __init__(
        self,
        vault_dir: str,
        encoding: str = "utf-8",
        extract_frontmatter: bool = True,
        extract_tags: bool = True,
        extract_links: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        self.vault_dir = vault_dir
        self.encoding = encoding
        self.extract_frontmatter = extract_frontmatter
        self.extract_tags = extract_tags
        self.extract_links = extract_links
        self.logger = logger or logging.getLogger(__name__)

    def get_name(self) -> str:
        return "obsidian"

    def load_documents(self) -> List[Document]:
        """Carga documentos desde el vault de Obsidian."""
        # PASO 1: Inicializar lista vacía
        documents: List[Document] = []

        # PASO 2: Validar que vault_dir existe
        if not os.path.isdir(self.vault_dir):
            self.logger.warning("Vault dir no existe: %s", self.vault_dir)
            return documents

        # PASO 3: Recorrer recursivamente todos los archivos
        for root, _, files in os.walk(self.vault_dir):
            # PASO 3.1: Filtrar solo archivos .md
            for file_name in sorted(files):
                if not file_name.lower().endswith(".md"):
                    continue

                # PASO 3.2: Construir rutas del archivo
                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, self.vault_dir)
                abs_path = os.path.abspath(file_path)

                # PASO 3.3: Intentar cargar el archivo
                try:
                    doc = self._load_single_file(abs_path, file_name, rel_path)
                    if doc:  # Solo agregar si el documento es válido
                        documents.append(doc)
                except Exception as exc:
                    self.logger.warning("Omite archivo %s: %s", file_path, exc)
                    continue  # Continuar con siguiente archivo

        self.logger.info("Cargados %d documentos desde Obsidian", len(documents))
        return documents

    def _load_single_file(
        self,
        abs_path: str,
        file_name: str,
        rel_path: str
    ) -> Optional[Document]:
        """Carga un archivo .md individual."""

        # PASO 4.1: Leer archivo
        with open(abs_path, "r", encoding=self.encoding) as f:
            content = f.read()

        if not content.strip():  # Archivo vacío
            return None

        # PASO 4.2: Parsear frontmatter YAML
        frontmatter = {}
        text_content = content
        if content.startswith("---"):  # Frontmatter está al inicio
            try:
                # Dividir por separador "---"
                parts = content.split("---", 2)  # máximo 2 divisiones
                if len(parts) >= 3:
                    # parts[0] = "", parts[1] = yaml, parts[2] = contenido
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    text_content = parts[2].strip()
            except Exception as exc:
                self.logger.warning("Frontmatter inválido en %s: %s", file_name, exc)
                # No fallar, solo ignorar frontmatter

        # PASO 4.3: Extraer metadata del contenido
        tags = self._extract_tags(content) if self.extract_tags else []
        wikilinks = self._extract_wikilinks(content) if self.extract_links else []

        # PASO 4.4: Información del archivo
        stat = os.stat(abs_path)
        uploaded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        doc_id = f"obsidian:{abs_path}"

        # PASO 4.5: Construir metadata del documento
        metadata = {
            # Identificadores
            "id": doc_id,
            "source": "obsidian",

            # Ubicación
            "file_name": file_name,
            "filename": file_name,  # Algunos endpoints esperan "filename"
            "path": abs_path,
            "relative_path": rel_path,
            "vault_path": os.path.dirname(rel_path),  # Para filtrar por carpeta

            # Metadatos de archivo
            "size": stat.st_size,
            "uploadedAt": uploaded_at,
            "status": "indexed",
        }

        # PASO 4.6: Extraer y normalizar project (prioridad: frontmatter > nombre de carpeta)
        project_name = None
        project_type = None

        # Intentar extraer del frontmatter primero
        if frontmatter and isinstance(frontmatter, dict) and "project" in frontmatter:
            project_raw = frontmatter["project"]
            # Normalizar el valor del frontmatter
            normalized = self._normalize_project_name(project_raw)
            if normalized:
                project_name = normalized["name"]
                project_type = normalized["type"]
        else:
            # Fallback: extraer del nombre de la carpeta principal (KYMA)
            project_info = self._extract_project_from_path(rel_path)
            if project_info:
                project_name = project_info["name"]
                project_type = project_info["type"]

        # Agregar a metadata si se encontró
        if project_name:
            metadata["project"] = project_name
        if project_type:
            metadata["project_type"] = project_type

        # PASO 4.7: Agregar frontmatter si existe
        if frontmatter:
            metadata["frontmatter"] = frontmatter

        # PASO 4.8: Agregar tags y wikilinks si existen
        if tags:
            metadata["tags"] = tags
        if wikilinks:
            metadata["wikilinks"] = wikilinks

        # PASO 4.9: Retornar Document
        return Document(content=text_content, metadata=metadata)

    def _normalize_project_name(self, project_value: str) -> Optional[Dict[str, str]]:
        """
        Normaliza un nombre de proyecto, extrayendo tipo y nombre.

        Útil para normalizar valores del frontmatter que podrían tener prefijos.

        Retorna un dict con:
        - "type": "proyecto" | "servicio" | "general"
        - "name": nombre normalizado (sin prefijo)

        Estrategia:
        1. Si empieza con "proj-" → type:"proyecto", name sin prefijo
        2. Si empieza con "srv-" → type:"servicio", name sin prefijo
        3. Si otro valor → type:"general", name tal cual

        Ejemplos:
            "proj-apolo" → {"type": "proyecto", "name": "apolo"}
            "srv-ram" → {"type": "servicio", "name": "ram"}
            "kyma" → {"type": "general", "name": "kyma"}
            "banco-calibracion-piezo" → {"type": "general", "name": "banco-calibracion-piezo"}
        """
        if not project_value or not isinstance(project_value, str):
            return None

        project_value = project_value.strip()

        # Si es formato "proj-name"
        if project_value.startswith("proj-"):
            return {
                "type": "proyecto",
                "name": project_value[5:]  # Remover "proj-"
            }

        # Si es formato "srv-name"
        elif project_value.startswith("srv-"):
            return {
                "type": "servicio",
                "name": project_value[4:]  # Remover "srv-"
            }

        # Para otros casos, clasificar como general
        else:
            return {
                "type": "general",
                "name": project_value
            }

    def _extract_project_from_path(self, rel_path: str) -> Optional[Dict[str, str]]:
        """
        Extrae el tipo y nombre del proyecto del path relativo.

        Estrategia de fallback para documentos sin metadata:

        Retorna un dict con:
        - "type": "proyecto" | "servicio" | "general" | None
        - "name": nombre normalizado (sin prefijo)

        Estrategia:
        1. Si "proj-name/..." → type:"proyecto", name:"name"
        2. Si "srv-name/..." → type:"servicio", name:"name"
        3. Si "kyma/..." → type:"general", name:"kyma"
        4. Si "templates/..." → type:"general", name:"templates"
        5. Si está en raíz → return None

        Ejemplos:
            "proj-turing/nota.md" → {"type": "proyecto", "name": "turing"}
            "proj-apolo/wiki/nota.md" → {"type": "proyecto", "name": "apolo"}
            "kyma/actuadores/nota.md" → {"type": "general", "name": "kyma"}
            "srv-ram/nota.md" → {"type": "servicio", "name": "ram"}
            "nota.md" → None
        """
        # Obtener la primera carpeta del path
        parts = rel_path.split(os.sep)

        # Si el archivo está en la raíz (sin carpeta), retornar None
        if len(parts) < 2:
            return None

        first_folder = parts[0]

        # Si es formato "proj-name", clasificar como proyecto
        if first_folder.startswith("proj-"):
            return {
                "type": "proyecto",
                "name": first_folder[5:]  # Remover "proj-"
            }

        # Si es formato "srv-name", clasificar como servicio
        elif first_folder.startswith("srv-"):
            return {
                "type": "servicio",
                "name": first_folder[4:]  # Remover "srv-"
            }

        # Para otros casos (kyma, templates), clasificar como general
        else:
            return {
                "type": "general",
                "name": first_folder
            }

    def _extract_tags(self, content: str) -> List[str]:
        """Extrae hashtags (#tag) del contenido."""
        # Patrón regex: # seguido de caracteres alfanuméricos y guiones
        pattern = r"#[\w\-]+"
        matches = re.findall(pattern, content)
        # Remover # y normalizar a minúsculas
        return list(set(tag[1:].lower() for tag in matches))

    def _extract_wikilinks(self, content: str) -> List[str]:
        """Extrae wikilinks ([[...]]) del contenido."""
        # Patrón regex: [[...]] con cualquier contenido
        pattern = r"\[\[([^\]]+)\]\]"
        matches = re.findall(pattern, content)
        # Devolver lista única (sin duplicados)
        return list(set(matches))
