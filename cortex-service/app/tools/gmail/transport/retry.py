"""Exponential backoff + jitter and HTTP error classification."""

import asyncio
import random
from googleapiclient.errors import HttpError
from ..exceptions import GmailRateLimitError, GmailTransientError, GmailPermanentError

def classify_http_error(exc: HttpError) -> Exception:
    status = exc.resp.status if exc.resp else None
    
    if status == 429:
        retry_after = exc.resp.get("retry-after") if exc.resp else None
        return GmailRateLimitError("Gmail API rate limit exceeded", retry_after=float(retry_after) if retry_after else None)
        
    if status in (500, 502, 503, 504):
        return GmailTransientError(f"Gmail API transient error: {status}")
        
    if status in (401, 403):
        return GmailTransientError(f"Gmail API auth-adjacent error: {status}") 
        
    return GmailPermanentError(f"Gmail API permanent error: {status}")

async def with_backoff(coro_factory, max_attempts: int = 5, base_delay: float = 0.5, max_delay: float = 20.0):
    """Executes coro_factory() with exponential backoff + full jitter."""
    last_exc = None
    
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except HttpError as http_exc:
            classified = classify_http_error(http_exc)
            last_exc = classified
            
            if isinstance(classified, GmailPermanentError):
                raise classified
                
            delay = getattr(classified, "retry_after", None) or min(max_delay, base_delay * (2 ** attempt))
            delay = random.uniform(0, delay)
            await asyncio.sleep(delay)
            
    raise last_exc