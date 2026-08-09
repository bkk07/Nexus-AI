import asyncio

from app.connectors.gmail import (
    build_default_gmail_connector,
)


async def main():

    gmail = build_default_gmail_connector()

    print("=" * 60)
    print("GMAIL COUNT")
    print("=" * 60)

    unread = await gmail.count(
        "is:unread"
    )

    print(
        "Unread emails:",
        unread
    )

    starred = await gmail.count(
        "is:starred"
    )

    print(
        "Starred emails:",
        starred
    )

    attachments = await gmail.count(
        "has:attachment"
    )

    print(
        "Emails with attachments:",
        attachments
    )

    interview = await gmail.count(
        "interview"
    )

    print(
        "Interview emails:",
        interview
    )
    
if __name__ == "__main__":
    asyncio.run(main())