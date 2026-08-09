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
    print("GMAIL EXTRACT")
    print("=" * 60)

    for email in emails:

        extracted = gmail.extract_information(
            email,
            fields=[
                "emails",
                "urls",
                "phones",
            ],
        )

        if any(extracted.values()):

            print(
                "\nSubject:",
                email["subject"],
            )

            print(
                "Extracted:",
                extracted,
            )


if __name__ == "__main__":
    asyncio.run(main())