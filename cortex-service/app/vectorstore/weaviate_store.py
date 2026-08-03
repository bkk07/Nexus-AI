import weaviate
from langchain_weaviate import WeaviateVectorStore
from config import config
from vectorstore.embeddings import get_embedding_model

def get_weaviate_client() -> weaviate.WeaviateClient:
    """Connects to the local Weaviate container running via Docker."""
    client = weaviate.connect_to_local(
        host=config.WEAVIATE_HOST,
        port=config.WEAVIATE_PORT,
        grpc_port=config.WEAVIATE_GRPC_PORT
    )
    return client

def get_vector_store(index_name: str = "DocumentChunk"):
    """
    Initializes the Weaviate VectorStore with HuggingFace local embeddings.
    Allows Hybrid Search (Dense Vector + BM25) out of the box.
    """
    client = get_weaviate_client()
    embeddings = get_embedding_model()
    
    vector_store = WeaviateVectorStore(
        client=client,
        index_name=index_name,
        text_key="content",
        embedding=embeddings
    )
    return vector_store