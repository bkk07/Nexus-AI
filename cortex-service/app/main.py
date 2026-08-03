import sys
from app.graph.workflow import rag_app


def run_pipeline(question: str):
    print(f"\n================ USER QUESTION ================")
    print(f"{question}\n")

    initial_state = {
        "question": question,
        "retry_count": 0,
    }

    # Execute the LangGraph workflow synchronously
    final_state = rag_app.invoke(initial_state)

    print("\n================ DETECTED INTENT ================")
    print(final_state.get("intent", "N/A"))

    if final_state.get("subtasks"):
        print("\n================ GENERATED SUBTASKS ================")
        for subtask in final_state["subtasks"]:
            print(f"- [Task {subtask['id']}] {subtask['description']}")

    print("\n================ FINAL ANSWER ================")
    print(final_state.get("generation", "No answer generated."))

    if final_state.get("citations"):
        print("\n================ CITATIONS ================")
        for cit in final_state["citations"]:
            print(f"[{cit['index']}] Source: {cit['source']}")
            print(f"    Snippet: {cit['snippet']}...\n")


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "What are the Employee Benefits & Workplace Policy Guide (2026)?"
    run_pipeline(query)