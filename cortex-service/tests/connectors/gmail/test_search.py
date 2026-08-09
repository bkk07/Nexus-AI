import asyncio

from app.connectors.gmail import (
    build_default_gmail_connector,
)


async def main():

    gmail = build_default_gmail_connector()

    results = await gmail.search(
        query="interview",
        top_k=5,
    )

    print()
    print("=" * 60)
    print("GMAIL SEARCH")
    print("=" * 60)

    print(
        "Results:",
        len(results)
    )

    for index, email in enumerate(
        results,
        start=1
    ):

        print()
        print("-" * 60)

        print(
            "Result:",
            index
        )

        print(
            "ID:",
            email["id"]
        )

        print(
            "Thread:",
            email["thread_id"]
        )

        print(
            "From:",
            email["from"]
        )

        print(
            "To:",
            email["to"]
        )

        print(
            "Subject:",
            email["subject"]
        )

        print(
            "Date:",
            email["date"]
        )

        print(
            "Snippet:",
            email["snippet"]
        )

        print(
            "Labels:",
            email["labels"]
        )


if __name__ == "__main__":
    asyncio.run(main())