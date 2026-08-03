from app.vectorstore.weaviate_store import get_weaviate_client

def clear_weaviate_data():
    client = get_weaviate_client()
    collection_name = "DocumentChunk"

    if client.collections.exists(collection_name):
        client.collections.delete(collection_name)
        print(f"-> Collection '{collection_name}' deleted successfully!")
    else:
        print(f"-> Collection '{collection_name}' does not exist.")

if __name__ == "__main__":
    clear_weaviate_data()