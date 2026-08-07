"""Operators and data classes for building Gmail API queries."""

from enum import Enum
from dataclasses import dataclass, field
from typing import List

class GmailOperator(str, Enum):
    AFTER = "after"
    BEFORE = "before"
    NEWER_THAN = "newer_than"
    OLDER_THAN = "older_than"
    FROM = "from"
    TO = "to"
    SUBJECT = "subject"
    IS = "is"
    HAS = "has"
    LABEL = "label"

@dataclass(frozen=True)
class GmailQueryFragment:
    operator: GmailOperator
    value: str
    confidence: float
    source_span: str 

@dataclass
class CompiledGmailQuery:
    fragments: List[GmailQueryFragment] = field(default_factory=list)
    raw_keywords: List[str] = field(default_factory=list)
    overall_confidence: float = 0.0

    def to_query_string(self) -> str:
        parts = [f"{f.operator.value}:{f.value}" for f in self.fragments]
        parts.extend(self.raw_keywords)
        return " ".join(parts)