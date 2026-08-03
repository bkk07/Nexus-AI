from langchain_huggingface import HuggingFaceEmbeddings
from config import config

def get_embedding_model():
    """Returns local embedding model."""
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL_NAME
    )