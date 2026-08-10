from app.core.operation_planner import (
    GmailQueryConstraints,
    OperationPlanResponse,
    PlannedOperation,
    generate_operation_plan,
)
from app.core.operations import OperationType


def test_microsoft_today_plan(monkeypatch):

    class FakeStructuredLLM:

        def invoke(self, prompt):

            return OperationPlanResponse(
                operations=[
                    PlannedOperation(
                        operation=OperationType.COUNT,
                        connector="gmail",
                        parameters=GmailQueryConstraints(
                            sender="microsoft",
                            time_range="today",
                        ),
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
        "How many emails did I get from Microsoft today?"
    )

    operation = plan.operations[0]

    assert (
        operation.operation
        == OperationType.COUNT
    )

    assert operation.connector == "gmail"

    assert operation.parameters.sender == "microsoft"

    assert operation.parameters.time_range == "today"