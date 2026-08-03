from langchain_groq import ChatGroq
from config import config

def get_fast_llm():
    """Lightweight model for quick routing and extraction."""
    return ChatGroq(
        model_name=config.FAST_LLM_MODEL,
        groq_api_key=config.GROQ_API_KEY,
        temperature=0.0
    )

def get_reasoning_llm():
    """High-capacity model for planning, synthesis, and answer generation."""
    return ChatGroq(
        model_name=config.REASONING_LLM_MODEL,
        groq_api_key=config.GROQ_API_KEY,
        temperature=0.2
    )