from typing import List, Dict, Any
from app.vectorstore.weaviate_store import hybrid_search


class PDFSearchTool:
    name: str = "pdf_search"

    def execute(self, args: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
        query = args.get("query", "")
        top_k = args.get("top_k", 5)

        print(f" -> [Tool: pdf_search] Searching Weaviate for: '{query}' [Project: {project_id}]")
        results = hybrid_search(query_text=query, project_id=project_id, top_k=top_k, alpha=0.5)

        evidence_items = []
        for item in results:
            evidence_items.append({
                "source_type": "pdf",
                "content": item.get("content", ""),
                "source": item.get("source", "Unknown"),
                "score": item.get("score", 0.0),
                "metadata": {"project_id": project_id}
            })

        return evidence_items