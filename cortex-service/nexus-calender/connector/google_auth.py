from __future__ import annotations

import os

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

load_dotenv()

CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]


def get_google_calendar_credentials() -> Credentials:
    """
    Build Google OAuth credentials using an existing refresh token.

    No browser authentication is required.
    """

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

    missing = []

    if not client_id:
        missing.append("GOOGLE_CLIENT_ID")

    if not client_secret:
        missing.append("GOOGLE_CLIENT_SECRET")

    if not refresh_token:
        missing.append("GOOGLE_REFRESH_TOKEN")

    if missing:
        raise RuntimeError(
            "Missing Google OAuth environment variables: "
            + ", ".join(missing)
        )

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=CALENDAR_SCOPES,
    )

    credentials.refresh(Request())

    return credentials