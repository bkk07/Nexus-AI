import pytest

from app.core.execution_plan import ExecutionPlan
from app.core.operations import OperationType
from app.graph.nodes import operation_executor as executor_module
from app.graph.nodes.operation_executor import (
    operation_executor_node,
)


class FakeGmailConnector:

    async def search(
        self,
        query="",
        top_k=10,
    ):
        return [
            {
                "id": "email-1",
                "subject": "Microsoft Interview",
                "snippet": "Interview invitation",
            }
        ]

    async def fetch(
        self,
        message_id,
    ):
        return {
            "id": message_id,
            "subject": "Microsoft Interview",
            "body": "Your interview is scheduled.",
        }

    async def count(
        self,
        query="",
    ):
        return 42

    def filter_emails(
        self,
        emails,
        field,
        operator,
        value,
    ):
        return [
            email
            for email in emails
            if value.lower()
            in email.get(field, "").lower()
        ]

    def classify_emails(
        self,
        emails,
    ):
        return [
            {
                **email,
                "classification": "interview",
            }
            for email in emails
        ]

    def extract_information(
        self,
        email,
        fields,
    ):
        return {
            field: []
            for field in fields
        }


@pytest.fixture
def fake_gmail(monkeypatch):

    fake = FakeGmailConnector()

    monkeypatch.setattr(
        executor_module,
        "build_default_gmail_connector",
        lambda: fake,
    )

    return fake


@pytest.mark.asyncio
async def test_search_execution(
    fake_gmail,
):

    plan = ExecutionPlan()

    plan.add_operation(
        OperationType.SEARCH,
        "gmail",
        {
            "query": "Microsoft",
            "top_k": 10,
        },
    )

    state = {
        "question": "Find Microsoft emails",
        "operation_plan": plan,
    }

    result = await operation_executor_node(
        state
    )

    assert "search" in result[
        "operation_results"
    ]

    assert (
        result["operation_results"]["search"][0]["id"]
        == "email-1"
    )


@pytest.mark.asyncio
async def test_count_execution(
    fake_gmail,
):

    plan = ExecutionPlan()

    plan.add_operation(
        OperationType.COUNT,
        "gmail",
        {
            "query": "is:unread",
        },
    )

    state = {
        "question": "How many unread emails?",
        "operation_plan": plan,
    }

    result = await operation_executor_node(
        state
    )

    assert (
        result["operation_results"]["count"]
        == 42
    )


@pytest.mark.asyncio
async def test_search_then_fetch(
    fake_gmail,
):

    plan = ExecutionPlan()

    plan.add_operation(
        OperationType.SEARCH,
        "gmail",
        {
            "query": "Microsoft",
            "top_k": 1,
        },
    )

    plan.add_operation(
        OperationType.FETCH,
        "gmail",
        {
            "source": "previous_operation",
        },
        depends_on=0,
    )

    state = {
        "question": "Fetch Microsoft email",
        "operation_plan": plan,
    }

    result = await operation_executor_node(
        state
    )

    fetched = result[
        "operation_results"
    ]["fetch"]

    assert len(fetched) == 1

    assert (
        fetched[0]["id"]
        == "email-1"
    )

    assert (
        fetched[0]["body"]
        == "Your interview is scheduled."
    )