from app.core.execution_plan import ExecutionPlan
from app.core.operations import OperationType
from app.graph.nodes.operation_result_router import (
    route_after_operation_execution,
)


def test_search_routes_to_adapter():

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
        "operation_plan": plan,
    }

    result = route_after_operation_execution(
        state
    )

    assert (
        result
        == "operation_result_adapter_node"
    )


def test_count_routes_to_generator():

    plan = ExecutionPlan()

    plan.add_operation(
        OperationType.COUNT,
        "gmail",
        {
            "query": "is:unread",
        },
    )

    state = {
        "operation_plan": plan,
    }

    result = route_after_operation_execution(
        state
    )

    assert result == "generator_node"


def test_summarize_routes_to_generator():

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

    plan.add_operation(
        OperationType.SUMMARIZE,
        "llm",
        {
            "source": "previous_operation",
        },
        depends_on=1,
    )

    state = {
        "operation_plan": plan,
    }

    result = route_after_operation_execution(
        state
    )

    assert result == "generator_node"


def test_empty_plan_routes_to_generator():

    state = {
        "operation_plan": None,
    }

    result = route_after_operation_execution(
        state
    )

    assert result == "generator_node"