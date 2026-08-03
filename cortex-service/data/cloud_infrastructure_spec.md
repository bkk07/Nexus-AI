# Nexus Cloud Infrastructure & Deployment Spec

## 1. Microservice Architecture
The Nexus AI platform is deployed across three primary AWS regions: `us-east-1`, `eu-central-1`, and `ap-southeast-1`.

### Core Service Topology
* **Cortex Engine:** Python FastAPI service executing LangGraph agentic workflows.
* **Weaviate Vector Cluster:** Dockerized vector database operating on port `8080` (REST) and `50051` (gRPC).
* **Redis Sentinel:** Distributed caching layer for session state and rate limiting (Port `6379`).

## 2. Service Level Agreements (SLA) & Limits
* **Platform Availability Target:** 99.95% uptime per calendar month.
* **Target Query Latency:** Under 200ms for standard vector search; under 1500ms for full Agentic reflection loops.
* **Rate Limits:** Enterprise tier accounts are throttled at 500 requests per minute (RPM). Exceeding this limit triggers HTTP `429 Too Many Requests`.

## 3. Environment Configuration
Required environment variables for the production container:

```env
WEAVIATE_HOST=weaviate.internal.nexus
WEAVIATE_PORT=8080
WEAVIATE_GRPC_PORT=50051
GROQ_API_KEY=gsk_prod_live_key_99x
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
MAX_AGENT_RETRIES=2