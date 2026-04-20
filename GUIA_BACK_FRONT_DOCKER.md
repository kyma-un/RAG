# Guia operativa: Back-First + Frontend (Docker)

Esta guia prioriza levantar primero el backend RAG y despues integrar el frontend real.

Rutas finales esperadas:

- `/` -> frontend
- `/api` -> backend
- `/api/docs` -> swagger backend

## 1) Prerrequisitos

- Docker Desktop iniciado (Engine running)
- Repo backend RAG con `docker-compose.yml`
- Archivo `deploy/.env.deploy` generado desde `deploy/.env.deploy.example`
- Archivo `.env` del backend generado desde `.env.example`

## 2) Fase Back-First (sin frontend real)

En `deploy/.env.deploy`, usa temporalmente:

```env
FRONTEND_IMAGE=nginx:stable-alpine
```

Esto permite validar API, LLM y proxy aun sin build del frontend.

### Levantar backend

Con Ollama local en Docker:

```powershell
docker compose --env-file deploy/.env.deploy --profile ollama up -d --build
```

Con Gemini o Azure OpenAI (sin Ollama):

```powershell
docker compose --env-file deploy/.env.deploy up -d --build
```

### Verificar backend

- `http://localhost/api`
- `http://localhost/api/docs`

Comandos utiles:

```powershell
docker compose --env-file deploy/.env.deploy ps
docker compose --env-file deploy/.env.deploy logs -f rag-api
docker compose --env-file deploy/.env.deploy logs -f reverse-proxy
```

## 3) Construir imagen del frontend real (repo frontend)

En el repo del frontend:

```powershell
docker build -t chatbot-frontend:local .
docker images | findstr chatbot-frontend
```

Prueba rapida opcional:

```powershell
docker run -d -p 8080:80 --name chatbot-frontend-test chatbot-frontend:local
curl.exe -I http://localhost:8080/
docker rm -f chatbot-frontend-test
```

## 4) Integrar frontend con el backend

En el repo backend, en `deploy/.env.deploy`:

```env
FRONTEND_IMAGE=chatbot-frontend:local
```

Aplicar cambios:

```powershell
docker compose --env-file deploy/.env.deploy up -d
```

## 5) Verificacion end-to-end

- `http://localhost/` -> frontend
- `http://localhost/api/docs` -> swagger backend

Validaciones:

```powershell
docker compose --env-file deploy/.env.deploy ps
docker compose --env-file deploy/.env.deploy logs -f frontend
docker compose --env-file deploy/.env.deploy logs -f rag-api
```

## 6) Comportamiento esperado de APIs

El frontend debe usar rutas relativas bajo `/api`:

- `/api/ask`
- `/api/sources`
- `/api/documents`
- `/api/documents/upload`
- `/api/documents/ingest-sources`

## 7) Problemas comunes

### `docker compose up -d` falla por imagen de frontend

Errores tipicos:

- `Unable to find image 'chatbot-frontend:local' locally`
- `pull access denied for chatbot-frontend`

Causa:

- `FRONTEND_IMAGE` apunta a una imagen que aun no existe localmente o en un registry.

Solucion rapida back-first:

```env
FRONTEND_IMAGE=nginx:stable-alpine
```

Luego vuelve a levantar y valida backend. Cuando tengas el frontend real, cambia de nuevo a `chatbot-frontend:local`.

### Error de daemon / `dockerDesktopLinuxEngine`

Solucion:

```powershell
docker version
```

Si falla, iniciar Docker Desktop.

### Puerto en uso (80/443)

Revisar procesos/contenedores que ya ocupen esos puertos o cambiar `HTTP_PORT` y `HTTPS_PORT` en `deploy/.env.deploy`.

## 8) Comandos de limpieza

```powershell
docker compose --env-file deploy/.env.deploy down
docker rm -f chatbot-frontend-test
```

## 9) Checklist rapido (Back-First)

- [ ] Docker Desktop activo
- [ ] `.env` y `deploy/.env.deploy` creados
- [ ] Stack levanta con `FRONTEND_IMAGE` placeholder
- [ ] Backend responde en `/api/docs`
- [ ] Imagen frontend real construida
- [ ] `FRONTEND_IMAGE=chatbot-frontend:local` aplicado
- [ ] Front responde en `/`
- [ ] Requests del navegador salen a `/api/...`
