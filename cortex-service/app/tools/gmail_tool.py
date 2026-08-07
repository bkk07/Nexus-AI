"""Gmail Search Tool with Clean Keyword Filtering."""

import re
from typing import Any, Dict, List
from app.tools.base import Tool
from app.tools.gmail.tools import gmail_search_emails


class GmailSearchTool(Tool):
    """Searches Gmail by translating natural language queries to Gmail API filters."""

    name: str = "gmail_search"

    def execute(
        self, args: Dict[str, Any], project_id: str = "default"
    ) -> List[Dict[str, Any]]:
        raw_query = args.get("query", "").lower()
        print(f" -> [Tool: gmail_search] Raw incoming query: '{raw_query}'")

        unread_only = "unread" in raw_query or "is:unread" in raw_query
        starred_only = "starred" in raw_query or "is:starred" in raw_query

        q_parts = []

        # 1. Parse Date Ranges
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", raw_query)
        if len(dates) >= 2:
            start_date = dates[0].replace("-", "/")
            end_date = dates[1].replace("-", "/")
            q_parts.append(f"after:{start_date} before:{end_date}")
        elif "last" in raw_query and "days" in raw_query:
            days_match = re.search(r"last\s+(\d+)\s+days?", raw_query)
            if days_match:
                q_parts.append(f"newer_than:{days_match.group(1)}d")
        elif "today" in raw_query or "newer_than" in raw_query:
            q_parts.append("newer_than:5d")  # Fallback to recent 5 days for summary requests

        # 2. Strip filler words, month names, and standalone digits
        clean_terms = re.sub(
            r'["\']|\b(search|gmail|for|emails|email|sent|received|between|summarize|summaries|summary|results|from|retrieve|including|the|and|last|days|inbox|january|february|march|april|may|june|july|august|september|october|november|december)\b',
            " ",
            raw_query,
            flags=re.IGNORECASE,
        )
        # Strip isolated YYYY-MM-DD dates and stray numbers
        clean_terms = re.sub(r"\d{4}-\d{2}-\d{2}", " ", clean_terms)
        clean_terms = re.sub(r"\b\d{1,2}\b", " ", clean_terms)
        clean_terms = " ".join(clean_terms.split())

        if clean_terms:
            q_parts.append(clean_terms)

        final_query = " ".join(q_parts).strip()
        print(
            f" -> [Tool: gmail_search] Validated Gmail API Query: '{final_query}' | unread_only={unread_only}"
        )

        try:
            raw_response = gmail_search_emails.invoke(
                {
                    "query": final_query if final_query else None,
                    "unread_only": unread_only,
                    "starred_only": starred_only,
                    "max_results": 5,
                }
            )
            emails = raw_response.get("emails", [])

            evidence_items: List[Dict[str, Any]] = []
            for email in emails:
                formatted_content = (
                    f"Subject: {email.get('subject', '(No Subject)')}\n"
                    f"From: {email.get('sender', '')}\n"
                    f"Date: {email.get('date', '')}\n\n"
                    f"Body:\n{email.get('body', email.get('snippet', ''))}"
                )

                evidence_items.append(
                    {
                        "content": formatted_content,
                        "source": f"Gmail (ID: {email.get('id')})",
                        "score": 0.90 if email.get("is_unread") else 0.70,
                        "metadata": email,
                    }
                )

            print(
                f" -> [Tool: gmail_search] Found {len(evidence_items)} matching email(s)."
            )
            return evidence_items

        except Exception as e:
            print(f" [!] GmailSearchTool execution error: {e}")
            return []