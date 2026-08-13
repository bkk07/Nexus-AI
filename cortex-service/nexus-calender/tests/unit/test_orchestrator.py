from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import pytest

from assistant.orchestrator import (
    AMBIGUOUS_STATUSES,
    SUPPORTED_OPERATIONS,
    AssistantContext,
    CalendarOrchestrator,
)


@dataclass
class Outcome:
    status: str = "feasible"
    message: str = "done"
    candidates: list = None
    conflicts: list = None

    def __post_init__(self):
        self.candidates = self.candidates or []
        self.conflicts = self.conflicts or []


@pytest.fixture
def executors():
    calls = {}
    mapping = {}

    for operation in SUPPORTED_OPERATIONS:
        def handler(_operation=operation, **kwargs):
            calls[_operation] = kwargs
            return Outcome(message=f"{_operation} executed")
        mapping[operation] = handler

    def search_handler(_operation="SEARCH", **kwargs):
        calls[_operation] = kwargs
        return Outcome(status="found", message="Search completed.")
    mapping["SEARCH"] = search_handler
    return mapping, calls


def test_supported_operations_are_unique_and_25_plus():
    assert len(SUPPORTED_OPERATIONS) >= 25
    assert len(SUPPORTED_OPERATIONS) == len(set(SUPPORTED_OPERATIONS))


def test_router_dispatches_every_supported_operation(executors):
    mapping, calls = executors
    orchestrator = CalendarOrchestrator(
        planner=lambda _: None,
        executors=mapping,
    )

    for operation in SUPPORTED_OPERATIONS:
        result = orchestrator.route(
            operation,
            {"marker": operation},
        )
        assert result.operation == operation
        assert calls[operation]["marker"] == operation


def test_unknown_operation_is_rejected(executors):
    orchestrator = CalendarOrchestrator(
        planner=lambda _: None,
        executors=executors[0],
    )
    with pytest.raises(ValueError):
        orchestrator.route("UNKNOWN")


def test_planner_result_is_routed_and_explained(executors):
    mapping, calls = executors
    orchestrator = CalendarOrchestrator(
        planner=lambda _: SimpleNamespace(
            operation="SEARCH",
            parameters={"query": "DSA"},
        ),
        executors=mapping,
    )

    answer = orchestrator.ask("Show my DSA events")

    assert answer == "Search completed."
    assert calls["SEARCH"]["query"] == "DSA"


def test_ambiguous_outcome_always_asks_for_clarification():
    candidate_a = SimpleNamespace(
        title="DSA",
        start="18:00",
        end="19:00",
    )
    candidate_b = SimpleNamespace(
        title="DSA",
        start="20:00",
        end="21:00",
    )

    executors = {
        operation: (lambda **kwargs: Outcome())
        for operation in SUPPORTED_OPERATIONS
    }
    executors["FETCH"] = lambda **kwargs: Outcome(
        status="ambiguous",
        candidates=[candidate_a, candidate_b],
    )

    orchestrator = CalendarOrchestrator(
        planner=lambda _: SimpleNamespace(
            operation="FETCH",
            parameters={},
        ),
        executors=executors,
    )

    answer = orchestrator.ask("Fetch my DSA session")

    assert "multiple" in answer.lower()
    assert "DSA" in answer
    assert "18:00" in answer
    assert "20:00" in answer


def test_not_found_does_not_guess_replacement():
    executors = {
        operation: (lambda **kwargs: Outcome())
        for operation in SUPPORTED_OPERATIONS
    }
    executors["FETCH"] = lambda **kwargs: Outcome(
        status="not_found",
        message="The DSA event was not found.",
    )

    orchestrator = CalendarOrchestrator(
        planner=lambda _: SimpleNamespace(
            operation="FETCH",
            parameters={},
        ),
        executors=executors,
    )

    answer = orchestrator.ask("Find my DSA event")

    assert answer == "The DSA event was not found."
    assert "available" not in answer.lower()


def test_conflict_blocked_uses_only_real_conflicts():
    conflict = SimpleNamespace(
        title="Existing Meeting",
        start="18:00",
        end="19:00",
    )
    executors = {
        operation: (lambda **kwargs: Outcome())
        for operation in SUPPORTED_OPERATIONS
    }
    executors["UPDATE"] = lambda **kwargs: Outcome(
        status="conflict_blocked",
        conflicts=[conflict],
    )

    orchestrator = CalendarOrchestrator(
        planner=lambda _: SimpleNamespace(
            operation="UPDATE",
            parameters={},
        ),
        executors=executors,
    )

    answer = orchestrator.ask("Move it")

    assert "Existing Meeting" in answer
    assert "18:00" in answer


def test_schedule_it_uses_exact_previous_slot_and_revalidates():
    calls = []
    slot = SimpleNamespace(
        start="2026-08-14T18:00:00+05:30",
        end="2026-08-14T20:00:00+05:30",
    )
    executors = {
        operation: (lambda **kwargs: Outcome())
        for operation in SUPPORTED_OPERATIONS
    }

    def create(**kwargs):
        calls.append(kwargs["slot"])
        return Outcome(
            status="created",
            message="Created the selected slot.",
        )

    executors["CREATE"] = create

    context = AssistantContext()
    orchestrator = CalendarOrchestrator(
        planner=lambda _: None,
        executors=executors,
        context=context,
    )

    revalidated = []
    context.metadata["revalidate_slot"] = lambda candidate: (
        revalidated.append(candidate) or True
    )

    orchestrator.remember_proposal(slot)
    answer = orchestrator.ask("Schedule it.")

    assert answer == "Created the selected slot."
    assert calls == [slot]
    assert revalidated == [slot]
    assert context.pending_confirmation is False


def test_schedule_it_does_not_create_when_revalidation_fails():
    calls = []
    slot = SimpleNamespace(start="18:00", end="20:00")
    executors = {
        operation: (lambda **kwargs: Outcome())
        for operation in SUPPORTED_OPERATIONS
    }
    executors["CREATE"] = lambda **kwargs: calls.append(kwargs) or Outcome(
        status="created",
        message="created",
    )

    context = AssistantContext()
    context.metadata["revalidate_slot"] = lambda _: False
    orchestrator = CalendarOrchestrator(
        planner=lambda _: None,
        executors=executors,
        context=context,
    )
    orchestrator.remember_proposal(slot)

    answer = orchestrator.ask("Schedule it")

    assert "no longer available" in answer
    assert calls == []


def test_engine_error_becomes_plain_language_failure():
    executors = {
        operation: (lambda **kwargs: Outcome())
        for operation in SUPPORTED_OPERATIONS
    }

    def failing(**kwargs):
        raise RuntimeError("calendar connector unavailable")

    executors["SEARCH"] = failing

    orchestrator = CalendarOrchestrator(
        planner=lambda _: SimpleNamespace(
            operation="SEARCH",
            parameters={},
        ),
        executors=executors,
    )

    answer = orchestrator.ask("What do I have tomorrow?")

    assert "couldn't" in answer.lower()
    assert "calendar connector unavailable" in answer
    assert "done" not in answer.lower()


def test_explainer_receives_structured_result_without_orchestrator_mutation():
    seen = []
    result = Outcome(message="actual result")
    executors = {
        operation: (lambda **kwargs: result)
        for operation in SUPPORTED_OPERATIONS
    }

    def explainer(value):
        seen.append(value)
        return value.message

    orchestrator = CalendarOrchestrator(
        planner=lambda _: SimpleNamespace(
            operation="SEARCH",
            parameters={},
        ),
        executors=executors,
        explainer=explainer,
    )

    assert orchestrator.ask("events?") == "actual result"
    assert seen == [result]
