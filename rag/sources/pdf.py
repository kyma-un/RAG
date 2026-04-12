import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

from rag.core.datasource import DataSource
from rag.core.document import Document

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


class PDFSource(DataSource):
    """Carga PDFs desde un directorio y extrae su contenido de texto."""

    def __init__(self, pdf_dir: str, logger: Optional[logging.Logger] = None):
        self.pdf_dir = pdf_dir
        self.logger = logger or logging.getLogger(__name__)

    def get_name(self) -> str:
        return "pdf"

    def load_documents(self) -> List[Document]:
        documents: List[Document] = []

        if PdfReader is None:
            raise ImportError("pypdf es requerido para PDFSource. Instala con: pip install pypdf")

        if not os.path.isdir(self.pdf_dir):
            self.logger.warning("El directorio de PDFs no existe: %s", self.pdf_dir)
            return documents

        for root, _, files in os.walk(self.pdf_dir):
            for file_name in sorted(files):
                if not file_name.lower().endswith(".pdf"):
                    continue

                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, self.pdf_dir)
                abs_path = os.path.abspath(file_path)
                stat = os.stat(file_path)
                uploaded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                doc_id = f"pdf:{abs_path}"

                try:
                    reader = PdfReader(file_path)
                    page_texts = [(page.extract_text() or "") for page in reader.pages]
                    text = "\n".join(page_texts).strip()
                except Exception as exc:
                    self.logger.warning("Se omite PDF no legible %s: %s", file_path, exc)
                    continue

                if not text:
                    continue

                documents.append(
                    Document(
                        content=text,
                        metadata={
                            "id": doc_id,
                            "source": "pdf",
                            "file_name": file_name,
                            "filename": file_name,
                            "path": abs_path,
                            "relative_path": rel_path,
                            "pages": len(page_texts),
                            "size": stat.st_size,
                            "uploadedAt": uploaded_at,
                            "status": "indexed",
                        },
                    )
                )

        return documents
