import asyncio
import uuid
from langchain_core.messages import HumanMessage
from app.graph.workflow import rag_app


async def run_interactive_chat():
    """CLI test interface for the Cortex AI reasoning engine."""
    print("==================================================")
    print(" CORTEX AI SERVICE - Local Interactive Debugger ")
    print("==================================================")
    print("Type 'exit' or 'quit' to end the session.\n")

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    project_id = "demo_project_01"

    while True:
        try:
            user_input = input("\nYou > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                print("\nSession ended.")
                break

            # PASS HumanMessage TO UPDATE LANGGRAPH MESSAGE HISTORY PROPERLY
            inputs = {
                "question": user_input,
                "project_id": project_id,
                "messages": [HumanMessage(content=user_input)]
            }

            result = await rag_app.ainvoke(inputs, config=config)

            generation = result.get("generation", "No response generated.")
            citations = result.get("citations", [])

            print(f"\nAI > {generation}")

            if citations:
                print("\n[Citations]")
                for cite in citations:
                    print(f"  [{cite['index']}] Source: {cite['source']}")

        except (KeyboardInterrupt, EOFError):
            print("\nSession interrupted. Exiting.")
            break
        except Exception as e:
            print(f"\n[ERROR] An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(run_interactive_chat())