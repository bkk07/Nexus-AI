import asyncio

from app.connectors.gmail import (
    build_default_gmail_connector,
)


async def main():

    gmail = build_default_gmail_connector()

    message_id = "19fe5495c1acaf80"

    result = await gmail.fetch(
        message_id
    )

    print("=" * 60)
    print("GMAIL FETCH")
    print("=" * 60)

    print("ID:", result["id"])
    print("Thread:", result["thread_id"])
    print("From:", result["from"])
    print("To:", result["to"])
    print("Subject:", result["subject"])
    print("Date:", result["date"])
    print("Labels:", result["labels"])
    print("Body Type:", result["body_type"])
    print("Depth:", result["depth"])

    print("\nBODY:")
    print(result["body"][:3000])


if __name__ == "__main__":
    asyncio.run(main())