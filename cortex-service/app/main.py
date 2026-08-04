import uuid
import warnings
# Suppress HTTPS client unclosed socket warnings on CLI exit
warnings.filterwarnings("ignore", category=ResourceWarning)

from langchain_core.messages import HumanMessage
from app.graph.workflow import rag_app


def run_interactive_chat():
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    project_id = "proj_phoenix_001"
    config = {"configurable": {"thread_id": session_id}}

    print("================ CORTEX AI INTERACTIVE CHAT ================")
    print(f"Session Thread ID: {session_id}")
    print(f"Active Project Scope: {project_id}")
    print("Type 'exit', 'quit', or 'q' to end the session.\n")

    while True:
        try:
            user_input = input("\nYou > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting session. Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("\nEnding chat session. Goodbye!")
            break

        # Pass current turn into inputs (LangGraph add_messages reducer appends this)
        inputs = {
            "question": user_input,
            "project_id": project_id,
            "messages": [HumanMessage(content=user_input)]
        }

        # Execute workflow graph with checkpointer
        result = rag_app.invoke(inputs, config=config)

        print("\nAgent >")
        print(result.get("generation"))

        citations = result.get("citations", [])
        if citations:
            print("\nSources:")
            for c in citations:
                print(f"  [{c['index']}] {c['source']}")


if __name__ == "__main__":
    run_interactive_chat()