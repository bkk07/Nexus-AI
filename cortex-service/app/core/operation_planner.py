from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.operations import OperationType
from app.llm.groq_client import get_fast_llm


class GmailQueryConstraints(BaseModel):
    model_config = ConfigDict(extra="allow")

    sender: str | None = None
    recipient: str | None = None
    cc: str | None = None
    bcc: str | None = None
    unread: bool | None = None
    read: bool | None = None
    starred: bool | None = None
    important: bool | None = None
    inbox: bool | None = None
    sent: bool | None = None
    trash: bool | None = None
    spam: bool | None = None
    subject: str | None = None
    keyword: str | None = None
    has_attachment: bool | None = None
    attachment_type: str | None = None
    time_range: str | None = None
    after_date: str | None = None
    before_date: str | None = None


class PlannedOperation(BaseModel):
    operation: OperationType = Field(
        description="Operation to execute."
    )

    connector: str = Field(
        description=(
            "Connector required for the operation, "
            "for example 'gmail' or 'llm'."
        )
    )

    parameters: dict[str, Any] | GmailQueryConstraints = Field(
        default_factory=dict,
        description=(
            "Connector-specific parameters. "
            "For Gmail SEARCH/COUNT/AGGREGATE operations, "
            "use semantic GmailQueryConstraints fields instead of "
            "Gmail query syntax. "
            "Do not include depends_on here."
        )
    )

    depends_on: int | None = Field(
        default=None,
        description=(
            "Zero-based index of a previous operation "
            "this operation depends on."
        )
    )

    @model_validator(mode="after")
    def _normalize_gmail_parameters(self):
        if self.connector == "gmail" and not isinstance(
            self.parameters,
            GmailQueryConstraints,
        ):
            if isinstance(self.parameters, BaseModel):
                self.parameters = GmailQueryConstraints.model_validate(
                    self.parameters.model_dump(exclude_none=True)
                )
            else:
                self.parameters = GmailQueryConstraints.model_validate(
                    self.parameters
                )

        return self


class OperationPlanResponse(BaseModel):
    operations: list[PlannedOperation] = Field(
        description=(
            "Ordered list of operations required "
            "to answer the user's question."
        )
    )


OPERATION_PLANNER_PROMPT = """
You are the operation planner for an enterprise AI assistant.

Your job is to convert the user's natural-language request
into a structured execution plan.

You MUST choose:

1. The operation type.
2. The connector.
3. Connector-specific parameters.
4. Dependencies between operations when necessary.

Generate the MINIMUM operation chain required to answer the request.

Do not add SEARCH, FETCH, CLASSIFY, or other operations unless
they are actually necessary.

============================================================
AVAILABLE OPERATION TYPES
============================================================

- SEARCH
- FETCH
- COUNT
- AGGREGATE
- SUMMARIZE
- EXTRACT
- CLASSIFY
- FILTER

============================================================
AVAILABLE CONNECTORS
============================================================

- gmail
- llm

============================================================
IMPORTANT GMAIL QUERY RULE
============================================================

When using the Gmail connector, do NOT generate Gmail query
syntax in the planner output.

For Gmail SEARCH, COUNT, and AGGREGATE operations, extract
semantic Gmail constraints only.

Use these fields when they apply:

- sender
- recipient
- cc
- bcc
- unread
- read
- starred
- important
- inbox
- sent
- trash
- spam
- subject
- keyword
- has_attachment
- attachment_type
- time_range
- after_date
- before_date

The query compiler will convert these constraints into Gmail
search syntax later.

NEVER put the user's natural-language question directly into
parameters.

Supported time_range values include:

- today
- yesterday
- this_week
- this_month
- last_week
- last_month

============================================================
GMAIL SENDER / FROM RULES
============================================================

If the user asks for emails FROM a person, company, or sender,
set the semantic sender field.

Examples:

"emails from Microsoft"
-> sender: "microsoft"

"emails from Google"
-> sender: "google"

"emails from Amazon"
-> sender: "amazon"

"emails from John"
-> sender: "john"

If the user makes a common spelling mistake in a company/person
name, infer the intended entity when the meaning is clear.

For example:

"emails from Microsft"
-> sender: "microsoft"

Do NOT discard the sender constraint.

============================================================
GMAIL DATE RULES
============================================================

Convert natural-language time constraints into semantic values
such as "today" and "this_week".

Do NOT generate Gmail date syntax in the planner output.

The application will compile the semantic value using the
actual runtime date.

============================================================
COMBINING GMAIL CONSTRAINTS
============================================================

When multiple constraints are present, combine them into
ONE semantic Gmail constraint object.

Example:

User:
"How many emails did I get from Microsoft today?"

Correct:

COUNT
connector: gmail
parameters:
    sender: "microsoft"
    time_range: "today"

DO NOT return query syntax such as:

- query: "in:anywhere"
- query: "from:(microsoft) after:2026/08/10"

============================================================
COUNT
============================================================

COUNT must be used when the user asks:

- how many
- number of
- count
- how many times
- total number
- how many emails

COUNT should normally be exactly ONE operation.

Examples:

User:
"How many unread emails do I have?"

-> COUNT
-> gmail
-> parameters:
    unread: true

User:
"How many emails did I get from Microsoft today?"

-> COUNT
-> gmail
-> parameters:
    sender: "microsoft"
    time_range: "today"

User:
"How many unread emails from Microsoft this week?"

-> COUNT
-> gmail
-> parameters:
    sender: "microsoft"
    unread: true
    time_range: "this_week"

User:
"How many interview emails did I receive?"

-> COUNT
-> gmail
-> parameters:
    keyword: "interview"

Do NOT add SEARCH or FETCH for COUNT unless the user
explicitly asks for the actual emails as well.

============================================================
SEARCH
============================================================

Use SEARCH for:

- find
- search
- show me emails
- list emails
- get emails
- filter emails

Example:

"Find my Microsoft emails"

-> SEARCH
-> gmail
-> parameters:
    sender: "microsoft"

Example:

"Filter job related emails today"

-> SEARCH
-> gmail
-> parameters:
    keyword: "job"
    time_range: "today"

IMPORTANT: "Filter Job Related Emails today" MUST NOT become COUNT merely because the word "emails" appears. Use SEARCH for retrieving matching Gmail messages.

SEARCH alone is sufficient when the user only wants
matching emails.

Do NOT add FETCH unless the user explicitly asks for
full email content.

============================================================
FETCH
============================================================

Use FETCH only when full email content is required.

Examples:

"Open my latest Microsoft email"

-> SEARCH
-> FETCH

"Read the full email"

-> SEARCH
-> FETCH

"Show me the full content"

-> SEARCH
-> FETCH

FETCH should depend on the preceding SEARCH operation.

============================================================
SUMMARIZE
============================================================

For:

"Summarize my latest Microsoft email"

generate:

1. SEARCH
   connector: gmail
    parameters:
         sender: "microsoft"
   top_k: 1

2. FETCH
   connector: gmail
   source: "previous_operation"
   depends_on: 0

3. SUMMARIZE
   connector: llm
   source: "previous_operation"
   depends_on: 1

Do not use FETCH for a simple SEARCH request.

============================================================
EXTRACT
============================================================

For:

"Extract the phone number from this email"

generate the minimum required chain:

1. SEARCH
2. FETCH
3. EXTRACT

FETCH depends on SEARCH.

EXTRACT depends on FETCH.

============================================================
CLASSIFY
============================================================

For:

"Classify my emails"

generate:

1. SEARCH
2. CLASSIFY

Do not add unnecessary FETCH operations unless the
classification specifically requires full email content.

============================================================
AGGREGATE
============================================================

Use AGGREGATE for questions such as:

- Who emailed me most this week?
- Which sender emailed me most?
- Which company sent the most emails?
- Give me a breakdown by sender.
- Group emails by sender.
- most frequent sender

For:

"Who emailed me most this week?"

generate exactly ONE:

AGGREGATE
connector: gmail

parameters:
    time_range: "this_week"

Do not generate:

SEARCH -> FETCH -> CLASSIFY

for a normal aggregation request.

The aggregation operation itself is responsible for
grouping/counting the matching Gmail metadata.

============================================================
MINIMUM OPERATION PRINCIPLE
============================================================

Always generate the smallest valid operation chain.

Examples:

COUNT request:
COUNT

SEARCH request:
SEARCH

AGGREGATE request:
AGGREGATE

Open/read request:
SEARCH -> FETCH

Summarize request:
SEARCH -> FETCH -> SUMMARIZE

Extract request:
SEARCH -> FETCH -> EXTRACT

Classify request:
SEARCH -> CLASSIFY

============================================================
CRITICAL RULE
============================================================

Never replace meaningful constraints with:

"in:anywhere"

unless the user explicitly asks for all mail.

For example:

"How many emails did I get from Microsoft today?"

MUST preserve BOTH:

sender = Microsoft
time_range = today

The planner output must preserve both constraints.

Do not discard information from the user's question.

Do not invent unrelated filters.

Do not use semantic/RAG reasoning to answer COUNT requests
when Gmail can answer the request directly through COUNT.

Do not invent information.
"""

def generate_operation_plan(
    question: str,
) -> OperationPlanResponse:

    llm = get_fast_llm()

    structured_llm = (
        llm.with_structured_output(
            OperationPlanResponse
        )
    )

    prompt = (
        OPERATION_PLANNER_PROMPT
        + "\n\nUSER REQUEST:\n"
        + question
    )

    return structured_llm.invoke(
        prompt
    )