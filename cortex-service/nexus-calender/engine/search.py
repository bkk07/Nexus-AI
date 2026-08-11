from __future__ import annotations

from datetime import datetime

from compiler import CalendarQueryCompiler
from datetime_utils import DateTimeNormalizer
from models import CalendarOperation, CalendarRequest, EventSummary

from connector.calendar_client import CalendarClient


class CalendarSearchEngine:
    """
    Complete SEARCH pipeline:

        CalendarRequest
              ↓
        Date normalization
              ↓
        Query compilation
              ↓
        CalendarClient.search()
              ↓
        EventSummary[]

    No new search algorithm is introduced here.
    This class only orchestrates the existing phases.
    """

    def __init__(
        self,
        client: CalendarClient,
        compiler: CalendarQueryCompiler | None = None,
    ) -> None:

        self.client = client

        self.compiler = (
            compiler
            or CalendarQueryCompiler()
        )

    def search_events(
        self,
        request: CalendarRequest,
        *,
        reference: datetime,
    ) -> list[EventSummary]:

        if request.operation != CalendarOperation.SEARCH:
            raise ValueError(
                "CalendarSearchEngine only supports SEARCH."
            )

        query = self.compiler.compile_search(
            request,
            reference=reference,
        )

        return self.client.search(
            query
        )