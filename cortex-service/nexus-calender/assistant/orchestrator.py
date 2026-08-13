from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping


# Phase 25 deliberately uses strings here instead of extending the existing
# CalendarOperation enum. Earlier phases already use that enum as a public
# contract; changing it is unnecessary for the conversational layer.
SUPPORTED_OPERATIONS: tuple[str, ...] = (
    "SEARCH",
    "COUNT",
    "FETCH",
    "CHECK_AVAILABILITY",
    "FIND_FREE_SLOTS",
    "FIND_NEXT_FREE_SLOT",
    "FIND_BEST_SLOT",
    "CREATE",
    "UPDATE",
    "DELETE",
    "FIND_CONFLICTS",
    "ANALYZE_DAY",
    "ANALYZE_WEEK",
    "SCHEDULE_TASK",
    "SCHEDULE_TASKS",
    "FIND_FOCUS_TIME",
    "SCHEDULE_HABIT",
    "SCHEDULE_HABITS",
    "RESCHEDULE",
    "FIND_ALTERNATIVES",
    "MULTI_CONSTRAINT",
    "FIND_NEXT_AVAILABLE",
    "CHECK_BUFFERS",
    "CHECK_WINDOWS",
    "CHECK_PREFERENCES",
    "SCHEDULE_RECURRING_HABIT",
)


AMBIGUOUS_STATUSES = {
    "ambiguous",
    "not_found",
    "conflict_blocked",
}


@dataclass
class AssistantContext:
    """Conversation state needed by Phase 25.

    The exact structured result shown to the user is retained.  A later
    "Schedule it" therefore refers to the same concrete proposal rather than
    silently recomputing a new slot.
    """

    last_result: Any | None = None
    selected_slot: Any | None = None
    selected_event: Any | None = None
    pending_confirmation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def remember_slot(self, slot: Any) -> None:
        self.selected_slot = slot
        self.pending_confirmation = True

    def clear_confirmation(self) -> None:
        self.selected_slot = None
        self.pending_confirmation = False


@dataclass(frozen=True)
class RouteResult:
    operation: str
    result: Any


class OrchestratorError(RuntimeError):
    """Plain application-level failure from an orchestrator execution."""


class CalendarOrchestrator:
    """Conversational front end over already-tested Calendar engines.

    The orchestrator does not perform interval math and does not invent
    calendar facts.  Engines remain the source of truth.

    planner(question) -> structured plan
    executor(operation, parameters) -> typed engine outcome
    explainer(result) -> natural-language explanation

    All three are injectable so unit tests never require Groq or Google
    credentials.
    """

    def __init__(
        self,
        *,
        planner: Callable[[str], Any],
        executors: Mapping[str, Callable[..., Any]],
        explainer: Callable[[Any], str] | None = None,
        context: AssistantContext | None = None,
    ) -> None:
        self.planner = planner
        self.executors = dict(executors)
        self.explainer = explainer or self._default_explainer
        self.context = context or AssistantContext()

        missing = [
            operation
            for operation in SUPPORTED_OPERATIONS
            if operation not in self.executors
        ]
        if missing:
            raise ValueError(
                "Missing Phase 25 executor mappings: "
                + ", ".join(missing)
            )

    def route(
        self,
        operation: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> RouteResult:
        """Dispatch one structured operation to exactly one engine adapter."""

        normalized = str(operation).upper()

        if normalized not in SUPPORTED_OPERATIONS:
            raise ValueError(
                f"Unsupported Calendar operation: {operation}"
            )

        handler = self.executors[normalized]
        payload = dict(parameters or {})

        try:
            result = handler(**payload)
        except Exception as exc:
            raise OrchestratorError(
                f"Calendar operation {normalized} failed: {exc}"
            ) from exc

        self.context.last_result = result
        return RouteResult(
            operation=normalized,
            result=result,
        )

    def handle_plan(self, plan: Any) -> str:
        """Execute a planner result and explain only its typed outcome.

        A planner may return:
          * an object with ``operation`` and ``parameters``;
          * a mapping with those keys.
        """

        operation = self._value(plan, "operation")
        parameters = self._value(plan, "parameters", {})

        route = self.route(operation, parameters)
        result = route.result

        if self._status(result) in AMBIGUOUS_STATUSES:
            return self._clarification(result)

        return self.explainer(result)

    def ask(
        self,
        question: str,
    ) -> str:
        """Run one user turn through planner -> engine -> explanation."""

        if not question or not question.strip():
            raise ValueError("Question cannot be empty.")

        # "Schedule it" is intentionally resolved from conversation state,
        # not by asking the planner to invent/recompute a new slot.
        if self._is_confirmation(question):
            return self.confirm_selected_slot()

        try:
            plan = self.planner(question)
            return self.handle_plan(plan)
        except OrchestratorError as exc:
            return f"I couldn't complete that calendar operation: {exc}."
        except Exception as exc:
            return f"I couldn't process that calendar request: {exc}."

    def confirm_selected_slot(self) -> str:
        """Create a previously proposed slot only after revalidation.

        The CREATE executor receives the exact slot retained in context and
        must perform the existing Phase 12 duplicate/conflict safety checks.
        """

        if not self.context.pending_confirmation:
            return "I don't have a previously selected calendar slot to schedule."

        slot = self.context.selected_slot
        if slot is None:
            return "I don't have a concrete slot to schedule."

        validator = self.context.metadata.get("revalidate_slot")
        if validator is not None:
            try:
                validation = validator(slot)
            except Exception as exc:
                return (
                    "I couldn't re-check that slot before scheduling it: "
                    f"{exc}."
                )

            if not validation:
                return (
                    "That previously proposed slot is no longer available, "
                    "so I did not create the event."
                )

        creator = self.executors["CREATE"]

        try:
            result = creator(slot=slot)
        except Exception as exc:
            return f"I couldn't schedule that slot: {exc}."

        self.context.last_result = result
        status = self._status(result)

        if status in AMBIGUOUS_STATUSES or status == "conflict_blocked":
            return self._clarification(result)

        self.context.clear_confirmation()
        return self.explainer(result)

    def remember_proposal(self, slot: Any) -> None:
        self.context.remember_slot(slot)

    @staticmethod
    def _value(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, Mapping):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _status(result: Any) -> str | None:
        value = getattr(result, "status", None)
        if value is None and isinstance(result, Mapping):
            value = result.get("status")
        return str(value) if value is not None else None

    @staticmethod
    def _is_confirmation(question: str) -> bool:
        normalized = " ".join(question.lower().strip().rstrip(".!?").split())
        return normalized in {
            "schedule it",
            "schedule that",
            "book it",
            "create it",
        }

    @staticmethod
    def _clarification(result: Any) -> str:
        status = CalendarOrchestrator._status(result)

        if status == "ambiguous":
            candidates = getattr(result, "candidates", None) or []
            if not candidates and isinstance(result, Mapping):
                candidates = result.get("candidates", []) or []
            if candidates:
                details = "; ".join(
                    CalendarOrchestrator._describe_candidate(candidate)
                    for candidate in candidates
                )
                return (
                    "I found multiple matching calendar events. "
                    "Please tell me which one you mean: "
                    + details
                )
            return "I found multiple matching calendar events. Which one do you mean?"

        if status == "not_found":
            message = CalendarOrchestrator._message(result)
            return message or "I couldn't find the requested calendar event."

        if status == "conflict_blocked":
            conflicts = getattr(result, "conflicts", None) or []
            if not conflicts and isinstance(result, Mapping):
                conflicts = result.get("conflicts", []) or []
            details = "; ".join(
                CalendarOrchestrator._describe_candidate(item)
                for item in conflicts
            )
            if details:
                return (
                    "I couldn't make that calendar change because it conflicts "
                    "with: " + details
                )
            return "I couldn't make that calendar change because the requested time conflicts with another event."

        return CalendarOrchestrator._message(result) or (
            "I couldn't complete that calendar request."
        )

    @staticmethod
    def _message(result: Any) -> str | None:
        value = getattr(result, "message", None)
        if value is None and isinstance(result, Mapping):
            value = result.get("message")
        return value

    @staticmethod
    def _describe_candidate(candidate: Any) -> str:
        title = getattr(candidate, "title", None)
        start = getattr(candidate, "start", None)
        end = getattr(candidate, "end", None)

        if isinstance(candidate, Mapping):
            title = candidate.get("title", title)
            start = candidate.get("start", start)
            end = candidate.get("end", end)

        if title is not None and start is not None and end is not None:
            return f"{title} ({start} -> {end})"
        return str(candidate)

    @staticmethod
    def _default_explainer(result: Any) -> str:
        message = CalendarOrchestrator._message(result)
        if message:
            return message
        return str(result)
