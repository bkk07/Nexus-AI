from langchain_core.documents import Document
from app.vectorstore.weaviate_store import get_vector_store


def seed_sample_docs():
    print("Ingesting sample documents into Weaviate...")
    vector_store = get_vector_store()

    sample_documents = [
        Document(
            page_content="Project Strategy Goal 1: Expand regional enterprise market share by 25% through localized customer engagement.",
            metadata={"source": "Project_Strategy_2026.pdf"},
        ),
        Document(
            page_content="Project Strategy Goal 2: Reduce operational query response latency under 200ms using agentic RAG technology.",
            metadata={"source": "Project_Strategy_2026.pdf"},
        ),
        Document(
            page_content="Project Strategy Goal 3: Maintain 99.9% platform availability across all deployed microservices.",
            metadata={"source": "Project_Strategy_2026.pdf"},
        ),
    ]

    vector_store.add_documents(sample_documents)
    print("-> 3 sample strategy documents ingested successfully!")


if __name__ == "__main__":
    seed_sample_docs()