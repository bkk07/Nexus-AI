from app.core.operations import OperationType
from app.core.execution_plan import (
    ExecutionPlan,
)


def test_execution_plan():

    plan = ExecutionPlan()

    plan.add_operation(
        OperationType.SEARCH,
        "gmail",
        {
            "query": "from:microsoft",
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

    plan.add_operation(
        OperationType.SUMMARIZE,
        "llm",
        {
            "source": "previous_operation",
        },
        depends_on=1,
    )

    assert len(plan) == 3

    assert (
        plan.operations[0].operation_type
        == OperationType.SEARCH
    )

    assert (
        plan.operations[1].operation_type
        == OperationType.FETCH
    )

    assert (
        plan.operations[2].operation_type
        == OperationType.SUMMARIZE
    )

    assert (
        plan.operations[1].depends_on == 0
    )

    assert (
        plan.operations[2].depends_on == 1
    )