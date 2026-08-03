import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Weaviate Local Docker settings
    WEAVIATE_HOST: str = os.getenv("WEAVIATE_HOST", "localhost")
    WEAVIATE_PORT: int = int(os.getenv("WEAVIATE_PORT", 8080))
    WEAVIATE_GRPC_PORT: int = int(os.getenv("WEAVIATE_GRPC_PORT", 50051))
    
    # Fast, free Groq models
    FAST_LLM_MODEL: str = "llama-3.1-8b-instant"       # Router / Intent detection
    REASONING_LLM_MODEL: str = "llama-3.3-70b-versatile" # Planning & Final Generation
    
    # Local Embedding model (Runs on CPU/GPU locally)
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"

config = Config()