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
