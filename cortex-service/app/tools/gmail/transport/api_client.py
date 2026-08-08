"""GmailAPIClient: thin async wrapper over googleapiclient."""

import asyncio
from googleapiclient.discovery import build

class GmailAPIClient:
    """Wraps synchronous Gmail API calls in async threads."""
    
    def __init__(self, credentials):
        self._service = build('gmail', 'v1', credentials=credentials)

    async def list_messages(self, query: str, max_results: int = 10) -> list:
        def _fetch():
            return self._service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
        
        response = await asyncio.to_thread(_fetch)
        return response.get('messages', [])

    async def get_message(self, message_id: str) -> dict:
        def _fetch():
            return self._service.users().messages().get(
                userId='me', id=message_id, format='full'
            ).execute()
        
        return await asyncio.to_thread(_fetch)