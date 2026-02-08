import os
import json
from typing import TypedDict, Annotated, List, Union, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.output_parsers import JsonOutputParser

# Import shared LLM provider
from llm_provider import llm
from bilingual_generator import generate_bilingual_document

# Normalize user answers so "No / Unknown" are terminal
def normalize_value(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ["unknown", "null", "none", "not available", "na", "no"]:
        return "NOT_AVAILABLE"
    return v

# 🔁 Canonical Alias Map to prevent semantic repetition
CANONICAL_ALIASES = {
    "witness": "witness_details",
    "witnesses": "witness_details",
    "witness_info": "witness_details",
    "eyewitness": "witness_details",
    "bystanders": "witness_details"
}

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
    asked_facts: List[str]            # List of fact keys/categories already asked
    answered_facts: Dict[str, Any]    # Dict of facts explicitly answered {key: value}
    fact_conflicts: Dict[str, List[Any]] # Conflicting values {key: [val1, val2]}
    
    stage: str                       # "investigation", "confirmation", "completed"
    turn_count: int                  # Turn counter to force clarification loops
    last_input_hash: str             # Idempotency check
    fallback_turn: int               # Turn number when fallback question was asked (-1 if not asked)

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
    
    # Handle backward compatibility for answered_facts (List vs Dict)
    raw_answered = state.get("answered_facts", {})
    if isinstance(raw_answered, list):
        answered_facts = {k: "unknown" for k in raw_answered}
    else:
        answered_facts = raw_answered
        
    fact_conflicts = state.get("fact_conflicts", {})
    
    # Increase turn count
    current_turn_count = state.get("turn_count", 0) + 1
    fallback_turn = state.get("fallback_turn", -1)
    
    conversation_history = "\n".join([f"{m.type}: {m.content}" for m in messages])
    
    # 1. Extraction & Intent Detection Prompt
    extraction_prompt = f"""
    You are an expert AI Legal Assistant 'Satta Vizhi'.
    
    [GLOBAL CONSTRAINT]
    You MUST extract only FACTUAL information. 
    You MUST NOT extract legal conclusions, sections, acts, or court jurisdictions.
    
    [CANONICAL FACT DIMENSIONS - NORMALIZATION RULES]
    To eliminate semantic repetition, you MUST map user inputs to these Abstract Canonical Dimensions:
    
    1. **Event Dimension**:
       - Key: `primary_event_overview` (The main thing that happened)
       - Key: `specific_action` (Specific acts done by parties)
    2. **Party Dimension**:
       - Key: `counterparty_name` (The person/entity opposing the user)
       - Key: `counterparty_role` (Landlord, Husband, Bank, etc.)
       - Key: `user_role` (Tenant, Wife, Customer, etc.)
    3. **Time Dimension**:
       - Key: `event_timestamp` (Date/Time of main event)
       - Key: `duration_frequency` (How long/often)
    4. **Place/Context Dimension**:
       - Key: `incident_location` (Physical or Digital place)
       - Key: `reference_identifier` (Account Number, ID, Reg Number)
    5. **Impact Dimension**:
       - Key: `financial_loss_value` (Monetary impact)
       - Key: `harm_description` (Non-monetary harm)
    6. **Evidence Dimension**:
       - Key: `evidence_available` (Documents like Salary Slips, Offer Letter, Termination Letter, Contracts)

    [CONSISTENCY & REDUNDANCY CHECK]
    - **Normalization**: If the user says "My husband hit me" -> extract 'primary_event_overview': "Physical assault per user". 
    - **Deduplication**: Compare with [CURRENT FACTS]. If 'event_timestamp' is already known, DO NOT include it in 'required_keys_schema' even if the user rephrases it as 'date of calling'.
    - **Locking**: If a user previously said "No" or "Unknown" to a dimension, it is locked. Do not put it in schema.

    [TASK]
    Analyze the conversation history.
    
    1. **Identify Intent**: specific factual problem.
    2. **Fact Extraction**: Extract facts using the CANONICAL KEYS above.
       - Use "NOT_AVAILABLE" for negative answers to lock them.
    3. **Schema Definition**: Define REQUIRED fields using ONLY the CANONICAL KEYS above.
    
    [CURRENT FACTS]
    Critical: {json.dumps(current_critical)}
    Optional: {json.dumps(current_optional)}
    
    [CONVERSATION HISTORY]
    {conversation_history}
    
    [SAFETY CHECK (CRITICAL)]
    Analyze if the user input involves:
    - Immediate danger to life
    - Violence / Physical Assault (ongoing or planned)
    - Serious criminal activity (not just civil disputes)
    - Emergency situations
    
    If ANY of these are detected, set "safety_status": "UNSAFE" and "safety_reason": "Reason...".
    Otherwise, set "safety_status": "SAFE".

    [OUTPUT FORMAT]
    Return a VALID JSON object (no markdown):
    {{
        "intent": "string",
        "safety_status": "SAFE" or "UNSAFE",
        "extracted_critical_facts": {{ "CANONICAL_KEY": "value" }},
        "extracted_optional_facts": {{ "CANONICAL_KEY": "value" }},
        "required_keys_schema": ["CANONICAL_KEY_1", "CANONICAL_KEY_2"]
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
        
        # New extractions
        new_critical = analysis.get("extracted_critical_facts", {})
        normalized_critical = {}
        for k, v in new_critical.items():
            canonical_key = CANONICAL_ALIASES.get(k, k)
            normalized_critical[canonical_key] = v

        new_critical = normalized_critical
        new_optional = analysis.get("extracted_optional_facts", {})
        required_keys = [
            CANONICAL_ALIASES.get(k, k)
            for k in analysis.get("required_keys_schema", [])
        ]

        intent = analysis.get("intent", "Unknown")
        
        # --- SAFETY CHECK ---
        if analysis.get("safety_status") == "UNSAFE":
             return {
                 "legal_facts": state.get("legal_facts", {}),
                 "critical_facts": {},
                 "optional_facts": {},
                 "intent": "SAFETY_REFUSAL",
                 "missing_fields": [],
                 "readiness_score": 0,
                 "next_step": "refusal",
                 "stage": "completed",
                 "turn_count": current_turn_count,
                 "last_rejection_turn": -1,
                 "asked_facts": [],
                 "answered_facts": {},
                 "fact_conflicts": {},
                 "fallback_turn": -1
             }
        
        # Metrics for Readiness
        newly_added_facts_count = 0
        resolved_conflicts_count = 0
        
        # --- CONFLICT DETECTION & FACT LOCKING ---
        # Helper to process updates
        updated_critical = current_critical.copy()
        
        for k, v in new_critical.items():
            v = normalize_value(v)

            if v == "NOT_AVAILABLE":
                answered_facts[k] = "NOT_AVAILABLE"
                updated_critical[k] = "NOT_AVAILABLE"
                continue
            # Check for conflict resolution
            if k in fact_conflicts:
                # User provided a value for a specifically conflicted field
                # We interpret this as the resolution
                answered_facts[k] = v
                updated_critical[k] = v
                del fact_conflicts[k]
                resolved_conflicts_count += 1
                
            elif k in answered_facts:
                existing_val = str(answered_facts[k]).strip()
                new_val = str(v).strip()
                
                # 1. Exact Match: No Op
                if existing_val.lower() == new_val.lower():
                    pass
                
                # Global Constraint: DO NOT MODIFY numeric values
                elif any(char.isdigit() for char in new_val) and new_val != existing_val:
                     # If conflicting numbers, trigger conflict resolution
                     fact_conflicts[k] = [existing_val, v]
                    
                elif existing_val.lower() in new_val.lower() or new_val.lower() in existing_val.lower():
                     # Update to the longer/more detailed version
                     longest_val = new_val if len(new_val) > len(existing_val) else existing_val
                     answered_facts[k] = longest_val
                     updated_critical[k] = longest_val
                     # Do NOT trigger conflict. Treat as reinforcement.
                     
                # 3. True Conflict
                else:
                    # CONFLICT DETECTED!
                    # Do NOT overwrite. Record conflict.
                    fact_conflicts[k] = [existing_val, v]
            else:
                # New fact found
                answered_facts[k] = v
                updated_critical[k] = v
                newly_added_facts_count += 1
                
        # Optional facts merge (less strict, but let's lock them too for consistency)
        updated_optional = current_optional.copy()
        for k, v in new_optional.items():
            if v and str(v).lower() not in ["unknown", "null"]:
                if k not in answered_facts: # Treat optional same as critical for locking
                    answered_facts[k] = v
                    updated_optional[k] = v
                    # Optional facts don't necessarily count for "critical" readiness but good to track

                    # Optional facts don't necessarily count for "critical" readiness but good to track

        # --- MODE 2 EXPRESS TRIGGER (STRICT) ---
        last_msg_clean = messages[-1].content.strip().lower()
        
        # 1. Explicit Completion Commands -> Move to CONFIRMATION (Stage 2)
        # User explicitly says they are done or wants to generate.
        # We DO NOT generate immediately. We must go to Confirmation FIRST.
        gen_triggers = ["proceed", "generate", "continue", "draft", "make document", "no more details", "no more info", "nothing else to add", "nothing more", "done"]
        is_explicit_trigger = any(t in last_msg_clean for t in gen_triggers)
        
        # 2. Ambiguous "Yes" Fail-Safe (Only if NO new facts were extracted)
        is_ambiguous_yes = (newly_added_facts_count == 0) and (last_msg_clean in ["yes", "yeah", "yep", "ok", "okay", "sure", "fine", "go ahead"])

        if is_explicit_trigger or is_ambiguous_yes:
             return {
                 "legal_facts": {**state.get("legal_facts", {}), **updated_critical, **updated_optional},
                 "critical_facts": updated_critical,
                 "optional_facts": updated_optional,
                 "intent": intent,
                 "missing_fields": [], # Clear missing to prevent loop
                 "readiness_score": 100, # Force Internal Completeness
                 "next_step": "ask_confirmation", # GO TO CONFIRMATION (Stage 2)
                 "stage": "confirmation", # Set Stage 2
                 "turn_count": current_turn_count,
                 "last_rejection_turn": state.get("last_rejection_turn", -1),
                 "asked_facts": list(asked_facts),
                 "answered_facts": answered_facts,
                 "fact_conflicts": fact_conflicts,
                 "fallback_turn": fallback_turn
             }

        # --- MISSING FIELDS CALCULATION ---
        present_critical_count = 0
        missing_critical_fields = []

        for key in required_keys:
            if key in answered_facts:
                continue  # already answered or locked
            missing_critical_fields.append(key)

                
        # --- READINESS CALCULATION ---
        total_required = len(required_keys)
        readiness_score = 0
        if total_required > 0:
            readiness_score = int((present_critical_count / total_required) * 100)
            
        # Fallback for generic intents
        if readiness_score == 0 and len(answered_facts) > 3:
            readiness_score = 50
            
        # Guard 1: Anti-Inflation
        previous_score = state.get("readiness_score", 0)
        # Only allow score increase if we have NEW info (confirmed fact or resolved conflict)
        if newly_added_facts_count == 0 and resolved_conflicts_count == 0:
             if readiness_score > previous_score:
                 readiness_score = previous_score

        # Guard 2: Unresolved Conflicts Cap
        if len(fact_conflicts) > 0:
            if readiness_score > 70:
                readiness_score = 70

        # Stage Management
        next_step = "ask_question"
        new_stage = current_stage
        last_rejection = state.get("last_rejection_turn", -1)
        
        # --- FALLBACK QUESTION HANDLING ---
        # If the PREVIOUS turn was the fallback question, intercept the user's answer
        if fallback_turn == (current_turn_count - 1):
             last_msg_clean = messages[-1].content.strip().lower()
             
             # Case A: "No" or "Done" -> User has no more facts -> Force Confirmation
             if last_msg_clean in ["no", "nope", "nothing", "none", "no more", "no details", "not really", "na", "done"]:
                 new_stage = "confirmation"
                 next_step = "ask_confirmation"
                 # Return immediately to bypass readiness blocks
                 return {
                     "legal_facts": {**state.get("legal_facts", {}), **updated_critical, **updated_optional},
                     "critical_facts": updated_critical,
                     "optional_facts": updated_optional,
                     "intent": intent,
                     "missing_fields": missing_critical_fields,
                     "readiness_score": 100, # Force valid
                     "next_step": next_step,
                     "stage": new_stage,
                     "turn_count": current_turn_count,
                     "last_rejection_turn": last_rejection,
                     "asked_facts": list(asked_facts),
                     "answered_facts": answered_facts,
                     "fact_conflicts": fact_conflicts,
                     "fallback_turn": fallback_turn
                 }

             # Case B: "Yes" -> User has facts -> Let them talk -> Continue Investigation
             # We do NOT reset fallback_turn because we don't want to ask "Is there anything else?" again immediately.
             # We just let the flow proceed to generate_question, which will handle the prompt.
             elif last_msg_clean in ["yes", "yeah", "yep", "ok", "sure"]:
                 pass 

        # --- READINESS GATEKEEPER ---
        # 4. MINIMUM INVESTIGATION GUARDRAIL
        # The system must always ask at least ONE follow-up question.
        # Confirmation or document generation must be impossible on the first user turn.
        if current_turn_count <= 2:
            readiness_score = min(readiness_score, 60) # Cap strictly
            
        # Check for Placeholders
        vals = list(updated_critical.values())
        if any(x and str(x).lower() in ["unknown", "tbd", "insert", "placeholder"] for x in vals):
             if readiness_score > 80: readiness_score = 80
        
        # --- TRANSITION LOGIC ---
        if current_stage == "confirmation":
            # 5. CONFIRMATION LOCK (STAGE 2 -> STAGE 3)
            last_msg = messages[-1].content.strip().upper() # Normalize to UPPER for strict check
            
            # Explicit Rejection / Edit -> Go back to investigation
            # Keyword: EDIT
            if "EDIT" in last_msg or "CHANGE" in last_msg or "WRONG" in last_msg:
                new_stage = "investigation"
                next_step = "ask_question"
                last_rejection = current_turn_count
                
            # Explicit Approval -> Generate
            # STRICT KEYWORD: "CONFIRM"
            elif "CONFIRM" in last_msg:
                next_step = "generate_document"
                new_stage = "completed"
                
            # Anything else -> Repeat Confirmation Question
            else:
                next_step = "ask_confirmation" 
                
        else:
            # Investigation stage
            # If conflicts exist, we MUST stay in investigation/questioning
            if len(fact_conflicts) > 0:
                next_step = "ask_question"
            # If we haven't asked at least one question (turn 1), forbid confirmation
            elif current_turn_count < 2:
                 next_step = "ask_question"
            elif readiness_score >= 80:
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
            "answered_facts": answered_facts,
            "fact_conflicts": fact_conflicts,
            "fallback_turn": fallback_turn
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
    current_turn = state.get("turn_count", 0)
    fallback_turn = state.get("fallback_turn", -1)
    
    # Initialize SAFE DEFAULT for asked_facts here to prevent UnboundLocalError
    asked_facts = state.get("asked_facts", [])
    
    fact_conflicts = state.get("fact_conflicts", {})
    
    if next_step == "refusal":
        return {
            "generated_content": "I cannot assist with this request. If you are in immediate danger or facing an emergency, please contact the police or emergency services immediately. This system is for legal documentation assistance only.",
            "asked_facts": asked_facts
        }
    
    if next_step == "ask_confirmation":
        # Confirmation Question (STAGE 2)
        summary_points = []
        for k, v in state.get("answered_facts", {}).items():
            summary_points.append(f"- {k}: {v}")
        summary_text = "\n".join(summary_points)

        prompt = f"""
        Translate the following message to {lang} ONLY if the user is not speaking English.
        If the user is speaking English, keep it exactly as is.

        Context:
        {summary_text}

        Message:
        "Please confirm the above details.
        Type CONFIRM to generate the document or EDIT to make changes."
        
        Return ONLY the final message content.
        """
    elif len(fact_conflicts) > 0:
        # CONFLICT RESOLUTION MODE
        # Pick the first conflict to resolve
        conflict_key = list(fact_conflicts.keys())[0]
        target_field = conflict_key # Ensure target_field is defined for prompt usage
        conflict_vals = fact_conflicts[conflict_key]
        
        prompt = f"""
        You are a legal intake assistant.

        You must ask ONLY about the following factual field.
        You are NOT allowed to ask about anything else.

        FACT_KEY: {target_field}

        Rules:
        - Ask exactly ONE question
        - Ask ONLY about FACT_KEY
        - Do NOT rephrase earlier questions
        - Do NOT include examples
        - Do NOT ask follow-up questions
        - Do NOT ask about laws or rights
        - Use language: {lang}

        Return ONLY the question text.
        """
        
    else:
        # MEMORY GUARD checks
        recent_ai_msgs = [m.content for m in messages if isinstance(m, AIMessage)][-2:]
        recent_context = "\n".join(recent_ai_msgs)
        
        # Handling Answered Facts
        raw_answered = state.get("answered_facts", {})
        if isinstance(raw_answered, dict):
            answered_keys = list(raw_answered.keys())
        else:
            answered_keys = list(raw_answered) # Fallback if list
            
        # asked_facts is already initialized at top
        
        # STRICT FILTER: Never ask for what we have
        # TASK 4: Selection Discipline
        
        candidate_fields = [f for f in missing if f not in answered_keys and f not in asked_facts]
        
        candidate_fields = [f for f in candidate_fields if f not in answered_keys]

        target_field = None
        
        if candidate_fields:
            target_field = candidate_fields[0]
            asked_facts.append(target_field)
            target_instruction = f"Target missing field: {target_field}"
        else:
            # HARD STOP: nothing more to specific to ask
            
            # CHECK: Have we already asked the fallback question?
            if fallback_turn > -1:
                # YES, we already asked it.
                # Do NOT ask it again.
                
                # Check if user just said "Yes" (indicating they want to talk)
                last_msg_clean = messages[-1].content.strip().lower()
                if last_msg_clean in ["yes", "yeah", "yep", "ok", "sure"]:
                    return {
                        "generated_content": (
                            "Please type the additional details. If there are no more details, type DONE."
                                if state.get("user_language", "en") == "en"
                                else "கூடுதல் விவரங்களை உள்ளிடவும். கூடுதல் விவரங்கள் இல்லை என்றால், DONE என டைப் செய்யவும்."
                        ),
                        "asked_facts": asked_facts
                    }
                
                # Otherwise, if we have no questions and already asked fallback -> Confirmation
                return {
                     "generated_content": (
                        "Please type the additional details. If there are no more details, type DONE."
                        if state.get("user_language", "en") == "en"
                        else "கூடுதல் விவரங்களை உள்ளிடவும். கூடுதல் விவரங்கள் இல்லை என்றால், DONE என டைப் செய்யவும்."
                     ),
                     "next_step": "ask_confirmation", # Force transition
                     "asked_facts": asked_facts
                }

            # First time asking fallback?
            return {
                "generated_content": (
                    "Please type the additional details. If there are no more details, type DONE."
                    if state.get("user_language", "en") == "en"
                    else "கூடுதல் விவரங்களை உள்ளிடவும். கூடுதல் விவரங்கள் இல்லை என்றால், DONE என டைப் செய்யவும்."
                ),
                "asked_facts": asked_facts,
                "fallback_turn": current_turn # Mark as asked
            }


        prompt = f"""
        You are a compassionate legal assistant.
        User Language: {lang}
        Intent: {intent}
        
        [STRICT TARGET CONTROL]
        {target_instruction}
        
        [What we ALREADY KNOW (STRICTLY DO NOT ASK)]: {answered_keys}
        [What we ALREADY ASKED (STRICTLY DO NOT REPEAT)]: {asked_facts}
        [RECENTLY ASKED QUESTIONS]: {recent_context}
        
        [GLOBAL RULES]
        1. ASK ONLY FACTUAL QUESTIONS. 
        2. NEVER ASK about Laws, Acts, Sections, Legal Validity, or User Rights.
        3. Allowed Categories: Event details, People involved, Time/Dates, Locations/Accounts, Financial/Emotional Impact.
        
        Task: 
        1. Generate ONE clear, polite follow-up question strictly targeting the [TARGET CANONICAL FIELD].
        2. STRICT RULE: Do NOT ask about anything in [What we ALREADY KNOW].
        3. STRICT RULE: If 'bank_name' or 'account' is in [What we ALREADY KNOW], do NOT mention it in the question.
        4. STRICT RULE: Do NOT ask about anything mentioned in [RECENTLY ASKED QUESTIONS].
        5. Use {lang} language.
        6. If no specific target is defined, ask: "Is there any other important factual detail you would like to add?"
        
        Return ONLY the question text in {lang}.
        """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    question = response.content.strip().strip('"')
    
    return {
        "generated_content": question,
        "asked_facts": asked_facts
    }

# Node: Generate Document (Bilingual)
def generate_document_node(state: LegalState):
    facts = state.get("legal_facts", {})
    intent = state.get("intent", "Legal Document")
    lang = state.get("user_language", "en")
    
    # Generate bilingual document
    bilingual_result = generate_bilingual_document(intent, facts, lang)
    
    # Format the output for frontend
    output = {
        "user_language_content": bilingual_result["user_language_content"],
        "english_content": bilingual_result["english_content"],
        "document_type": bilingual_result["document_type"],
        "readiness_score": bilingual_result["readiness_score"],
        "user_language": lang,
        "is_bilingual": True
    }
    
    # For backward compatibility, also set generated_content
    # This will be the user language version for display
    generated_content = f"""# Legal Document - {bilingual_result['document_type'].replace('_', ' ').title()}

**Language**: {lang.upper()} + English (Bilingual)
**Readiness Score**: {bilingual_result['readiness_score']}/100

---

## Version in Your Language ({lang.upper()})

{bilingual_result['user_language_content']}

---

## English Version (For Official Submission)

{bilingual_result['english_content']}

---

**Note**: This document has been generated in both languages. The bilingual PDF will contain both versions for your convenience.
"""
    
    return {
        "generated_content": generated_content,
        "bilingual_document": output
    }

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
        "refusal": "generate_question", # Handle safety refusal in question node
        "generate_document": "generate_document",
        "completed": "generate_document" # Safety edge if stage is completed
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

import hashlib

def process_message(thread_id: str, user_input: str):
    config = {"configurable": {"thread_id": thread_id}}
    
    # 1. IDEMPOTENCY CHECK
    # Check if this exact input was just processed to avoid duplicates/refreshes
    current_input_hash = hashlib.md5(user_input.encode()).hexdigest()
    
    current_state = app.get_state(config).values
    last_processed_hash = current_state.get("last_input_hash", "")
    
    if last_processed_hash == current_input_hash:
        print(f"Idempotency: Skipping duplicate input for thread {thread_id}")
        # Return existing state without invoking graph
        generated_content = current_state.get("generated_content", "")
        facts = current_state.get("legal_facts", {})
        intent = current_state.get("intent", "")
        score = current_state.get("readiness_score", 0)
        next_step = current_state.get("next_step", "")
        
        return {
            "content": generated_content,
            "entities": facts,
            "intent": intent,
            "readiness_score": score,
            "is_document": next_step == "generate_document"
        }

    # 2. INVOKE GRAPH
    app.invoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "last_input_hash": current_input_hash
        },
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
