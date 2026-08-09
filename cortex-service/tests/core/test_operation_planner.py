from app.core.operation_planner import (
    OperationPlanResponse,
    PlannedOperation,
    generate_operation_plan,
)
from app.core.operations import OperationType


def test_unread_count_plan(monkeypatch):

    class FakeStructuredLLM:

        def invoke(self, prompt):

            return OperationPlanResponse(
                operations=[
                    PlannedOperation(
                        operation=OperationType.COUNT,
                        connector="gmail",
                        parameters={
                            "query": "is:unread"
                        },
                    )
                ]
            )

    class FakeLLM:

        def with_structured_output(self, model):
            return FakeStructuredLLM()

    monkeypatch.setattr(
        "app.core.operation_planner.get_fast_llm",
        lambda: FakeLLM(),
    )

    plan = generate_operation_plan(
        "How many unread emails do I have?"
    )

    operation = plan.operations[0]

    assert (
        operation.operation
        == OperationType.COUNT
    )

    assert operation.connector == "gmail"

    assert (
        operation.parameters["query"]
        == "is:unread"
    )