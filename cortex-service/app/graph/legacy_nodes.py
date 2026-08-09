import asyncio
from typing import List,Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.llm.groq_client import get_fast_llm, get_reasoning_llm
from app.graph.state import AgentState, SubTask, EvidenceItem
from app.tools.registry import get_tool
from datetime import datetime
today = datetime.now().strftime("%A, %B %d, %Y")
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
    # 1. Primary Domain Tools (Check these first)
    "gmail_search": ["email", "emails", "inbox", "sent", "message", "mail"],
    "calendar_search": ["meeting", "deadline", "calendar", "schedule", "event"],
    "notion_search": ["notes", "notion", "task", "tasks", "wiki", "page"],
    "pdf_search": ["document", "pdf", "report", "spec", "file", "policy", "guide"],
    
    # 2. Date Tool (Specific temporal intent phrases)
    "date_tool": [
        "today's date",
        "current date",
        "current year",
        "what year",
        "what is today",
        "current time",
        "day of week",
        "what day is it",
    ],
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
    """Decomposes user query into focused search subtasks."""
    print("\n--- [NODE] Query Planner ---")
    question = state.get("question", "")
    llm = get_fast_llm()
    structured_llm = llm.with_structured_output(PlannerOutput)
    
    prompt = (
        "You are an enterprise search query planner.\n"
        "Decompose the user question into 1 to 2 concise retrieval subqueries targeting underlying data.\n\n"
        "RULES:\n"
        "1. Output ONLY search terms targeting documents or emails.\n"
        "2. NEVER generate action steps like 'summarize the results', 'analyze data', or 'format output'.\n"
        "3. Do NOT include meta-instructions like 'search Gmail for' or 'retrieve emails'.\n\n"
        f"User Question: {question}"
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

    try:
        llm = get_fast_llm().bind(response_format={"type": "json_object"})

        context_sample = "\n---\n".join([item.get("content", "")[:300] for item in ranked_evidence[:3]])
        
        prompt = (
            "You are an evidence relevance evaluator.\n"
            "Evaluate whether the retrieved documents contain information relevant to fulfilling the user request.\n\n"
            "IMPORTANT EVALUATION RULES:\n"
            "1. For open-ended or summary requests (e.g., 'summarize emails', 'check my inbox', 'latest messages'), "
            "grade 'YES' as long as the retrieved documents are emails/messages from the requested timeframe or source.\n"
            "2. Grade 'NO' ONLY if the retrieved documents are completely off-topic or empty.\n\n"
            f"User Question: {question}\n\n"
            f"Retrieved Context Sample:\n{context_sample}\n\n"
            'Respond ONLY with a JSON object: {"binary_score": "yes"} or {"binary_score": "no"}'
        )

        response = llm.invoke(prompt)
        import json
        data = json.loads(response.content)
        
        binary_score = data.get("binary_score", "yes").lower().strip()
        is_relevant = binary_score == "yes"
        print(f" -> Evidence Grade: '{binary_score.upper()}' | Relevancy: {is_relevant}")

    except Exception as e:
        print(f" -> [!] Evaluator parsing issue ({e}). Defaulting relevancy to True to continue flow.")
        is_relevant = True

    return {"is_relevant": is_relevant, "retry_count": retry_count + 1}

def query_rewriter_node(state: AgentState) -> dict:
    """Reformulates queries for secondary search attempts."""
    print("\n--- [NODE] Query Rewriter ---")
    question = state.get("question", "")
    retry_count = state.get("retry_count", 1)

    llm = get_fast_llm()
    prompt = (
        f"The initial search for the user request failed:\nRequest: '{question}'\n\n"
        "Generate a 2-4 word keyword query optimized for email search (e.g., 'recent emails', 'inbox updates').\n"
        "DO NOT write long sentences, lists of dates, or month names. Output ONLY the short query."
    )

    response = llm.invoke(prompt)
    rewritten_query = response.content.strip().replace('"', '')

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
        
    from datetime import datetime
    today = datetime.now().strftime("%A, %B %d, %Y")

    from datetime import datetime
    today = datetime.now().strftime("%A, %B %d, %Y")

    system_prompt = f"""
    You are an enterprise AI assistant. Today's date is {today}.

    Your job is to answer the user's question using the supplied context. 

    Rules:
    1. Base your answer on the provided context. If asked to summarize, provide a concise summary of the items in the context.
    2. Every factual statement or summary point must end with citations like [1] or [2].
    3. If the context contains absolutely no information related to the request, reply exactly:
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
    
    # Define a healthy UI preview length
    PREVIEW_LENGTH = 350 

    citations = []
    for idx, item in enumerate(ranked_evidence):
        full_content = item.get("content", "")
        
        # Take the first 350 characters and clean up any messy newlines for the UI
        snippet = full_content[:PREVIEW_LENGTH].strip()
        
        # If the original text is longer than our preview, add an ellipsis
        if len(full_content) > PREVIEW_LENGTH:
            snippet += "..."
            
        citations.append({
            "index": idx + 1, 
            "source": item.get("source", "Unknown"), 
            "snippet": snippet
        })
    
    print(" -> Answer generated successfully!")
    
    return {
        "generation": answer_text,
        "citations": citations,
        "messages": [AIMessage(content=answer_text)]
    }