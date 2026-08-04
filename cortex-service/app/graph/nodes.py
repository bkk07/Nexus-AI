from typing import List
from pydantic import BaseModel, Field

from app.llm.groq_client import get_fast_llm, get_reasoning_llm
from app.vectorstore.weaviate_store import get_vector_store
from app.graph.state import AgentState, SubTask, EvidenceItem

from app.vectorstore.weaviate_store import hybrid_search

# ==========================================
# Pydantic Schemas for Structured Outputs
# ==========================================

class IntentClassification(BaseModel):
    intent: str = Field(
        description="Classify query as 'simple_qa' (e.g. greetings, general questions) or 'retrieval_needed' (specific information or domain knowledge required)."
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
# Graph Nodes
# ==========================================

def intent_detection_node(state: AgentState) -> dict:
    """Classifies user query to determine if vector store retrieval is needed."""
    print("\n--- [NODE] Intent Detection ---")
    question = state.get("question", "")
    llm = get_fast_llm()
    structured_llm = llm.with_structured_output(IntentClassification)
    
    prompt = f"Analyze the following user query and classify its intent:\n\nQuery: {question}"
    result: IntentClassification = structured_llm.invoke(prompt)
    
    print(f"-> Classified Intent: '{result.intent}'")
    return {"intent": result.intent}


def planner_node(state: AgentState) -> dict:
    """Decomposes the user query into subtasks for targeted retrieval."""
    print("\n--- [NODE] Query Planner ---")
    question = state.get("question", "")
    llm = get_fast_llm()
    structured_llm = llm.with_structured_output(PlannerOutput)
    
    prompt = (
        "Decompose the following user question into 1 to 3 focused sub-queries for retrieving evidence:\n\n"
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

def retriever_node(state: AgentState) -> dict:
    """Retrieves relevant evidence chunks using Weaviate Hybrid Search (BM25 + Vector)."""
    print("\n--- [NODE] Vector Retriever (Hybrid Search) ---")
    subtasks = state.get("subtasks") or []
    question = state.get("question", "")

    queries = [task["description"] for task in subtasks] if subtasks else [question]
    raw_evidence = []

    for q in queries:
        print(f"-> Hybrid Searching Weaviate for query: '{q}'")
        # alpha=0.5 guarantees equal weight between BM25 keywords & BGE vector similarity
        results = hybrid_search(query_text=q, top_k=3, alpha=0.5)
        raw_evidence.extend(results)

    print(f"-> Retrieved {len(raw_evidence)} raw evidence chunk(s).")
    return {"raw_evidence": raw_evidence}


def ranker_node(state: AgentState) -> dict:
    """Deduplicates and sorts evidence collected from retriever calls."""
    print("\n--- [NODE] Evidence Ranker ---")
    raw_evidence = state.get("raw_evidence", [])
    
    # Deduplicate by text content
    seen_contents = set()
    deduped_evidence: List[EvidenceItem] = []
    
    for item in raw_evidence:
        if item["content"] not in seen_contents:
            seen_contents.add(item["content"])
            deduped_evidence.append(item)
            
    # Sort descending by score
    sorted_evidence = sorted(deduped_evidence, key=lambda x: x["score"], reverse=True)
    top_ranked = sorted_evidence[:8]
    
    print(f"-> Deduplicated from {len(raw_evidence)} to {len(deduped_evidence)} items.")
    print(f"-> Retained top {len(top_ranked)} ranked chunk(s).")
    return {"ranked_evidence": top_ranked}


def generator_node(state: AgentState) -> dict:
    """Generates the final answer using Groq Llama-3.3-70b with cited context."""
    print("\n--- [NODE] Answer Generator ---")
    question = state.get("question", "")
    ranked_evidence = state.get("ranked_evidence", [])
    llm = get_reasoning_llm()
    
    if not ranked_evidence:
        formatted_context = "No specific retrieved context available."
    else:
        context_blocks = []
        for idx, item in enumerate(ranked_evidence, start=1):
            context_blocks.append(f"[{idx}] (Source: {item['source']})\n{item['content']}")
        formatted_context = "\n\n".join(context_blocks)
        
    system_prompt = f"""
    You are an enterprise RAG assistant.

    Your job is to answer the user's question ONLY using the supplied context.

    Rules:

    1. Never use outside knowledge.
    2. Never invent information.
    3. Never explain your reasoning.
    4. Never self-correct.
    5. Never say things like:
    - "I apologize"
    - "Actually"
    - "I made a mistake"
    - "The correct source is..."
    6. Produce only the final answer.
    7. Every factual statement must end with one or more citations like [1] or [2].
    8. If the context does not contain enough information, reply exactly:
    "I don't have enough information in the provided documents."

    Context:
    -----------------------
    {formatted_context}
    -----------------------

    Question:
    {question}

    Final Answer:
    """
    
    print("-> Invoking Groq Llama-3.3-70b...")
    response = llm.invoke(system_prompt)
    
    citations = [
        {"index": idx + 1, "source": item["source"], "snippet": item["content"][:150]}
        for idx, item in enumerate(ranked_evidence)
    ]
    
    print("-> Answer generated successfully!")
    return {
        "generation": response.content,
        "citations": citations
    }


def simple_qa_node(state: AgentState) -> dict:
    """Handles conversational asides without vector search."""
    print("\n--- [NODE] Simple QA ---")
    question = state.get("question", "")
    llm = get_fast_llm()
    response = llm.invoke(f"Respond politely and concisely to the user: {question}")
    return {"generation": response.content, "citations": []}


# Add this import at the top of app/graph/nodes.py if not already present
from pydantic import BaseModel, Field

# ==========================================
# Reflection Schemas & Nodes
# ==========================================

class RelevanceScore(BaseModel):
    binary_score: str = Field(
        description="Grade whether retrieved evidence is relevant to the user question. 'yes' or 'no'."
    )

def evaluator_node(state: AgentState) -> dict:
    """Grades whether the top ranked evidence is relevant to the question."""
    print("\n--- [NODE] Relevance Evaluator ---")
    question = state.get("question", "")
    ranked_evidence = state.get("ranked_evidence", [])
    retry_count = state.get("retry_count") or 0

    if not ranked_evidence:
        print("-> No evidence retrieved. Grading as 'no'.")
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

    print(f"-> Evidence Grade: '{result.binary_score.upper()}' | Relevancy: {is_relevant}")
    return {"is_relevant": is_relevant, "retry_count": retry_count + 1}


def query_rewriter_node(state: AgentState) -> dict:
    """Reformulates the query to improve vector retrieval on second attempt."""
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

    print(f"-> Rewrote Query (Attempt #{retry_count}): '{rewritten_query}'")
    
    # Overwrite subtasks with the single optimized query
    new_subtasks: List[SubTask] = [{"id": 1, "description": rewritten_query}]
    return {"subtasks": new_subtasks}