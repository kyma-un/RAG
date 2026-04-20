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
- LLM configurable: Ollama, Gemini o Azure OpenAI

## Guia rapida

- Flujo completo Back-First (Back + Front) en Docker: [GUIA_BACK_FRONT_DOCKER.md](GUIA_BACK_FRONT_DOCKER.md)

## Ruta recomendada (Back-First)

El flujo recomendado para este proyecto es:

1. Levantar y validar primero el backend (API + proxy + LLM).
2. Integrar despues la imagen real del frontend.

Secuencia minima sugerida:

1. Copia [\.env.example](.env.example) a `.env` y define proveedor LLM.
2. Copia [deploy/.env.deploy.example](deploy/.env.deploy.example) a `deploy/.env.deploy`.
3. Para fase backend-first, usa frontend placeholder:

```env
FRONTEND_IMAGE=nginx:stable-alpine
```

4. Levanta stack y valida `http://<dominio>/api/docs`.
5. Construye tu imagen real de frontend (repo separado), actualiza `FRONTEND_IMAGE` y redeploy.

## Despliegue con Docker Compose

Este repositorio ahora incluye artefactos para despliegue en servidor local:

- [Dockerfile](Dockerfile): imagen del backend FastAPI.
- [docker-compose.yml](docker-compose.yml): orquesta backend, proxy, frontend (imagen externa), dashboard opcional y Ollama opcional.
- [deploy/Caddyfile](deploy/Caddyfile): reverse proxy para usar un solo dominio.
- [requirements.txt](requirements.txt): dependencias Python reproducibles para build.

### Arquitectura recomendada

- Frontend y backend en contenedores separados.
- Un solo dominio con rutas:
  - `/` -> frontend
  - `/api` -> backend RAG
- Exponer al host solo `80/443` (proxy).
- Persistir volúmenes de `vector_store`, `logs` y `files`.

### 1. Preparar variables

1. Copia [.env.example](.env.example) a `.env`.
2. Ajusta como mínimo:

```env
LLM_PROVIDER=ollama
LLM_FALLBACK_PROVIDER=gemini
GEMINI_API_KEY=tu_api_key
API_ROOT_PATH=/api
CORS_ALLOW_ORIGINS=http://chatbot.lab.local,https://chatbot.lab.local
```

3. Copia [deploy/.env.deploy.example](deploy/.env.deploy.example) a `deploy/.env.deploy` (o exporta variables en shell).
4. Ajusta `DOMAIN` y `FRONTEND_IMAGE` (imagen de tu repo de frontend).

### 2. Levantar stack

#### 2A. Fase Back-First (primero backend)

Si aun no tienes imagen de frontend lista, usa un placeholder temporal en `deploy/.env.deploy`:

```env
FRONTEND_IMAGE=nginx:stable-alpine
```

Luego levanta backend + proxy:

Con Ollama local en Docker:

```powershell
docker compose --env-file deploy/.env.deploy --profile ollama up -d --build
```

Con Gemini o Azure OpenAI (sin Ollama):

```powershell
docker compose --env-file deploy/.env.deploy up -d --build
```

Valida primero backend:

- `http://chatbot.lab.local/api`
- `http://chatbot.lab.local/api/docs`

#### 2B. Integrar frontend real

Si tu frontend esta en otro repo, construye su imagen y etiquetala antes de levantar el stack:

```powershell
docker build -t chatbot-frontend:local <RUTA_AL_REPO_FRONTEND>
```

Luego define en `deploy/.env.deploy`:

```env
FRONTEND_IMAGE=chatbot-frontend:local
```

Reaplica el despliegue:

```powershell
docker compose --env-file deploy/.env.deploy up -d
```

Para levantar dashboard:

```powershell
docker compose --env-file deploy/.env.deploy --profile dashboard up -d
```

### 3. DNS local

Si tienes DNS interno, crea un registro A para `chatbot.lab.local` apuntando a la IP del servidor.

Si no tienes DNS, agrega entrada en `hosts` de tu cliente:

```text
192.168.1.50 chatbot.lab.local
```

### 4. Acceso

- Frontend: `http://chatbot.lab.local/`
- API RAG: `http://chatbot.lab.local/api`
- Swagger: `http://chatbot.lab.local/api/docs`
- Dashboard (si usas perfil `dashboard`): `http://chatbot.lab.local/dashboard/`

Nota: `FRONTEND_IMAGE` debe definirse en `deploy/.env.deploy`. Si lo pones solo en `.env`, puedes tener resultados no esperados segun como ejecutes `docker compose`.

### 5. Persistencia

Docker Compose crea estos volúmenes:

- `rag_vector_store`
- `rag_logs`
- `rag_files`
- `ollama_data` (si usas perfil `ollama`)

Al reiniciar contenedores, se conserva índice FAISS, logs y documentos.

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
pip install python-dotenv google-genai openai ollama pypdf
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

### Opcion C: Azure OpenAI

```env
LLM_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://tu-recurso.openai.azure.com
AZURE_OPENAI_API_KEY=tu_azure_openai_api_key
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_TEMPERATURE=0.2
```

Tambien puedes usar Azure OpenAI como fallback:

```env
LLM_PROVIDER=ollama
LLM_FALLBACK_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://tu-recurso.openai.azure.com
AZURE_OPENAI_API_KEY=tu_azure_openai_api_key
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
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
