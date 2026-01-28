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
    
    # Facts - Generic Classification
    legal_facts: Dict[str, Any]      # Merged facts (Backward compatibility + Storage)
    critical_facts: Dict[str, Any]   # Essential facts
    optional_facts: Dict[str, Any]   # Nice-to-have facts
    
    intent: str
    readiness_score: int
    missing_fields: List[str]        # Only critical missing fields
    
    next_step: str                   # "ask_question", "ask_confirmation", "generate_document"
    generated_content: str           # The text to send to user
    

    
    primary_language: str            # Locked language from start
    last_rejection_turn: int         # Turn number of last "No" to confirmation
    
    # FACT TRACKING
    asked_facts: List[str]           # List of fact keys/categories already asked
    answered_facts: List[str]        # List of facts explicitly answered by user
    
    stage: str                       # "investigation", "confirmation", "completed"
    turn_count: int                  # Turn counter to force clarification loops

# Node: Detect Language
def detect_language_node(state: LegalState):
    # Language Lock: If primary_language is set, KEEP IT.
    primary_lang = state.get("primary_language")
    if primary_lang:
        return {"user_language": primary_lang}

    messages = state["messages"]
    if not messages:
        return {"user_language": "en", "primary_language": "en"}
    
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
        
    return {"user_language": lang_code, "primary_language": lang_code}

# Node: Analyze Legal Context
def analyze_legal_context_node(state: LegalState):
    messages = state["messages"]
    current_facts = state.get("legal_facts", {})
    current_critical = state.get("critical_facts", {})
    current_optional = state.get("optional_facts", {})
    current_stage = state.get("stage", "investigation")
    
    # Track asked/answered
    asked_facts = set(state.get("asked_facts", []))
    answered_facts = set(state.get("answered_facts", []))
    
    # Increase turn count
    current_turn_count = state.get("turn_count", 0) + 1
    
    conversation_history = "\n".join([f"{m.type}: {m.content}" for m in messages])
    
    # 1. Extraction & Intent Detection Prompt
    extraction_prompt = f"""
    You are an expert AI Legal Assistant 'Satta Vizhi'.
    
    [TASK]
    Analyze the conversation history.
    
    1. **Identify Intent**: What is the specific legal issue? (e.g., 'Landlord Dispute', 'Divorce Petition')
    2. **Fact Extraction**: Extract meaningful legal facts.
    3. **Schema Definition**: For this specific intent, define the REQUIRED critical fields that MUST be collected.
    
    [CURRENT FACTS]
    Critical: {json.dumps(current_critical)}
    Optional: {json.dumps(current_optional)}
    
    [CONVERSATION HISTORY]
    {conversation_history}
    
    [OUTPUT FORMAT]
    Return a VALID JSON object (no markdown):
    {{
        "intent": "string",
        "extracted_critical_facts": {{ "key": "value" }},
        "extracted_optional_facts": {{ "key": "value" }},
        "required_keys_schema": ["key1", "key2", "key3"]
    }}
    """
    
    response = llm.invoke([
        SystemMessage(content="You are a legal reasoning engine. Output valid JSON only."),
        HumanMessage(content=extraction_prompt)
    ])
    
    try:
        content = response.content
        if "```" in content:
            content = content.replace("```json", "").replace("```", "")
        
        analysis = json.loads(content.strip())
        
        # Merge facts
        new_critical = analysis.get("extracted_critical_facts", {})
        new_optional = analysis.get("extracted_optional_facts", {})
        required_keys = analysis.get("required_keys_schema", [])
        intent = analysis.get("intent", "Unknown")
        
        # Merge with existing logic (prefer new values if non-null/empty)
        # We need to be careful not to overwrite existing valid data with empty/null if LLM hallucinates
        updated_critical = current_critical.copy()
        for k, v in new_critical.items():
            if v and v != "unknown" and v != "null":
                updated_critical[k] = v
                
        updated_optional = current_optional.copy()
        for k, v in new_optional.items():
            if v:
                updated_optional[k] = v

        # FACT-FIRST VALIDATION & TRACKING
        # Programmatically calculate missing fields based on the LLM's defined schema and our actual data
        missing_critical_fields = []
        present_critical_count = 0
        newly_added_facts_count = 0
        
        # 1. Update Answered Facts based on extraction
        for key, val in updated_critical.items():
            if val and str(val).lower() not in ["unknown", "null"]:
                if key not in answered_facts:
                    answered_facts.add(key)
                    newly_added_facts_count += 1
        
        # 2. Filter Missing Fields (Remove anything already answered OR asked recently without result?)
        # Actually, if we asked and they didn't answer, we might need to re-ask differently.
        # But we must NEVER ask what is in answered_facts.
        
        for key in required_keys:
            if key in answered_facts:
                present_critical_count += 1
            else:
                missing_critical_fields.append(key)
                
        # 3. Calculate Readiness
        total_required = len(required_keys)
        readiness_score = 0
        if total_required > 0:
            readiness_score = int((present_critical_count / total_required) * 100)
            
        # Stop-gap: If we have many facts but LLM didn't return schema, boost score slightly
        if readiness_score == 0 and len(answered_facts) > 3:
            readiness_score = 50
            
        # 4. Anti-Inflation: If NO new facts added this turn, do not increase readiness aggressively
        previous_score = state.get("readiness_score", 0)
        if newly_added_facts_count == 0:
            # Cap readiness at previous level to prevent "chatty" inflation
            if readiness_score > previous_score:
                readiness_score = previous_score

        # Stage Management & Confirmation Logic
        next_step = "ask_question"
        new_stage = current_stage
        last_rejection = state.get("last_rejection_turn", -1)
        
        # --- READINESS GATEKEEPER ---
        # 1. Enforce minimum turns (Clarification Discipline)
        if current_turn_count <= 2:
            if readiness_score > 60: readiness_score = 60
            
        # 2. Check for Placeholders / Ambiguity
        has_placeholders = False
        vals = list(updated_critical.values())
        if any(x and str(x).lower() in ["unknown", "tbd", "insert", "placeholder", "null", "none"] for x in vals):
            has_placeholders = True
            
        # 3. Minimum Critical Categories (Diversity Check)
        # We want >= 3 distinct non-placeholder facts
        distinct_facts = [v for v in vals if v and str(v).lower() not in ["unknown", "tbd", "insert", "placeholder"]]
        if len(distinct_facts) < 3:
            if readiness_score > 75: readiness_score = 75
            
        # 4. Cap score if placeholders exist
        if has_placeholders and readiness_score > 80:
             readiness_score = 80
             
        # --- CONFIRMATION RETRY LOGIC (STRENGTHENED) ---
        # If user previously rejected, force at least 2 turns or 2 NEW facts
        if last_rejection > 0:
            turns_since_reject = current_turn_count - last_rejection
            
            # Reset rejection if user explicity says "ready" (handled by intent logic ideally, but simplest here is time)
            if turns_since_reject < 2:
                 # Check if we have gathered significant new info
                 # We track newly_added_facts_count. 
                 # This simple logic holds off confirmation for 2 turns.
                 if readiness_score > 79: readiness_score = 79 
        
        # --- TRANSITION LOGIC ---
        if current_stage == "confirmation":
            last_msg = messages[-1].content.lower()
            # aggressive check for rejection
            if any(x in last_msg for x in ["no", "wait", "stop", "wrong", "missing", "incorrect", "not yet", "hold on"]):
                new_stage = "investigation"
                next_step = "ask_question"
                last_rejection = current_turn_count # Mark rejection turn
            elif any(x in last_msg for x in ["yes", "proceed", "go", "correct", "continue", "right", "agree"]):
                next_step = "generate_document"
            else:
                # Ambiguous? Assume proceed or re-confirm. Let's ask to confirm again to be safe.
                next_step = "ask_confirmation" 
        else:
            # Investigation stage
            if readiness_score >= 80:
                next_step = "ask_confirmation"
                new_stage = "confirmation"
            else:
                next_step = "ask_question"

        updated_legal_facts = {**state.get("legal_facts", {}), **updated_critical, **updated_optional}
        
        return {
            "legal_facts": updated_legal_facts,
            "critical_facts": updated_critical,
            "optional_facts": updated_optional,
            "intent": intent,
            "missing_fields": missing_critical_fields,
            "readiness_score": readiness_score,
            "next_step": next_step,
            "stage": new_stage,
            "turn_count": current_turn_count,
            "last_rejection_turn": last_rejection,
            "asked_facts": list(asked_facts),
            "answered_facts": list(answered_facts)
        }
    except Exception as e:
        print(f"Error parsing analysis: {e}")
        return {
            "next_step": "ask_question",
            "readiness_score": 0,
            "stage": current_stage
        }

# Node: Generate Question
def generate_question_node(state: LegalState):
    lang = state.get("user_language", "en")
    intent = state.get("intent", "General Legal Issue")
    missing = state.get("missing_fields", [])
    next_step = state.get("next_step", "ask_question")
    messages = state.get("messages", [])
    
    if next_step == "ask_confirmation":
        # Confirmation Question
        prompt = f"""
        Translate this to {lang}:
        "I have sufficient information to proceed with drafting the legal document. Shall I continue?"
        Return ONLY the translated text.
        """
    else:
        # MEMORY GUARD checks
        # Get recent AI messages to find what was just asked
        recent_ai_msgs = [m.content for m in messages if isinstance(m, AIMessage)][-2:]
        recent_context = "\n".join(recent_ai_msgs)
        
        # Filter: Remove keys that are already answered
        answered_facts = state.get("answered_facts", [])
        asked_facts = state.get("asked_facts", [])
        
        # Filter missing_fields to exclude anything we already have
        # This is a double-check on top of the Analysis node
        filtered_missing = [f for f in missing if f not in answered_facts]
        
        # If filtered_missing is empty but we are still here (score < 80),
        # we need to ask an open-ended question or find a secondary detail.
        
        prompt = f"""
        You are a compassionate legal assistant.
        User Language: {lang}
        Intent: {intent}
        Missing Critical Info: {filtered_missing}
        
        [What we ALREADY KNOW (Do NOT Ask)]: {answered_facts}
        [RECENTLY ASKED QUESTIONS]: {recent_context}
        
        Task: 
        1. Generate ONE clear, polite follow-up question to collect the missing critical info.
        2. STRICT RULE: Do NOT ask about anything in [What we ALREADY KNOW].
        3. STRICT RULE: Do NOT ask about anything mentioned in [RECENTLY ASKED QUESTIONS].
        4. Use {lang} language.
        5. If [Missing Critical Info] is empty, ask: "Is there any other important detail or document (like an agreement or proof) you haven't mentioned?"
        
        Return ONLY the question text in {lang}.
        """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    question = response.content.strip().strip('"')
    
    return {"generated_content": question}

# Node: Generate Document
def generate_document_node(state: LegalState):
    facts = state.get("legal_facts", {})
    intent = state.get("intent", "Legal Document")
    score = state.get("readiness_score", 0)
    
    prompt = f"""
    Generate a formal legal draft/document.
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
        "ask_confirmation": "generate_question", # Re-use generic question node but with different prompt logic
        "generate_document": "generate_document"
    }
)

workflow.add_edge("generate_question", END)
workflow.add_edge("generate_document", END)

# Persistence
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from psycopg_pool import ConnectionPool

raw_db_url = os.getenv("DB_URL", "postgresql://postgres:1234@localhost:5432/legal_db")
if raw_db_url.startswith("jdbc:"):
    DB_URL = raw_db_url.replace("jdbc:", "", 1)
else:
    DB_URL = raw_db_url

checkpointer = None

try:
    # Try Postgres Setup
    with ConnectionPool(conninfo=DB_URL, min_size=1, max_size=1, kwargs={"autocommit": True}) as setup_pool:
        temp_saver = PostgresSaver(setup_pool)
        temp_saver.setup()
    
    # Initialize Runtime Pool
    pool = ConnectionPool(conninfo=DB_URL, max_size=20)
    checkpointer = PostgresSaver(pool)
    print("Connected to Postgres for persistence.")
except Exception as e:
    print(f"Persistence Warning: Could not connect to Postgres ({e}). Falling back to In-Memory Checkpointer.")
    checkpointer = MemorySaver()

app = workflow.compile(checkpointer=checkpointer)

def process_message(thread_id: str, user_input: str):
    config = {"configurable": {"thread_id": thread_id}}
    
    app.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config
    )
    
    final_state = app.get_state(config).values
    
    generated_content = final_state.get("generated_content", "")
    facts = final_state.get("legal_facts", {})
    intent = final_state.get("intent", "")
    score = final_state.get("readiness_score", 0)
    next_step = final_state.get("next_step", "")
    
    return {
        "content": generated_content,
        "entities": facts,
        "intent": intent,
        "readiness_score": score,
        "is_document": next_step == "generate_document"
    }
