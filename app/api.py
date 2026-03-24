from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

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


@app.get("/")
def root():
    return {"message": "Bienvenido a la API de RAG. Envia tus preguntas a /ask"}

@app.post("/ask")
def ask(request: QueryRequest):
    result = rag.query(request.question)
    return result

@app.post("/documents/upload")
async def ingest(file:UploadFile = File(...)):
    return await rag.ingest(file)
    
@app.get("/documents")
def list_documents():
    return {
        "status": "200",
        "documents": rag.getDocuments()
    }
    