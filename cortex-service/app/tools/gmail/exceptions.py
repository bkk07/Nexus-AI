"""Exception hierarchy for the Gmail Tool."""

from typing import Optional

class GmailToolError(Exception):
    """Base exception for all Gmail tool failures."""
    pass

class GmailAuthError(GmailToolError):
    """Token invalid, expired beyond refresh, or revoked by user."""
    pass

class GmailRateLimitError(GmailToolError):
    """429 or quota-exceeded; carries retry_after hint."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after

class GmailTransientError(GmailToolError):
    """5xx errors; safe to retry with backoff."""
    pass

class GmailQueryCompilationError(GmailToolError):
    """Compiler could not produce a valid query."""
    pass

class GmailPermanentError(GmailToolError):
    """4xx (excluding 401/403/429) — malformed request, not retryable."""
    pass