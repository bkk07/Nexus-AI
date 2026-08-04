from langchain_core.messages import HumanMessage
from app.graph.workflow import rag_app


def run_chat_session():
    # Define a session thread ID
    config = {"configurable": {"thread_id": "session_tenant_001"}}

    # --- TURN 1 ---
    q1 = "What is our PTO rollover policy?"
    print(f"\n================ USER TURN 1: '{q1}' ================")
    
    inputs_1 = {
        "question": q1,
        "messages": [HumanMessage(content=q1)]
    }
    
    result_1 = rag_app.invoke(inputs_1, config=config)
    print("\n================ ANSWER 1 ================")
    print(result_1.get("generation"))


    # --- TURN 2 (Follow-up requiring memory) ---
    q2 = "How many total sick days do we get per year alongside that?"
    print(f"\n================ USER TURN 2: '{q2}' ================")
    
    inputs_2 = {
        "question": q2,
        "messages": [HumanMessage(content=q2)]
    }
    
    result_2 = rag_app.invoke(inputs_2, config=config)
    print("\n================ ANSWER 2 ================")
    print(result_2.get("generation"))


if __name__ == "__main__":
    run_chat_session()