from typing import Dict
from app.tools.base import Tool
from app.tools.pdf_tool import PDFSearchTool
from app.tools.gmail_tool import GmailSearchTool
from app.tools.notion_tool import NotionSearchTool
from app.tools.calendar_tool import CalendarSearchTool
from app.tools.date_tool import DateTool  # <--- Added import

TOOL_REGISTRY: Dict[str, Tool] = {
    "pdf_search": PDFSearchTool(),
    "gmail_search": GmailSearchTool(),
    "notion_search": NotionSearchTool(),
    "calendar_search": CalendarSearchTool(),
    "date_tool": DateTool(),  # <--- Registered DateTool
}


def get_tool(name: str) -> Tool:
    return TOOL_REGISTRY.get(name, PDFSearchTool())