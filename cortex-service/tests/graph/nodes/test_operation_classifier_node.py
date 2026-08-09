from app.graph.nodes.operation_classifier import (
    operation_classifier_node,
)
from app.core.operations import OperationType


def test_operation_classifier_node():

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

    assert (
        plan.operations[1].operation_type
        == OperationType.FETCH
    )

    assert (
        plan.operations[2].operation_type
        == OperationType.SUMMARIZE
    )

    assert result["operation_results"] == {}