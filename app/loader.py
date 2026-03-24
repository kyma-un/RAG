from langchain_community.document_loaders import PyPDFLoader
import os
import uuid
from datetime import datetime


def load_pdf(file_path, original_filename=None):
    loader = PyPDFLoader(file_path)
    docs = loader.load()

    normalized_filename = original_filename or os.path.basename(file_path)
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
    uploaded_at = datetime.utcnow().isoformat() + "Z"
    document_id = str(uuid.uuid4())

    for doc in docs:
        doc.metadata["id"] = document_id
        doc.metadata["filename"] = normalized_filename
        doc.metadata["size"] = file_size
        doc.metadata["uploadedAt"] = uploaded_at
        doc.metadata["status"] = "indexed"
        doc.metadata["source"] = normalized_filename

    return docs