from typing import Protocol, List, Dict, Any


class Tool(Protocol):
    """Common interface for enterprise search tools (PDF, Gmail, Notion, Calendar)."""
    name: str

    def execute(self, args: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
        """Executes the tool query within a project tenant scope."""
        ...
        