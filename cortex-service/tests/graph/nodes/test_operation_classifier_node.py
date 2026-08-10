from app.graph.nodes.operation_classifier import (
    operation_classifier_node,
)
from app.core.operations import OperationType
from app.core.operation_planner import (
    GmailQueryConstraints,
    OperationPlanResponse,
    PlannedOperation,
)
from datetime import date


def _freeze_gmail_date(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 8, 10)

    monkeypatch.setattr("app.core.gmail_query_compiler.date", FixedDate)


def _patch_planner(monkeypatch, operations):
    class FakeStructuredLLM:
        def invoke(self, prompt):
            return OperationPlanResponse(operations=operations)

    class FakeLLM:
        def with_structured_output(self, model):
            return FakeStructuredLLM()

    monkeypatch.setattr(
        "app.core.operation_planner.get_fast_llm",
        lambda: FakeLLM(),
    )


def test_operation_classifier_node(monkeypatch):

    _freeze_gmail_date(monkeypatch)
    _patch_planner(
        monkeypatch,
        [
            PlannedOperation(
                operation=OperationType.SEARCH,
                connector="gmail",
                parameters=GmailQueryConstraints(
                    sender="microsoft",
                    time_range="today",
                ),
            ),
            PlannedOperation(
                operation=OperationType.FETCH,
                connector="gmail",
                parameters={
                    "source": "previous_operation",
                },
                depends_on=0,
            ),
            PlannedOperation(
                operation=OperationType.SUMMARIZE,
                connector="llm",
                parameters={
                    "source": "previous_operation",
                },
                depends_on=1,
            ),
        ],
    )

    state = {
        "question": "Summarize my latest Microsoft email",
    }

    result = operation_classifier_node(state)

    plan = result["operation_plan"]

    assert plan is not None

    assert len(plan.operations) == 3

    assert (
        plan.operations[0].operation_type
        == OperationType.SEARCH
    )

    assert plan.operations[0].parameters["query"] == (
        "from:(microsoft) after:2026/08/10"
    )

    assert (
        plan.operations[1].operation_type
        == OperationType.FETCH
    )

    assert (
        plan.operations[2].operation_type
        == OperationType.SUMMARIZE
    )

    assert result["operation_results"] == {}