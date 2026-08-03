# Cortex Service REST API Handbook

## Authentication
All API requests to the Cortex engine must include an Authorization header containing a valid Bearer token:

`Authorization: Bearer <your_jwt_token>`

## Endpoints

### 1. Execute RAG Workflow
`POST /v1/chat/completions`

#### Request Payload
```json
{
  "query": "What is our PTO rollover policy?",
  "enable_reflection": true,
  "top_k": 3
}