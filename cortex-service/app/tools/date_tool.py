from datetime import datetime
from typing import Any, Dict, List


class DateTool:
    """Returns real-time temporal context (current date, time, year, day)."""

    name: str = "date_tool"

    def execute(
        self, args: Dict[str, Any], project_id: str
    ) -> List[Dict[str, Any]]:
        now = datetime.now()

        formatted_date = (
            f"Today's Date: {now.strftime('%A, %B %d, %Y')}\n"
            f"ISO Date: {now.strftime('%Y-%m-%d')}\n"
            f"Current Time: {now.strftime('%I:%M %p')}\n"
            f"Current Year: {now.year}\n"
            f"Current Month: {now.strftime('%B')}\n"
            f"Day of Week: {now.strftime('%A')}"
        )

        print(
            f" -> [Tool: date_tool] Retrieved system timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return [
            {
                "content": formatted_date,
                "source": "System Clock",
                "score": 1.0,
                "metadata": {
                    "iso_date": now.strftime("%Y-%m-%d"),
                    "year": now.year,
                    "day": now.strftime("%A"),
                },
            }
        ]