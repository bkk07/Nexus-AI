from typing import List, Dict, Any

class NotionSearchTool:
    name: str = "notion_search"

    def execute(self, args: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
        query = args.get("query", "")
        print(f" -> [Tool: notion_search] Querying workspace for: '{query}' (Integration Stub)")
        return []