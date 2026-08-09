import asyncio

from app.connectors.gmail import (
    build_default_gmail_connector,
)


async def main():

    gmail = build_default_gmail_connector()

    emails = await gmail.search(
        query="",
        top_k=20,
    )

    print("=" * 60)
    print("GMAIL CLASSIFY")
    print("=" * 60)

    results = gmail.classify_emails(
        emails
    )

    for email in results:

        print(
            f'{email["classification"]:12} '
            f'({email["classification_confidence"]:6}) '
            f'→ {email["subject"]}'
        )


if __name__ == "__main__":
    asyncio.run(main())