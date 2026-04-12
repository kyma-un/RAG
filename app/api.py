from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional

from fastapi.middleware.cors import CORSMiddleware

from .rag import RAG
from .loggers.SQLiteLogger import SQLiteLogger

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Inicializar el logger y el RAG
logger = SQLiteLogger() #Se puede cambiar luego a PostgreSQLLogger
rag = RAG(logger=logger)

class QueryRequest(BaseModel):
    question: str
    mode: str = "manual"
    sources: Optional[List[str]] = None
    k: int = 5


class IngestSourcesRequest(BaseModel):
    sources: Optional[List[str]] = None


@app.get("/")
def root():
    return {"message": "Bienvenido a la API de RAG. Envia tus preguntas a /ask"}

@app.post("/ask")
def ask(request: QueryRequest):
    result = rag.query(
        question=request.question,
        mode=request.mode,
        sources=request.sources,
        k=request.k,
    )
    return result

@app.post("/documents/upload")
async def ingest(file:UploadFile = File(...)):
    return await rag.ingest_document(file)


@app.post("/documents/ingest-sources")
def ingest_sources(request: IngestSourcesRequest):
    return rag.ingest_sources(request.sources)
    
@app.get("/documents")
def list_documents():
    return {
        "status": "200",
        "documents": rag.get_documents()
    }


@app.get("/sources")
def list_sources():
    return {
        "status": "200",
        "supported_sources": rag.get_supported_sources(),
        "indexed_sources": rag.get_available_sources(),
    }
    