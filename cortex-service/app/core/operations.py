from enum import Enum


class OperationType(str, Enum):
    """
    Operations that the Agent can perform.

    These are source-independent.
    Gmail, PDF, Notion, and Calendar can provide
    capabilities for these operations.
    """

    SEARCH = "SEARCH"
    FETCH = "FETCH"
    COUNT = "COUNT"
    AGGREGATE = "AGGREGATE"
    FILTER = "FILTER"
    CLASSIFY = "CLASSIFY"
    EXTRACT = "EXTRACT"
    SUMMARIZE = "SUMMARIZE"