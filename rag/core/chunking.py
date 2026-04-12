from typing import List

from .document import Document


class TextChunker:
    """Divide documentos largos en chunks con solapamiento, preservando metadata."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        if chunk_size <= 0:
            raise ValueError("chunk_size debe ser mayor que 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap no puede ser negativo")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap debe ser menor que chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_documents(self, docs: List[Document]) -> List[Document]:
        chunks: List[Document] = []

        for doc in docs:
            text = doc.content or ""
            if not text:
                continue

            start = 0
            chunk_index = 0
            text_length = len(text)

            while start < text_length:
                end = min(start + self.chunk_size, text_length)
                chunk_text = text[start:end].strip()

                if chunk_text:
                    chunk_metadata = {
                        **doc.metadata,
                        "chunk_index": chunk_index,
                        "chunk_start": start,
                        "chunk_end": end,
                    }
                    chunks.append(Document(content=chunk_text, metadata=chunk_metadata))

                if end >= text_length:
                    break

                start = end - self.chunk_overlap
                chunk_index += 1

        return chunks
