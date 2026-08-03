from langchain_huggingface import HuggingFaceEmbeddings
from app.config import config

# Global cache for the embedding model
_embedding_model = None

def get_embedding_model():
    """Returns a cached singleton instance of the HuggingFace embedding model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL_NAME
        )
    return _embedding_model