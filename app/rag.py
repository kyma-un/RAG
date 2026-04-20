import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import dotenv
from fastapi import UploadFile

from app.loggers.BaseLogger import BaseLogger
from app.Models.LLMFactory import get_llm
from rag.core import FaissVectorStore, SentenceTransformerEmbedder, TextChunker
from rag.core.document import Document
from rag.pipeline.ingestion import IngestionPipeline
from rag.query import PlaceholderMCPRouter, QueryHandler
from rag.retrieval import MultiSourceRetriever
from rag.sources import build_default_source_registry

dotenv.load_dotenv()


class RAG:
    PROMPT_TEMPLATE = """
    Eres un asistente experto.

    Responde SOLO con base en el contexto dado.
    Si no encuentras la respuesta, di "No tengo suficiente información".

    Contexto:
    {context}

    Pregunta:
    {question}

    Respuesta:
    """

    def __init__(self, logger: BaseLogger = None):
        self.logger = logger
        self.llm = get_llm()

        self.chunker = TextChunker(
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "200")),
        )
        self.embedder = SentenceTransformerEmbedder(
            model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        )
        self.vector_store = FaissVectorStore(
            embedder=self.embedder,
            persist_path=os.getenv("VECTOR_STORE_PATH", "vector_store"),
        )
        self.source_registry = build_default_source_registry()
        self.retriever = MultiSourceRetriever(vector_store=self.vector_store)
        self.query_handler = QueryHandler(
            retriever=self.retriever,
            supported_sources=self.get_supported_sources(),
            auto_router=PlaceholderMCPRouter(),
        )

    def _build_prompt(self, question: str, docs: List[Document]):
        context = "\n".join([doc.content for doc in docs])
        prompt = self.PROMPT_TEMPLATE.format(context=context, question=question)
        return context, prompt

    def _build_empty_result(
        self,
        question: str,
        start_time: float,
        mode: str,
        selected_sources: Optional[List[str]],
    ) -> Dict:
        return {
            "question": question,
            "mode": mode,
            "selected_sources": selected_sources,
            "context": "",
            "answer": "No tengo suficiente información",
            "sources": [],
            "num_sources": 0,
            "context_length": 0,
            "response_time": time.time() - start_time,
        }

    def _build_query_result(
        self,
        question: str,
        context: str,
        response: str,
        docs: List[Document],
        start_time: float,
        mode: str,
        selected_sources: Optional[List[str]],
    ) -> Dict:
        return {
            "question": question,
            "mode": mode,
            "selected_sources": selected_sources,
            "context": context,
            "answer": response,
            "sources": [doc.metadata for doc in docs],
            "num_sources": len(docs),
            "context_length": len(context),
            "response_time": time.time() - start_time,
        }

    def _log_result(self, result: Dict) -> None:
        if self.logger:
            self.logger.log_query(result)

    def query(
        self,
        question: str,
        mode: str = "manual",
        sources: Optional[List[str]] = None,
        k: int = 5,
    ) -> Dict:
        start_time = time.time()

        retrieval = self.query_handler.handle(
            query=question,
            mode=mode,
            sources=sources,
            k=k,
        )

        selected_sources = retrieval.get("selected_sources")
        docs = [
            Document(content=item["content"], metadata=item["metadata"])
            for item in retrieval.get("results", [])
        ]

        if not docs:
            result = self._build_empty_result(
                question=question,
                start_time=start_time,
                mode=mode,
                selected_sources=selected_sources,
            )
            self._log_result(result)
            return result

        context, prompt = self._build_prompt(question, docs)
        response = self.llm.generate(prompt)

        result = self._build_query_result(
            question=question,
            context=context,
            response=response,
            docs=docs,
            start_time=start_time,
            mode=mode,
            selected_sources=selected_sources,
        )
        self._log_result(result)
        return result

    def get_documents(self):
        docs = self.vector_store.all_documents()
        by_file: Dict[str, Dict] = {}

        for doc in docs:
            metadata = doc.metadata or {}
            file_name = metadata.get("file_name") or metadata.get("filename")
            if not file_name:
                continue

            source_name = metadata.get("source") or "unknown"
            unique_key = f"{source_name}:{metadata.get('path') or file_name}"

            candidate = {
                "id": metadata.get("id"),
                "filename": file_name,
                "path": metadata.get("path"),
                "relative_path": metadata.get("relative_path"),
                "source": source_name,
                "size": metadata.get("size"),
                "uploadedAt": metadata.get("uploadedAt"),
                "pages": metadata.get("pages"),
                "status": metadata.get("status", "indexed"),
            }

            current = by_file.get(unique_key)
            if current is None:
                by_file[unique_key] = candidate
                continue

            for field in ["id", "path", "relative_path", "source", "size", "pages", "status"]:
                if (current.get(field) in (None, "")) and (candidate.get(field) not in (None, "")):
                    current[field] = candidate[field]

            current_uploaded = current.get("uploadedAt")
            candidate_uploaded = candidate.get("uploadedAt")
            if candidate_uploaded and (
                not current_uploaded or self._parse_iso_datetime(candidate_uploaded) >= self._parse_iso_datetime(current_uploaded)
            ):
                current["uploadedAt"] = candidate_uploaded

        for summary in by_file.values():
            self._hydrate_summary_from_path(summary)

        return sorted(
            by_file.values(),
            key=lambda item: (item.get("source") or "", item.get("filename") or ""),
        )

    def _parse_iso_datetime(self, value: str) -> datetime:
        if not value:
            return datetime.min.replace(tzinfo=timezone.utc)
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    def _hydrate_summary_from_path(self, summary: Dict) -> None:
        path = summary.get("path")
        if not path or not os.path.isfile(path):
            return

        stat = os.stat(path)
        if summary.get("size") in (None, ""):
            summary["size"] = stat.st_size
        if summary.get("uploadedAt") in (None, ""):
            summary["uploadedAt"] = datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat().replace("+00:00", "Z")

    def get_available_sources(self) -> List[str]:
        docs = self.vector_store.all_documents()
        sources = sorted({doc.metadata.get("source") for doc in docs if doc.metadata.get("source")})
        return sources

    def get_supported_sources(self) -> List[str]:
        return self.source_registry.supported_sources()

    def ingest_sources(self, sources: Optional[List[str]] = None) -> Dict:
        resolved = self.source_registry.create_selected(sources)
        configured_sources = resolved["sources"]
        invalid_sources = resolved["invalid"]

        if not configured_sources:
            return {
                "status": "error",
                "message": "No se seleccionaron fuentes validas",
                "available_sources": self.get_supported_sources(),
                "invalid_sources": invalid_sources,
            }

        pipeline = IngestionPipeline(
            sources=configured_sources,
            chunker=self.chunker,
            embedder=self.embedder,
            vector_store=self.vector_store,
        )
        summary = pipeline.run()
        return {
            "status": "ok",
            "summary": summary,
            "selected_sources": resolved["selected"],
            "invalid_sources": invalid_sources,
        }

    async def ingest_document(self, file: UploadFile):
        if file.content_type != "application/pdf":
            return {"error": "solo se permiten archivos pdf"}

        os.makedirs("files", exist_ok=True)
        file_name = os.path.basename(file.filename)
        file_path = os.path.abspath(os.path.join("files", file_name))

        with open(file_path, "wb") as f:
            f.write(await file.read())

        source = self.source_registry.create("pdf", pdf_dir="files")
        docs = source.load_documents()
        matching = [doc for doc in docs if os.path.basename(doc.metadata.get("path", "")) == file_name]

        if not matching:
            return {"error": "No se pudo extraer contenido del PDF"}

        chunks = self.chunker.chunk_documents(matching)
        embeddings = self.embedder.embed([chunk.content for chunk in chunks])
        self.vector_store.add(chunks, embeddings)

        return {"status": "ok", "message": f"{file.filename} agregado al vector store"}
