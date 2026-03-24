from datetime import datetime
import os
from langchain_community.vectorstores import FAISS

from .loader import load_pdf


def enrich_chunk_metadata(chunks):
    uploaded_at = datetime.utcnow().isoformat() + "Z"
    for index, chunk in enumerate(chunks):
        filename = chunk.metadata.get("filename") or chunk.metadata.get("source", "unknown")
        chunk.metadata["chunk_index"] = index
        chunk.metadata["chunk_size"] = len(chunk.page_content)
        chunk.metadata["id"] = chunk.metadata.get("id", f"{filename}:{index}")
        chunk.metadata["filename"] = filename
        chunk.metadata["size"] = chunk.metadata.get("size")
        chunk.metadata["uploadedAt"] = chunk.metadata.get("uploadedAt", uploaded_at)
        chunk.metadata["status"] = chunk.metadata.get("status", "indexed")


def get_indexed_documents_metadata(db):
    if not db:
        return []

    by_filename = {}
    for doc in db.docstore._dict.values():
        metadata = doc.metadata or {}
        filename = metadata.get("filename") or metadata.get("source")
        if not filename:
            continue

        if filename not in by_filename:
            by_filename[filename] = {
                "id": metadata.get("id"),
                "filename": filename,
                "size": metadata.get("size"),
                "uploadedAt": metadata.get("uploadedAt"),
                "status": metadata.get("status", "indexed")
            }

    return sorted(by_filename.values(), key=lambda item: item["filename"])


def split_documents(docs, splitter):
    return splitter.split_documents(docs)


def upsert_vector_store(db, chunks, embeddings, vector_store_path="vector_store"):
    if db:
        db.add_documents(chunks)
        db.save_local(vector_store_path)
        return db

    new_db = FAISS.from_documents(chunks, embeddings)
    new_db.save_local(vector_store_path)
    return new_db


async def load_docs_from_upload(file, files_dir="./files"):
    if file.content_type != "application/pdf":
        return None, {"error": "solo se permiten archivos pdf"}

    os.makedirs(files_dir, exist_ok=True)
    file_name = os.path.basename(file.filename)
    file_path = os.path.join(files_dir, file_name)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    docs = load_pdf(file_path, original_filename=file_name)
    return docs, None

