from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from assistant.orchestrator import CalendarOrchestrator, SUPPORTED_OPERATIONS


@dataclass
class Result:
    status: str = "feasible"
    message: str = "ok"
    candidates: list = None
    conflicts: list = None
    blocks: list = None
    ranked_slots: list = None

    def __post_init__(self):
        self.candidates = self.candidates or []
        self.conflicts = self.conflicts or []
        self.blocks = self.blocks or []
        self.ranked_slots = self.ranked_slots or []


def build(executors, planner):
    return CalendarOrchestrator(
        planner=planner,
        executors=executors,
        explainer=lambda result: result.message,
    )


def test_free_time_dialogue_uses_engine_result():
    calls = []
    executors = {
        operation: lambda **kwargs: Result()
        for operation in SUPPORTED_OPERATIONS
    }
    executors["FIND_FREE_SLOTS"] = lambda **kwargs: (
        calls.append(kwargs) or Result(
            message="Actual free slot: 18:00 -> 20:00."
        )
    )

    planner = lambda question: SimpleNamespace(
        operation="FIND_FREE_SLOTS",
        parameters={"date": "tomorrow"},
    )

    assistant = build(executors, planner)
    answer = assistant.ask("Is there any free time tomorrow?")

    assert answer == "Actual free slot: 18:00 -> 20:00."
    assert calls == [{"date": "tomorrow"}]


def test_study_request_returns_engine_candidates():
    slot = SimpleNamespace(start="18:00", end="20:00")
    executors = {
        operation: lambda **kwargs: Result()
        for operation in SUPPORTED_OPERATIONS
    }
    executors["FIND_BEST_SLOT"] = lambda **kwargs: Result(
        message="Candidate: 18:00 -> 20:00."
    )

    assistant = build(
        executors,
        lambda _: SimpleNamespace(
            operation="FIND_BEST_SLOT",
            parameters={"duration_minutes": 120},
        ),
    )

    assert assistant.ask("Can I study DSA for two hours tomorrow?") == (
        "Candidate: 18:00 -> 20:00."
    )


def test_delete_ambiguity_never_guesses():
    candidates = [
        SimpleNamespace(
            title="DSA Session",
            start="18:00",
            end="19:00",
        ),
        SimpleNamespace(
            title="DSA Session",
            start="20:00",
            end="21:00",
        ),
    ]
    executors = {
        operation: lambda **kwargs: Result()
        for operation in SUPPORTED_OPERATIONS
    }
    executors["DELETE"] = lambda **kwargs: Result(
        status="ambiguous",
        candidates=candidates,
    )

    assistant = build(
        executors,
        lambda _: SimpleNamespace(
            operation="DELETE",
            parameters={"query": "DSA Session"},
        ),
    )

    answer = assistant.ask("Delete my DSA session.")

    assert "multiple" in answer.lower()
    assert "18:00" in answer
    assert "20:00" in answer


def test_schedule_it_revalidates_previous_selection():
    selected_slot = SimpleNamespace(
        start="18:00",
        end="20:00",
    )
    calls = []

    executors = {
        operation: lambda **kwargs: Result()
        for operation in SUPPORTED_OPERATIONS
    }
    executors["CREATE"] = lambda **kwargs: (
        calls.append(kwargs["slot"]) or Result(
            status="created",
            message="Scheduled the selected slot.",
        )
    )

    assistant = build(
        executors,
        lambda _: None,
    )
    assistant.context.metadata["revalidate_slot"] = lambda slot: slot is selected_slot
    assistant.remember_proposal(selected_slot)

    answer = assistant.ask("Schedule it.")

    assert answer == "Scheduled the selected slot."
    assert calls == [selected_slot]
