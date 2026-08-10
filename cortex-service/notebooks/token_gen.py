import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def main():
    credentials_file = "notebooks/credentials.json"

    if not os.path.exists(credentials_file):
        raise FileNotFoundError(
            f"{credentials_file} not found."
        )

    print("=" * 70)
    print("Google OAuth Authorization")
    print("=" * 70)

    print("\nRequested scopes:")
    for scope in SCOPES:
        print(" -", scope)

    # ---------------------------------------------------------
    # Create OAuth flow
    # ---------------------------------------------------------

    flow = InstalledAppFlow.from_client_secrets_file(
        credentials_file,
        SCOPES,
    )

    # ---------------------------------------------------------
    # Run OAuth authorization
    # ---------------------------------------------------------

    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        access_type="offline",
        prompt="consent",
        include_granted_scopes="false",
    )

    # ---------------------------------------------------------
    # Show granted scopes
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("AUTHORIZATION COMPLETE")
    print("=" * 70)

    granted_scopes = credentials.scopes or []

    print("\nGranted scopes:")

    for scope in granted_scopes:
        print(" -", scope)

    # ---------------------------------------------------------
    # Verify required permissions
    # ---------------------------------------------------------

    required_scopes = {
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar",
    }

    granted_scope_set = set(granted_scopes)

    missing_scopes = required_scopes - granted_scope_set

    if missing_scopes:
        print("\n❌ MISSING REQUIRED SCOPES:")

        for scope in missing_scopes:
            print(" -", scope)

        raise RuntimeError(
            "Google did not grant all required scopes."
        )

    print("\n✅ Gmail + Calendar permissions granted.")

    # ---------------------------------------------------------
    # Refresh token
    # ---------------------------------------------------------

    if not credentials.refresh_token:
        raise RuntimeError(
            "No refresh token was returned by Google."
        )

    print("\nRefresh token generated successfully.")

    # ---------------------------------------------------------
    # Save token locally
    # ---------------------------------------------------------

    token_data = {
        "refresh_token": credentials.refresh_token,
        "scopes": granted_scopes,
    }

    token_file = "notebooks/google_token.json"

    with open(
        token_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            token_data,
            file,
            indent=2,
        )

    print(f"\nToken saved to: {token_file}")

    print(
        "\n⚠️ Do NOT commit google_token.json "
        "or credentials.json."
    )


if __name__ == "__main__":
    main()