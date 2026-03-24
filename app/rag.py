from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from fastapi import UploadFile
from .models.LLMFactory import get_llm

import dotenv
import os
import time
from .loggers.BaseLogger import BaseLogger
from app.document_service import (
    enrich_chunk_metadata,
    get_indexed_documents_metadata,
    split_documents,
    upsert_vector_store,
    load_docs_from_upload,
)



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
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        if( os.path.exists("vector_store") and os.path.isdir("vector_store") and len(os.listdir("vector_store")) > 0):
            self.db = FAISS.load_local("vector_store", self.embeddings, allow_dangerous_deserialization=True) # Agregar allow_dangerous_deserialization=True para evitar el error de deserialización porque el archivo lo cree yo
        else:
            self.db = None
        

    def _split_docs(self, docs):
        splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, 
                chunk_overlap=200
            )
        return split_documents(docs, splitter)

    def _create_vectorstore(self, chunks):
        return upsert_vector_store(self.db, chunks, self.embeddings, "vector_store")

    def _build_empty_result(self, question, start_time):
        return {
            "question": question,
            "context": "",
            "answer": "No tengo suficiente información",
            "sources": [],
            "num_sources": 0,
            "context_length": 0,
            "response_time": time.time() - start_time
        }

    def _build_query_result(self, question, context, response, docs, start_time):
        return {
            "question": question,
            "context": context,
            "answer": response,
            "sources": [doc.metadata for doc in docs],
            "num_sources": len(docs),
            "context_length": len(context),
            "response_time": time.time() - start_time
        }

    def _build_prompt(self, question, docs):
        context = "\n".join([doc.page_content for doc in docs])
        prompt = self.PROMPT_TEMPLATE.format(context=context, question=question)
        return context, prompt

    def _log_result(self, result):
        if self.logger:
            self.logger.log_query(result)

    def retrieve(self, question:str):
        return self.db.similarity_search(question, k=3)

    def query(self, question):
        start_time = time.time()

        if not self.db:
            return {
                "error" : "No vector store found. Please ingest documents first."
            }

        docs = self.retrieve(question)
        
        if not docs:
            result = self._build_empty_result(question, start_time)
            self._log_result(result)

            return result

        context, prompt = self._build_prompt(question, docs)

        print("Tokens en el prompt:", len(prompt))

        response = self.llm.generate(prompt)

        result = self._build_query_result(question, context, response, docs, start_time)
        self._log_result(result)

        return result
    
    def getDocuments(self):
        return get_indexed_documents_metadata(self.db)
    

    async def ingest(self, file: UploadFile):
        docs, error = await load_docs_from_upload(file)
        if error:
            return error

        chunks = self._split_docs(docs)
        enrich_chunk_metadata(chunks)
        self.db = self._create_vectorstore(chunks)

        return {"status": "ok", "message": f"{file.filename} agregado al vector store"}