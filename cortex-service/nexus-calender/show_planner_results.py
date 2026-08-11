from planner import SearchPlanner


QUESTIONS = [
    # "Show my Nexus AI events tomorrow",
    # "What events do I have today?",
    # "Find my DSA events this week",
    # "Show my Nexus AI events tomorrow from 2 PM to 5 PM",
    # "Show my events tomorrow morning",
    # "Show my events today from 12 PM to 2 PM",
    # "Find my Nexus AI meetings",
    # "Show my events today from 12 AM to 2 AM",
    "Show me all DSA events in the last 7 days."
]


def main():
    planner = SearchPlanner()

    for index, question in enumerate(QUESTIONS, 1):
        print("\n" + "=" * 80)
        print(f"QUESTION {index}")
        print("=" * 80)

        print(f"User: {question}")

        result = planner.plan(question)

        print("\nGroq extracted:")
        print(f"  operation          = {result.operation.value}")
        print(f"  query              = {result.query!r}")
        print(f"  event_id           = {result.event_id!r}")
        print(f"  date               = {result.date!r}")
        print(f"  start_time         = {result.start_time!r}")
        print(f"  end_time           = {result.end_time!r}")
        print(f"  duration_minutes   = {result.duration_minutes!r}")
        print(f"  purpose            = {result.purpose!r}")
        print(f"  timezone            = {result.timezone!r}")


if __name__ == "__main__":
    main()