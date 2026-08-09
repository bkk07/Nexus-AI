from app.core.operations import OperationType
from app.graph.nodes.operation_classifier import (
    classify_operation,
)


def test_count():

    plan = classify_operation(
        "How many unread emails do I have?"
    )

    assert len(plan.operations) == 1

    assert (
        plan.operations[0].operation_type
        == OperationType.COUNT
    )

    assert (
        plan.operations[0].connector
        == "gmail"
    )


def test_search():

    plan = classify_operation(
        "Find my Microsoft emails"
    )

    assert len(plan.operations) == 1

    assert (
        plan.operations[0].operation_type
        == OperationType.SEARCH
    )


def test_aggregate():

    plan = classify_operation(
        "Who emailed me most this week?"
    )

    assert len(plan.operations) == 1

    assert (
        plan.operations[0].operation_type
        == OperationType.AGGREGATE
    )


def test_summarize():

    plan = classify_operation(
        "Summarize my latest Microsoft email"
    )

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

    assert (
        plan.operations[1].depends_on
        == 0
    )

    assert (
        plan.operations[2].depends_on
        == 1
    )


def test_extract():

    plan = classify_operation(
        "Extract the phone number from this email"
    )

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
        == OperationType.EXTRACT
    )


def test_classify():

    plan = classify_operation(
        "Classify my emails"
    )

    assert len(plan.operations) == 2

    assert (
        plan.operations[0].operation_type
        == OperationType.SEARCH
    )

    assert (
        plan.operations[1].operation_type
        == OperationType.CLASSIFY
    )