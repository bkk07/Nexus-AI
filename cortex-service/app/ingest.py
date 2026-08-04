import os
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.vectorstore.weaviate_store import get_vector_store

DATA_DIR = Path("./data")


def load_documents(data_dir: Path, project_id: str = "proj_phoenix_001") -> List[Document]:
    """Scans the data directory and loads PDF, MD, and TXT files, stamping tenant project_id."""
    documents: List[Document] = []

    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"-> Created missing directory: '{data_dir.resolve()}'. Add your files here!")
        return documents

    files = [f for f in data_dir.rglob("*") if f.is_file()]
    if not files:
        print(f"-> No files found in '{data_dir.resolve()}'. Place some files there and run again.")
        return documents

    for file_path in files:
        ext = file_path.suffix.lower()
        try:
            if ext == ".pdf":
                loader = PyPDFLoader(str(file_path))
                raw_docs = loader.load()
            elif ext in [".txt", ".md"]:
                loader = TextLoader(str(file_path), encoding="utf-8")
                raw_docs = loader.load()
            else:
                print(f"   [Skipped] Unsupported file type: {file_path.name}")
                continue

            # Standardize and enrich baseline metadata including project_id
            for doc in raw_docs:
                doc.metadata["project_id"] = project_id
                doc.metadata["filename"] = file_path.name
                doc.metadata["file_path"] = str(file_path)
                doc.metadata["source"] = file_path.name  # For clean citations

            documents.extend(raw_docs)
            print(f"-> Successfully loaded {len(raw_docs)} document unit(s) from '{file_path.name}' [Project: {project_id}]")

        except Exception as e:
            print(f"   [!] Failed to load '{file_path.name}': {e}")

    return documents


def chunk_documents(documents: List[Document], project_id: str = "proj_phoenix_001") -> List[Document]:
    """Splits raw documents into optimized chunks with boundary preservation and project_id metadata."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,       # Ideal balance for BGE embedding context windows
        chunk_overlap=150,     # Preserves context across sentence cuts
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)

    # Attach explicit chunk index and ensure project_id metadata is stamped on every chunk
    for idx, chunk in enumerate(chunks):
        chunk.metadata["project_id"] = project_id
        chunk.metadata["chunk_id"] = f"{chunk.metadata.get('filename', 'doc')}_{idx}"

    return chunks


def run_ingestion(project_id: str = "proj_phoenix_001"):
    print(f"================ STARTING DOCUMENT INGESTION [Project: {project_id}] ================")
    docs = load_documents(DATA_DIR, project_id=project_id)
    
    if not docs:
        print("-> Ingestion aborted: No valid documents to process.")
        return

    print(f"\n-> Chunking {len(docs)} document page(s)/file(s)...")
    chunks = chunk_documents(docs, project_id=project_id)
    print(f"-> Generated {len(chunks)} text chunks tagged with project_id='{project_id}'.")

    print("\n-> Upserting chunks into local Weaviate vector store...")
    vector_store = get_vector_store()
    vector_store.add_documents(chunks)
    print("================ INGESTION COMPLETE ================")


if __name__ == "__main__":
    run_ingestion()