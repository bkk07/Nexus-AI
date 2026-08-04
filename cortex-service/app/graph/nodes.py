import asyncio
from typing import List,Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.llm.groq_client import get_fast_llm, get_reasoning_llm
from app.graph.state import AgentState, SubTask, EvidenceItem
from app.tools.registry import get_tool

# from app.prompts.intent_prompt import get_intent_prompt;


# ==========================================
# Pydantic Schemas for Structured Outputs
# ==========================================
class IntentClassification(BaseModel):
    intent: Literal["simple_qa", "retrieval_needed"] = Field(
        description=(
            "MUST be either 'simple_qa' or 'retrieval_needed'.\n"
            "- Use 'retrieval_needed' whenever the user asks to search, check, find, or retrieve information "
            "from external sources like emails, inbox, documents, policies, notion notes, or calendar schedules.\n"
            "- Use 'simple_qa' ONLY for greetings, chitchat, general knowledge, introducing oneself (e.g. 'My name is...'), "
            "or meta-questions about the ongoing conversation history."
        )
    )

class PlannerOutput(BaseModel):
    subtasks: List[str] = Field(
        description="A list of 1 to 3 distinct sub-queries or tasks required to answer the user's question completely."
    )


class RelevanceScore(BaseModel):
    binary_score: str = Field(
        description="Grade whether retrieved evidence is relevant to the user question. 'yes' or 'no'."
    )


# ==========================================
# Deterministic Tool Routing Map
# ==========================================

KEYWORD_MAP = {
    "gmail_search": ["email", "emails", "inbox", "sent", "message", "mail"],
    "notion_search": ["notes", "notion", "task", "tasks", "wiki", "page"],
    "calendar_search": ["meeting", "deadline", "calendar", "schedule", "event"],
    "pdf_search": ["document", "pdf", "report", "spec", "file", "policy", "guide"],
}


def rule_based_route(subtask_desc: str) -> str:
    """Fast deterministic rule matching for tool routing."""
    text = subtask_desc.lower()
    for tool_name, keywords in KEYWORD_MAP.items():
        if any(k in text for k in keywords):
            return tool_name
    return "pdf_search"  # Default fallback tool


# ==========================================
# Core Graph Nodes
# ==========================================

def intent_detection_node(state: AgentState) -> dict:
    """Classifies user query to determine if enterprise data retrieval is needed."""
    print("\n--- [NODE] Intent Detection ---")
    question = state.get("question", "")
    llm = get_fast_llm()
    structured_llm = llm.with_structured_output(IntentClassification)
    
    prompt = f"Analyze the following user query and classify its intent:\n\nQuery: {question}"
    result: IntentClassification = structured_llm.invoke(prompt)
    
    print(f"-> Classified Intent: '{result.intent}'")
    return {"intent": result.intent}


def simple_qa_node(state: AgentState) -> dict:
    """Handles conversational turns and chitchat using full thread memory."""
    print("\n--- [NODE] Simple QA ---")
    messages = state.get("messages", [])
    
    system_prompt = SystemMessage(
        content="You are a polite, helpful enterprise AI assistant. "
                "Respond concisely and utilize the previous conversation history when answering."
    )
    
    prompt_messages = [system_prompt] + messages

    llm = get_fast_llm()
    response = llm.invoke(prompt_messages)
    answer_text = response.content

    return {
        "generation": answer_text,
        "citations": [],
        "messages": [AIMessage(content=answer_text)]
    }


def planner_node(state: AgentState) -> dict:
    """Decomposes the user query into 1-3 targeted subtasks."""
    print("\n--- [NODE] Query Planner ---")
    question = state.get("question", "")
    llm = get_fast_llm()
    structured_llm = llm.with_structured_output(PlannerOutput)
    
    prompt = (
        "Decompose the following user question into 1 to 3 focused sub-queries for evidence retrieval:\n\n"
        f"Question: {question}"
    )
    result: PlannerOutput = structured_llm.invoke(prompt)
    
    subtasks: List[SubTask] = [
        {"id": idx + 1, "description": task}
        for idx, task in enumerate(result.subtasks)
    ]
    
    print(f"-> Generated {len(subtasks)} subtask(s):")
    for st in subtasks:
        print(f"   [{st['id']}] {st['description']}")
        
    return {"subtasks": subtasks}


def router_node(state: AgentState) -> dict:
    """Maps subtasks to specific tool integrations (PDF, Gmail, Notion, Calendar)."""
    print("\n--- [NODE] Tool Router ---")
    subtasks = state.get("subtasks") or []
    question = state.get("question", "")

    routed_tasks = []
    if not subtasks:
        tool_name = rule_based_route(question)
        routed_tasks.append({
            "subtask": question,
            "tool_name": tool_name,
            "tool_args": {"query": question}
        })
    else:
        for st in subtasks:
            desc = st.get("description", "")
            tool_name = rule_based_route(desc)
            print(f" -> Subtask [{st.get('id')}]: '{desc}' ==> Routed to: [{tool_name}]")
            routed_tasks.append({
                "subtask": desc,
                "tool_name": tool_name,
                "tool_args": {"query": desc}
            })

    return {"routed_tasks": routed_tasks}


async def execute_tools_node(state: AgentState) -> dict:
    """Executes routed tool calls concurrently across registered sources."""
    print("\n--- [NODE] Parallel Tool Executor ---")
    routed_tasks = state.get("routed_tasks") or []
    project_id = state.get("project_id", "default_project")

    async def _run_single_tool(task):
        tool_name = task["tool_name"]
        tool_args = task["tool_args"]
        try:
            tool = get_tool(tool_name)
            if asyncio.iscoroutinefunction(tool.execute):
                return await tool.execute(args=tool_args, project_id=project_id)
            else:
                return tool.execute(args=tool_args, project_id=project_id)
        except Exception as e:
            print(f"   [!] Tool '{tool_name}' failed gracefully: {e}")
            return []

    tool_results = await asyncio.gather(*[_run_single_tool(task) for task in routed_tasks])
    
    raw_evidence = []
    for result in tool_results:
        raw_evidence.extend(result)

    print(f" -> Total raw evidence items gathered concurrently: {len(raw_evidence)}")
    return {"raw_evidence": raw_evidence}


def collector_node(state: AgentState) -> dict:
    """Flattens raw evidence and normalizes raw scores to a standardized 0.0 - 1.0 range."""
    print("\n--- [NODE] Evidence Collector ---")
    raw_evidence = state.get("raw_evidence") or []
    
    if not raw_evidence:
        print(" -> No raw evidence collected.")
        return {"collected_evidence": []}

    scores = [float(item.get("score", 0.0)) for item in raw_evidence]
    max_score = max(scores) if scores else 1.0
    min_score = min(scores) if scores else 0.0
    score_range = max_score - min_score

    collected_evidence = []
    for item in raw_evidence:
        raw_score = float(item.get("score", 0.0))
        
        if score_range > 0:
            norm_score = (raw_score - min_score) / score_range
        else:
            norm_score = 0.8

        normalized_item = {
            **item,
            "normalized_score": round(norm_score, 4)
        }
        collected_evidence.append(normalized_item)

    print(f" -> Collected and normalized {len(collected_evidence)} evidence items.")
    return {"collected_evidence": collected_evidence}


def ranker_node(state: AgentState) -> dict:
    """Deduplicates and ranks normalized evidence chunks."""
    print("\n--- [NODE] Evidence Ranker ---")
    evidence_pool = state.get("collected_evidence") or state.get("raw_evidence") or []
    
    seen_contents = set()
    deduped_evidence: List[EvidenceItem] = []
    
    for item in evidence_pool:
        content = item.get("content", "")
        if content and content not in seen_contents:
            seen_contents.add(content)
            deduped_evidence.append(item)
            
    sorted_evidence = sorted(
        deduped_evidence, 
        key=lambda x: x.get("normalized_score", x.get("score", 0.0)), 
        reverse=True
    )
    top_ranked = sorted_evidence[:8]
    
    print(f" -> Deduplicated from {len(evidence_pool)} to {len(deduped_evidence)} items.")
    print(f" -> Retained top {len(top_ranked)} ranked chunk(s).")
    return {"ranked_evidence": top_ranked}


def evaluator_node(state: AgentState) -> dict:
    """Grades whether retrieved evidence is sufficient to answer the question."""
    print("\n--- [NODE] Relevance Evaluator ---")
    question = state.get("question", "")
    ranked_evidence = state.get("ranked_evidence", [])
    retry_count = state.get("retry_count") or 0

    if not ranked_evidence:
        print(" -> No evidence retrieved. Grading as 'no'.")
        return {"is_relevant": False, "retry_count": retry_count + 1}

    llm = get_fast_llm()
    structured_llm = llm.with_structured_output(RelevanceScore)

    context_sample = "\n---\n".join([item["content"] for item in ranked_evidence[:3]])
    prompt = (
        "You are an expert grader evaluating whether retrieved documents contain relevant information "
        "to answer a user question.\n\n"
        f"User Question: {question}\n\n"
        f"Retrieved Evidence Sample:\n{context_sample}\n\n"
        "Does the evidence contain information directly relevant to answering the question? "
        "Grade with 'yes' or 'no'."
    )

    result: RelevanceScore = structured_llm.invoke(prompt)
    is_relevant = result.binary_score.lower().strip() == "yes"

    print(f" -> Evidence Grade: '{result.binary_score.upper()}' | Relevancy: {is_relevant}")
    return {"is_relevant": is_relevant, "retry_count": retry_count + 1}


def query_rewriter_node(state: AgentState) -> dict:
    """Reformulates queries for secondary search attempts upon low relevance."""
    print("\n--- [NODE] Query Rewriter ---")
    question = state.get("question", "")
    retry_count = state.get("retry_count", 1)

    llm = get_fast_llm()
    prompt = (
        f"The initial retrieval attempt for the user question below failed to find relevant documents:\n"
        f"Question: '{question}'\n\n"
        "Rewrite this query to be more specific, search-optimized, and rich in domain keywords "
        "for vector database search. Output ONLY the rewritten query text."
    )

    response = llm.invoke(prompt)
    rewritten_query = response.content.strip()

    print(f" -> Rewrote Query (Attempt #{retry_count}): '{rewritten_query}'")
    
    new_subtasks: List[SubTask] = [{"id": 1, "description": rewritten_query}]
    return {"subtasks": new_subtasks}


def generator_node(state: AgentState) -> dict:
    """Generates cited final response grounded strictly in retrieved context."""
    print("\n--- [NODE] Answer Generator ---")
    question = state.get("question", "")
    ranked_evidence = state.get("ranked_evidence", [])
    llm = get_reasoning_llm()
    
    if not ranked_evidence:
        formatted_context = "No specific retrieved context available."
    else:
        context_blocks = []
        for idx, item in enumerate(ranked_evidence, start=1):
            source = item.get("source", "Unknown")
            content = item.get("content", "")
            context_blocks.append(f"[{idx}] (Source: {source})\n{content}")
        formatted_context = "\n\n".join(context_blocks)
        
    system_prompt = f"""
    You are an enterprise RAG assistant.

    Your job is to answer the user's question ONLY using the supplied context.

    Rules:
    1. Never use outside knowledge.
    2. Never invent information.
    3. Never explain your reasoning.
    4. Never self-correct.
    5. Produce only the final answer.
    6. Every factual statement must end with citations like [1] or [2].
    7. If context is insufficient, reply exactly:
       "I don't have enough information in the provided documents."

    Context:
    -----------------------
    {formatted_context}
    -----------------------

    Question:
    {question}

    Final Answer:
    """
    
    print(" -> Invoking Groq Llama-3.3-70b...")
    response = llm.invoke(system_prompt)
    answer_text = response.content
    
    citations = [
        {"index": idx + 1, "source": item.get("source", "Unknown"), "snippet": item.get("content", "")[:150]}
        for idx, item in enumerate(ranked_evidence)
    ]
    
    print(" -> Answer generated successfully!")
    
    return {
        "generation": answer_text,
        "citations": citations,
        "messages": [AIMessage(content=answer_text)]
    }