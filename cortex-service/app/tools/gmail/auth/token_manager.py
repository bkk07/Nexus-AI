"""Per-tenant token cache with proactive refresh and single-flight locking."""

import time
import asyncio
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from ..exceptions import GmailAuthError

class OAuthTokenManager:
    """Manages token lifecycle safely across concurrent graph nodes."""
    
    def __init__(self, credentials_store, refresh_margin_seconds: int = 300):
        self._store = credentials_store
        self._refresh_margin = refresh_margin_seconds
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, project_id: str) -> asyncio.Lock:
        return self._locks.setdefault(project_id, asyncio.Lock())

    async def get_valid_credentials(self, project_id: str) -> Credentials:
        async with self._lock_for(project_id):
            creds = await self._store.load(project_id)
            expires_in = (creds.expiry.timestamp() - time.time()) if creds.expiry else 0
            
            if creds.valid and expires_in > self._refresh_margin:
                return creds
                
            if not creds.refresh_token:
                raise GmailAuthError(
                    f"No refresh token on file for project {project_id}; re-auth required."
                )
                
            try:
                # Refresh is a synchronous network call, wrap it in a thread
                await asyncio.to_thread(creds.refresh, GoogleAuthRequest())
            except Exception as exc:
                raise GmailAuthError(
                    f"Refresh failed for project {project_id}: {exc}"
                ) from exc
                
            await self._store.save(project_id, creds)
            return creds

        