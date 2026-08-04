import atexit
from typing import List, Dict, Any
import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.query import MetadataQuery, Filter
from langchain_weaviate import WeaviateVectorStore
from app.config import config
from app.vectorstore.embeddings import get_embedding_model

_weaviate_client = None
_vector_store = None


def close_weaviate_client():
    """Gracefully closes the Weaviate client connection upon process exit."""
    global _weaviate_client
    if _weaviate_client is not None:
        try:
            _weaviate_client.close()
        except Exception:
            pass

atexit.register(close_weaviate_client)


def get_weaviate_client() -> weaviate.WeaviateClient:
    global _weaviate_client
    if _weaviate_client is None or not _weaviate_client.is_ready():
        _weaviate_client = weaviate.connect_to_local(
            host=config.WEAVIATE_HOST,
            port=config.WEAVIATE_PORT,
            grpc_port=config.WEAVIATE_GRPC_PORT,
            skip_init_checks=True,
            additional_config=AdditionalConfig(
                timeout=Timeout(init=10, query=30, insert=120)
            )
        )
    return _weaviate_client


def get_vector_store(index_name: str = "DocumentChunk"):
    global _vector_store
    if _vector_store is None:
        client = get_weaviate_client()
        embeddings = get_embedding_model()
        _vector_store = WeaviateVectorStore(
            client=client,
            index_name=index_name,
            text_key="content",
            embedding=embeddings
        )
    return _vector_store


def hybrid_search(
    query_text: str,
    project_id: str,
    top_k: int = 5,
    alpha: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Executes Weaviate Hybrid Search filtered strictly by project_id.
    
    Args:
        query_text (str): Search prompt or sub-query.
        project_id (str): Multi-tenant project scope identifier.
        top_k (int): Maximum number of evidence chunks to return.
        alpha (float): 0.0 = pure BM25, 1.0 = pure vector search, 0.5 = hybrid fusion.
    """
    client = get_weaviate_client()
    collection_name = "DocumentChunk"

    if not client.collections.exists(collection_name):
        return []

    collection = client.collections.get(collection_name)
    embeddings = get_embedding_model()

    # 1. Embed query locally via BGE
    query_vector = embeddings.embed_query(query_text)

    # 2. Construct strict project_id payload filter
    tenant_filter = Filter.by_property("project_id").equal(project_id)

    # 3. Execute Weaviate v4 Filtered Hybrid Search
    response = collection.query.hybrid(
        query=query_text,
        vector=query_vector,
        alpha=alpha,
        limit=top_k,
        filters=tenant_filter,
        return_metadata=MetadataQuery(score=True)
    )

    results = []
    for obj in response.objects:
        props = obj.properties
        score = obj.metadata.score if obj.metadata else 0.0

        content = props.get("content") or props.get("text") or ""
        source = props.get("filename") or props.get("source") or "Unknown"

        results.append({
            "content": content,
            "source": source,
            "score": round(float(score), 4),
            "project_id": props.get("project_id", project_id)
        })

    return results