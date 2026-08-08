"""Normalizes plaintext by collapsing quote chains and trimming signatures."""

import re

_QUOTE_HEADER_PATTERN = re.compile(r"^On .{5,60} wrote:$", re.MULTILINE)

_SIGNATURE_MARKERS = [
    re.compile(r"^--\s*$", re.MULTILINE),
    re.compile(r"^Sent from my (iPhone|iPad|Android|Galaxy)", re.MULTILINE),
    re.compile(r"^Get Outlook for (iOS|Android)", re.MULTILINE),
]

class ContentNormalizer:
    def __init__(self, max_chars: int = 4000, quote_depth_limit: int = 1):
        self.max_chars = max_chars
        self.quote_depth_limit = quote_depth_limit

    def normalize(self, text: str) -> str:
        text = self._collapse_quote_chains(text)
        text = self._trim_signature(text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        
        if len(text) > self.max_chars:
            text = text[: self.max_chars].rsplit("\n", 1)[0] + "\n[...truncated...]"
        return text

    def _collapse_quote_chains(self, text: str) -> str:
        match = _QUOTE_HEADER_PATTERN.search(text)
        if not match:
            return text
        # Keep content up to first quote header; drop nested reply history
        return text[: match.start()].rstrip()

    def _trim_signature(self, text: str) -> str:
        earliest_cut = len(text)
        for pattern in _SIGNATURE_MARKERS:
            m = pattern.search(text)
            if m:
                earliest_cut = min(earliest_cut, m.start())
        return text[:earliest_cut].rstrip()