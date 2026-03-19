from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from .Models.LLMFactory import get_llm

import dotenv
import os
import time
from .logging.BaseLogger import BaseLogger



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
        if( os.path.exists("vector_store")):
            self.db = FAISS.load_local("vector_store", self.embeddings, allow_dangerous_deserialization=True) # Agregar allow_dangerous_deserialization=True para evitar el error de deserialización porque el archivo lo cree yo
        else:
            self.db = None
        
        

    def ingest(self, docs):
        chunks = self._split_docs(docs)
        self._create_vectorstore(chunks)

    def _split_docs(self, docs):
        splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, 
                chunk_overlap=200
            )
        return splitter.split_documents(docs)

    def _create_vectorstore(self, chunks):
        db = FAISS.from_documents(chunks, self.embeddings)
        db.save_local("vector_store")
        self.db = db
                
        
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
            result = {
                "question": question,
                "context": "",
                "answer": "No tengo suficiente información",
                "sources": [],
                "num_sources": 0,
                "context_length": 0,
                "response_time": time.time() - start_time
            }

            if self.logger:
                self.logger.log_query(result)

            return result

        context = "\n".join([doc.page_content for doc in docs])

        prompt = self.PROMPT_TEMPLATE.format(context=context, question=question)

        print("Tokens en el prompt:", len(prompt))

        response = self.llm.generate(prompt)

        result = {
            "question": question,
            "context": context,
            "answer": response,
            "sources": [doc.metadata for doc in docs],
            "num_sources": len(docs),
            "context_length": len(context),
            "response_time": time.time() - start_time
        }

        if self.logger:
            self.logger.log_query(result)

        return result
    