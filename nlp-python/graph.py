import os
import json
from typing import TypedDict, Annotated, List, Union, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.output_parsers import JsonOutputParser

# Import shared LLM provider
from llm_provider import llm

# Define State
class LegalState(TypedDict):
    # Valid messages from the conversation history
    messages: Annotated[List[BaseMessage], add_messages]
    thread_id: str
    user_language: str
    legal_facts: Dict[str, Any]
    intent: str
    readiness_score: int
    missing_fields: List[str]
    next_step: str # "ask_question" or "generate_document"
    generated_content: str # question or document text

# Node: Detect Language
def detect_language_node(state: LegalState):
    messages = state["messages"]
    if not messages:
        return {"user_language": "en"}
    
    last_message = messages[-1].content
    
    prompt = f"""
    You are a language detection system.
    Detect the ISO 639-1 language code of the following text (e.g., 'en', 'ta', 'hi', 'es').
    Return ONLY the 2-letter code. Nothing else.
    
    Text: "{last_message}"
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    lang_code = response.content.strip().lower()
    
    # Validation/Cleanup
    if len(lang_code) > 2:
        lang_code = lang_code[:2]
        
    return {"user_language": lang_code}

# Node: Analyze Legal Context
def analyze_legal_context_node(state: LegalState):
    messages = state["messages"]
    current_facts = state.get("legal_facts", {})
    
    conversation_history = "\n".join([f"{m.type}: {m.content}" for m in messages])
    
    analysis_prompt = f"""
    You are an expert AI Legal Assistant 'Satta Vizhi'.
    
    [TASK]
    Analyze the conversation history.
    1. Extract new legal facts and merge with [CURRENT FACTS].
    2. Identify the legal intent (e.g., 'Divorce', 'Property Dispute', 'Consumer Complaint').
    3. Identify MISSING essential information required to draft a legal notice/complaint.
    4. Calculate 'readiness_score' (0-100) based on completeness.
    5. Determine 'next_step':
       - "generate_document" if readiness_score >= 80.
       - "ask_question" otherwise.
    
    [CURRENT FACTS]
    {json.dumps(current_facts)}
    
    [CONVERSATION HISTORY]
    {conversation_history}
    
    [OUTPUT FORMAT]
    Return a VALID JSON object (no markdown, no preamble):
    {{
        "legal_facts": {{ "key": "value" }},
        "intent": "string",
        "missing_fields": ["field1", "field2"],
        "readiness_score": integer,
        "next_step": "ask_question" OR "generate_document"
    }}
    """
    
    response = llm.invoke([
        SystemMessage(content="You are a legal reasoning engine. Output valid JSON only."),
        HumanMessage(content=analysis_prompt)
    ])
    
    try:
        content = response.content
        # Groq/Llama3 sometimes wraps in ```json ... ```
        if "```" in content:
            content = content.replace("```json", "").replace("```", "")
        
        analysis = json.loads(content.strip())
        
        return {
            "legal_facts": analysis.get("legal_facts", {}),
            "intent": analysis.get("intent", "Unknown"),
            "missing_fields": analysis.get("missing_fields", []),
            "readiness_score": analysis.get("readiness_score", 0),
            "next_step": analysis.get("next_step", "ask_question")
        }
    except Exception as e:
        print(f"Error parsing analysis: {e}, Response: {response.content}")
        # Fallback to keep conversation alive
        return {
            "next_step": "ask_question",
            "readiness_score": 0
        }

# Node: Generate Question
def generate_question_node(state: LegalState):
    lang = state.get("user_language", "en")
    facts = state.get("legal_facts", {})
    missing = state.get("missing_fields", [])
    intent = state.get("intent", "General Legal Issue")
    
    prompt = f"""
    You are a compassionate legal assistant.
    User Language: {lang}
    Intent: {intent}
    Missing Info: {missing}
    
    Task: Generate ONE clear, polite follow-up question to ask the user, to collect the most critical missing info.
    Important: The question MUST be in the '{lang}' language.
    Return ONLY the question text.
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    question = response.content.strip()
    
    # Remove quotes if model adds them
    question = question.strip('"')
    
    return {"generated_content": question}

# Node: Generate Document
def generate_document_node(state: LegalState):
    facts = state.get("legal_facts", {})
    intent = state.get("intent", "Legal Document")
    score = state.get("readiness_score", 0)
    
    prompt = f"""
    Generate a formal legal draft/document (in English).
    Intent: {intent}
    Facts: {json.dumps(facts)}
    
    Header: "Readiness Score: {score}/100"
    
    If score < 100, include a disclaimer about missing details.
    Format as a proper legal document.
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    document = response.content.strip()
    
    return {"generated_content": document}

# Define the Graph
workflow = StateGraph(LegalState)

workflow.add_node("detect_language", detect_language_node)
workflow.add_node("analyze_legal_context", analyze_legal_context_node)
workflow.add_node("generate_question", generate_question_node)
workflow.add_node("generate_document", generate_document_node)

workflow.set_entry_point("detect_language")
workflow.add_edge("detect_language", "analyze_legal_context")

def check_next_step(state: LegalState):
    return state["next_step"]

workflow.add_conditional_edges(
    "analyze_legal_context",
    check_next_step,
    {
        "ask_question": "generate_question",
        "generate_document": "generate_document"
    }
)

workflow.add_edge("generate_question", END)
workflow.add_edge("generate_document", END)

# Persistence using Postgres
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

# ENV variables must be loaded
# The Java app uses jdbc:postgresql://... but Python needs postgresql://...
raw_db_url = os.getenv("DB_URL", "postgresql://postgres:1234@localhost:5432/legal_db")
if raw_db_url.startswith("jdbc:"):
    DB_URL = raw_db_url.replace("jdbc:", "", 1)
else:
    DB_URL = raw_db_url

# Connection Pool
# We need to run setup() with autocommit=True because it uses CREATE INDEX CONCURRENTLY
try:
    with ConnectionPool(conninfo=DB_URL, min_size=1, max_size=1, kwargs={"autocommit": True}) as setup_pool:
        temp_saver = PostgresSaver(setup_pool)
        temp_saver.setup()
except Exception as e:
    print(f"Persistence Setup Warning: {e}")

# Runtime Pool (standard transaction management)
pool = ConnectionPool(conninfo=DB_URL, max_size=20)
memory = PostgresSaver(pool)

app = workflow.compile(checkpointer=memory)

def process_message(thread_id: str, user_input: str):
    """
    Entry point for the API.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    # Run the graph
    app.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config
    )
    
    # Get the final state
    final_state = app.get_state(config).values
    
    generated_content = final_state.get("generated_content", "")
    facts = final_state.get("legal_facts", {})
    intent = final_state.get("intent", "")
    score = final_state.get("readiness_score", 0)
    
    return {
        "content": generated_content,
        "entities": facts,
        "intent": intent,
        "readiness_score": score,
        "is_document": final_state.get("next_step") == "generate_document"
    }
