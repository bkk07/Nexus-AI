"""Deterministic rules for parsing Natural Language into Gmail Operators."""

import re
from datetime import datetime, timedelta
from typing import List
from .operators import GmailOperator, GmailQueryFragment

class RelativeWindowResolver:
    """Resolves phrases like 'last week', 'past 3 days', 'yesterday'."""
    
    def resolve(self, text: str, reference_datetime: datetime) -> List[GmailQueryFragment]:
        fragments: List[GmailQueryFragment] = []
        text_lower = text.lower()
        
        # Match 'past N days' or 'last N days'
        match_days = re.search(r"\b(?:past|last) (\d+) days?\b", text_lower)
        if match_days:
            n = int(match_days.group(1))
            fragments.append(GmailQueryFragment(
                operator=GmailOperator.NEWER_THAN,
                value=f"{n}d",
                confidence=0.95,
                source_span=match_days.group(0),
            ))
            return fragments
            
        # Match 'yesterday'
        if re.search(r"\byesterday\b", text_lower):
            start = reference_datetime - timedelta(days=1)
            fragments.append(GmailQueryFragment(
                operator=GmailOperator.AFTER,
                value=start.strftime("%Y/%m/%d"),
                confidence=0.95,
                source_span="yesterday",
            ))
            # Gmail before is exclusive, so before today
            fragments.append(GmailQueryFragment(
                operator=GmailOperator.BEFORE,
                value=reference_datetime.strftime("%Y/%m/%d"),
                confidence=0.95,
                source_span="yesterday",
            ))
            return fragments
            
        # Match 'last week'
        if re.search(r"\blast week\b", text_lower):
            week_start = reference_datetime - timedelta(days=reference_datetime.weekday() + 7)
            week_end = week_start + timedelta(days=7)
            fragments.append(GmailQueryFragment(
                operator=GmailOperator.AFTER, 
                value=week_start.strftime("%Y/%m/%d"),
                confidence=0.9, 
                source_span="last week",
            ))
            fragments.append(GmailQueryFragment(
                operator=GmailOperator.BEFORE, 
                value=week_end.strftime("%Y/%m/%d"),
                confidence=0.9, 
                source_span="last week",
            ))
            return fragments
            
        return fragments