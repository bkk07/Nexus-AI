import atexit
import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
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

# Register the cleanup hook to run automatically when Python exits
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