# RAG Project

Sistema RAG (Retrieval-Augmented Generation) para consultar documentos PDF, con:
- API en FastAPI
- Cliente por consola
- Dashboard en Streamlit
- Logging de consultas en SQLite

## Stack

- Python 3.10+
- FastAPI + Uvicorn
- LangChain + FAISS
- Sentence Transformers (`all-MiniLM-L6-v2`)
- SQLite
- Streamlit (dashboard)
- LLM configurable: Ollama o Gemini

## Estructura

```text
app/
  api.py
  dashboard.py
  loader.py
  main.py
  rag.py
  logers/
  models/
files/
logs/
vector_store/
```

## 1. Clonar y entrar al proyecto

```powershell
git clone <URL_DEL_REPO>
cd RAG
```

## 2. Crear entorno virtual

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

## 3. Instalar dependencias

```powershell
pip install fastapi uvicorn pydantic python-multipart
pip install langchain-community langchain-text-splitters faiss-cpu sentence-transformers
pip install python-dotenv google-genai ollama pypdf
pip install streamlit pandas matplotlib wordcloud
```

Opcional (recomendado):

```powershell
pip install --upgrade pip
```

## 4. Configurar variables de entorno

Crea un archivo `.env` en la raiz del proyecto con una de estas opciones.

### Opcion A: Ollama (local)

```env
LLM_PROVIDER=ollama
```

Instalar e iniciar Ollama:

1. Descarga Ollama desde `https://ollama.com/download` e instalalo.
2. Verifica que quedo disponible:

```powershell
ollama --version
```

3. Inicia el servicio de Ollama (si no se inicio automaticamente):

```powershell
ollama serve
```

4. En otra terminal, descarga el modelo a usar:

```powershell
ollama pull llama3
```

5. Prueba rapida opcional:

```powershell
ollama run llama3 "Hola, responde en una linea"
```

### Opcion B: Gemini

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=tu_api_key
GEMINI_MODEL=gemini-2.0-flash
```

## 5. Ejecutar la API

Desde la raiz del proyecto:

```powershell
uvicorn app.api:app --reload
```

API docs:
- `http://127.0.0.1:8000/docs`

## 6. Ingestar PDFs

Usa el endpoint `POST /ingest` (desde Swagger UI en `/docs`) para subir PDFs.

Tambien puedes probar con `curl`:

```powershell
curl -X POST "http://127.0.0.1:8000/ingest" -F "file=@files/tu_archivo.pdf"
```

## 7. Hacer preguntas

Endpoint: `POST /ask`

Ejemplo:

```powershell
curl -X POST "http://127.0.0.1:8000/ask" ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Cual es el tema principal del documento?\"}"
```

## 8. Ejecutar modo consola (opcional)

```powershell
python -m app.main
```

## 9. Ejecutar dashboard (opcional)

```powershell
streamlit run app/dashboard.py
```

## Notas importantes

- Si no existe `vector_store`, debes ingestar al menos un PDF antes de consultar.
- El proyecto guarda logs en `logs/logs.db`.
- FAISS se carga con `allow_dangerous_deserialization=True` porque se asume que el `vector_store` es local y de confianza.
- Si usas Ollama, asegurate de tener el servicio corriendo localmente.

## Capacidades multi-fuente

La API ahora soporta consultas por fuentes multiples y modo auto (placeholder para agente/MCP).

### Variables opcionales

```env
OBSIDIAN_VAULT_DIR=files/obsidian
PDF_DIR=files/pdfs
VECTOR_STORE_PATH=vector_store
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=200
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Endpoints nuevos

- `POST /documents/ingest-sources`
  - Ingesta por fuente (`obsidian`, `pdf`, o `all`)
  - Ejemplo body:

```json
{
  "sources": ["obsidian", "pdf"]
}
```

- `GET /sources`
  - Retorna fuentes soportadas e indexadas.

### Endpoint /ask extendido

`POST /ask` ahora acepta:

```json
{
  "question": "Que notas hablan de arquitectura?",
  "mode": "manual",
  "sources": ["obsidian"],
  "k": 5
}
```

- `mode=manual`: usa `sources` (si `sources` es `null` o contiene `all`, consulta todas).
- `mode=auto`: placeholder para enrutamiento por agente/MCP (actualmente consulta todas).

Hook para MCP:
- El punto de extension para enrutamiento automatico de fuentes esta en [rag/query/mcp_router.py](rag/query/mcp_router.py).
- [rag/query/handler.py](rag/query/handler.py) inyecta el router y aplica el resultado como filtro de retrieval.

### Registry de fuentes

- El registro central vive en [rag/sources/registry.py](rag/sources/registry.py).
- [app/rag.py](app/rag.py) usa ese registro para:
  - listar fuentes soportadas
  - resolver seleccion de fuentes en `/documents/ingest-sources`
  - instanciar fuentes sin `if/else` por cada tipo

Para agregar una nueva fuente:

1. Crear una clase en `rag/sources/` que implemente `DataSource`.
2. Registrar la clase en `build_default_source_registry()` dentro de [rag/sources/registry.py](rag/sources/registry.py).
3. Asegurar que la metadata incluya `source` con el nombre registrado.

Con eso, la fuente ya queda disponible en `/sources`, en consultas manuales y en ingesta por fuentes, sin tocar endpoints.

## Troubleshooting rapido

- Error `No vector store found`: ingesta primero un PDF en `/ingest`.
- Error `SQLite objects created in a thread`: el logger ya esta configurado para FastAPI con `check_same_thread=False`.
- Error de imports (`No module named app`): ejecuta con `python -m app.main` desde la raiz.
