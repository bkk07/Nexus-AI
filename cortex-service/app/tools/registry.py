from typing import Dict
from datetime import datetime

# Base and existing tools
from app.tools.base import Tool
from app.tools.pdf_tool import PDFSearchTool
from app.tools.notion_tool import NotionSearchTool
from app.tools.calendar_tool import CalendarSearchTool
from app.tools.date_tool import DateTool

# --- NEW: Modular Gmail Tool Imports ---
from app.tools.gmail.tool import GmailTool
from app.tools.gmail.auth.token_manager import OAuthTokenManager
from app.tools.gmail.query.compiler import NLQueryCompiler
from app.tools.gmail.query.llm_fallback import LLMQueryFallback
from app.tools.gmail.transport.api_client import GmailAPIClient

# NOTE: Import your LLM generator here (used in your planner/generator nodes)
# Update this path if `get_fast_llm` lives somewhere else like app.graph.nodes
from app.llm.groq_client import get_fast_llm
import os
from google.oauth2.credentials import Credentials 

# ==========================================
# DEPENDENCY SETUP FOR GMAIL TOOL
# ==========================================

class EnvCredentialsStore:
    """
    Constructs Google Credentials dynamically from environment variables.
    """
    async def load(self, project_id: str) -> Credentials:
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            raise ValueError(
                "Missing Google OAuth environment variables. Ensure GOOGLE_CLIENT_ID, "
                "GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN are set."
            )

        # We set token=None because we don't have a live short-lived access token.
        # Your OAuthTokenManager will see this and automatically use the refresh_token 
        # to fetch a fresh access token using the token_uri!
        return Credentials(
            token=None,  
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        
    async def save(self, project_id: str, creds: Credentials) -> None:
        # We don't need to save the short-lived access token to disk since it 
        # is held in memory by the TokenManager and we have the permanent refresh token in env.
        pass

# 1. Initialize the LLM Fallback parser
_llm_client = get_fast_llm()
_llm_fallback = LLMQueryFallback(
    llm_client=_llm_client, 
    reference_datetime_provider=datetime.now
)

# 2. Initialize the Query Compiler (Rules + Fallback)
_query_compiler = NLQueryCompiler(
    llm_fallback=_llm_fallback, 
    reference_datetime_provider=datetime.now
)
# 3. Initialize the Token Manager with the Environment Store
_token_manager = OAuthTokenManager(credentials_store=EnvCredentialsStore())

# ==========================================
# TOOL REGISTRY
# ==========================================


TOOL_REGISTRY: Dict[str, Tool] = {
    "pdf_search": PDFSearchTool(),
    "notion_search": NotionSearchTool(),
    "calendar_search": CalendarSearchTool(),
    "date_tool": DateTool(),
    
    # --- The new enterprise Gmail adapter ---
    "gmail_search": GmailTool(
        token_manager=_token_manager,
        query_compiler=_query_compiler,
        api_client_factory=lambda creds: GmailAPIClient(creds)
    ),
}


def get_tool(name: str) -> Tool:
    return TOOL_REGISTRY.get(name, PDFSearchTool())