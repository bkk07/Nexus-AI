# Cortex Service

Minimal FastAPI service for the Cortex backend.

## Run locally

```bash
uvicorn app.main:app --reload
```

## Health check

```bash
GET /health
```

Expected response:

```json
{ "status": "ok" }
```

## Chat API

Sample request:

```bash
curl -X POST http://127.0.0.1:8000/chat \
	-H "Content-Type: application/json" \
	-d "{\"message\":\"Tell me about FastAPI\"}"
```

Sample response:

```json
{ "response": "FastAPI is a modern Python web framework for building APIs." }
```

