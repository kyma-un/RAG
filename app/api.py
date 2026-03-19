from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

from .rag import RAG
from .logging.SQLiteLogger import SQLiteLogger

from .loader import load_pdf

app = FastAPI()

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

@app.post("/ingest")
async def ingest(file:UploadFile = File(...)):
    if file.content_type != "application/pdf":
        return {"error" : "solo se permiten archivos pdf"}

    temp_path = f"./files/temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    docs = load_pdf(temp_path)

    rag.ingest(docs)

    return {"status": "ok", "message": f"{file.filename} agregado al vector store"}
    