from typing import List, Dict, Any

class GmailSearchTool:
    name: str = "gmail_search"

    def execute(self, args: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
        query = args.get("query", "")
        print(f" -> [Tool: gmail_search] Querying emails for: '{query}' (Integration Stub)")
        return []