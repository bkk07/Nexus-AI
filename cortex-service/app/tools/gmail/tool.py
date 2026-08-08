"""Public LangGraph Tool adapter for Gmail integration."""

from typing import Any, Dict, List
from .schemas import GmailToolArgs, EvidenceItem, GmailActionType
from .auth.token_manager import OAuthTokenManager
# Assuming you have a wrapper for compiler and client factory as outlined in the blueprint
# from .query.compiler import NLQueryCompiler
# from .transport.api_client import GmailAPIClient
from .actions import search_emails # Add other imports like get_thread, etc., as you build them
from .exceptions import GmailToolError

class GmailTool:
    """LangGraph Tool adapter conforming to app.tools.base.Tool protocol."""
    
    name = "gmail"
    
    def __init__(
        self,
        token_manager: OAuthTokenManager,
        query_compiler, # NLQueryCompiler
        api_client_factory,
    ):
        self._token_manager = token_manager
        self._compiler = query_compiler
        self._client_factory = api_client_factory

    async def execute(self, args: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
        # Validate arguments using the Pydantic schema
        parsed = GmailToolArgs.model_validate(args)
        
        # Get safely rotated/refreshed tokens
        creds = await self._token_manager.get_valid_credentials(project_id)
        client = self._client_factory(creds)
        
        try:
            # Map the requested action to the handler
            handlers = {
                GmailActionType.SEARCH_EMAILS: search_emails.run,
                # GmailActionType.GET_THREAD: get_thread.run,
                # GmailActionType.GET_UNREAD_SUMMARY: get_unread_summary.run,
                # GmailActionType.CREATE_DRAFT: create_draft.run,
            }
            
            handler = handlers[parsed.action]
            
            # Execute the action
            items: list[EvidenceItem] = await handler(
                args=parsed, client=client, compiler=self._compiler, project_id=project_id
            )
            
            # Return serialized output for LangGraph state
            return [item.model_dump() for item in items]
            
        except GmailToolError:
            raise
        except Exception as exc:
            raise GmailToolError(f"Unexpected Gmail tool failure: {exc}") from exc