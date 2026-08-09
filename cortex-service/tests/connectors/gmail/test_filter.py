import asyncio

from app.connectors.gmail import (
    build_default_gmail_connector,
)


async def main():

    gmail = build_default_gmail_connector()

    # ---------------------------------------------
    # Get input records using SEARCH
    # ---------------------------------------------

    emails = await gmail.search(
        query="",
        top_k=20,
    )

    print("=" * 60)
    print("GMAIL FILTER")
    print("=" * 60)

    print(
        "Input emails:",
        len(emails),
    )

    # ---------------------------------------------
    # Filter by subject
    # ---------------------------------------------

    microsoft = gmail.filter_emails(
        emails,
        field="subject",
        operator="contains",
        value="Microsoft",
    )

    print(
        "\nMicrosoft subject:",
        len(microsoft),
    )

    for email in microsoft:
        print(
            email["subject"]
        )

    # ---------------------------------------------
    # Filter unread
    # ---------------------------------------------

    unread = gmail.filter_emails(
        emails,
        field="labels",
        operator="contains",
        value="UNREAD",
    )

    print(
        "\nUnread:",
        len(unread),
    )

    # ---------------------------------------------
    # Filter by sender
    # ---------------------------------------------

    microsoft_sender = gmail.filter_emails(
        emails,
        field="from",
        operator="contains",
        value="microsoft",
    )

    print(
        "\nMicrosoft sender:",
        len(microsoft_sender),
    )

    # ---------------------------------------------
    # Exact subject
    # ---------------------------------------------

    exact = gmail.filter_emails(
        emails,
        field="subject",
        operator="equals",
        value="New jobs at Microsoft that match your profile",
    )

    print(
        "\nExact subject:",
        len(exact),
    )


if __name__ == "__main__":
    asyncio.run(main())