import os
import json
from datetime import datetime
from typing import TypedDict, Annotated, List, Union, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.output_parsers import JsonOutputParser

# Import shared LLM provider
from llm_provider import llm
from bilingual_generator import generate_bilingual_document

# ============================================================
# STAGE CONSTANTS (9-Stage Indian Legal Workflow Orchestrator)
# ============================================================
STAGE_INTAKE          = "intake"           # Stage 1: Intelligent Issue Intake
STAGE_READINESS       = "readiness"        # Stage 2: Legal Readiness Evaluation
STAGE_ACTION_ID       = "action_id"        # Stage 3: Legal Action Identification
STAGE_ACTION_EXPLAIN  = "action_explain"   # Stage 4: Action Explanation
STAGE_ACTION_CONFIRM  = "action_confirm"   # Stage 5: Confirm Action Selection
STAGE_DATA_COLLECT    = "data_collect"     # Stage 6: Document Data Collection
STAGE_GEN_DOCUMENT    = "gen_document"     # Stage 7: Document Generation
STAGE_DRAFT_MGMT      = "draft_mgmt"       # Stage 8: Draft Management
STAGE_COMPLETE        = "completed"        # Stage 9: Completion Verification

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
    
    stage: str                       # Current stage name (matches STAGE_* constants)
    turn_count: int                  # Turn counter to force clarification loops
    last_input_hash: str             # Idempotency check
    fallback_turn: int               # Turn number when fallback question was asked (-1 if not asked)

    # Stage 3-5 Action Selection
    legal_actions: List[Dict]        # Legal actions identified in Stage 3
    selected_action: Optional[str]   # User's chosen legal action (Stage 5)

    # Stage 9 Completion Checklist
    checklist: Dict[str, bool]

    # Bilingual document (Stage 7)
    bilingual_document: Optional[Dict]

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
    selected_action = state.get("selected_action", None)
    
    # Increase turn count
    current_turn_count = state.get("turn_count", 0) + 1
    fallback_turn = state.get("fallback_turn", -1)
    
    conversation_history = "\n".join([f"{m.type}: {m.content}" for m in messages])
    
    recent_question_context = ""
    if asked_facts:
        recent_question_context = f'''[RECENT QUESTION CONTEXT]
    The system's most recent question was trying to figure out the key: `{list(asked_facts)[-1]}`.
    If the user denied knowledge, YOU MUST ADD the key to `extracted_critical_facts` and set its value to "EXPLICITLY_DENIED".'''
    
    # 1. Extraction & Intent Detection Prompt
    extraction_prompt = f"""
    SYSTEM PROMPT – SATTA VIZHI (FREE VERSION)

    IDENTITY:
    You are Satta Vizhi, a free Indian legal guidance and complaint drafting assistant.
    You operate strictly under Indian law.
    You are NOT a lawyer, advocate, or law firm.
    You do NOT provide guaranteed legal advice, legal opinions, or legal representation.
    You provide structured legal information, procedural guidance, and complaint drafting assistance based only on user-provided facts.

    PURPOSE:
    Your purpose is to:
    1. Help users understand what type of legal case may apply to their issue.
    2. Explain available legal options in simple language.
    3. Suggest procedural next steps.
    4. Generate properly formatted complaint documents.
    5. Maintain safety, neutrality, and clarity.

    TARGET USERS:
    - Indian citizens
    - People without legal knowledge
    - First-time complainants
    - Rural and urban users

    TONE:
    - Calm, Respectful, Non-intimidating, Clear and simple, Neutral and structured.

    [CORE RULES]
    1. JURISDICTION RULE: Always confirm State, District, and Date of incident. If missing, ask for it.
    2. ONE QUESTION RULE: Ask only ONE question at a time. Do not overwhelm the user.
    3. NO ASSUMPTIONS RULE: Never assume intent, motive, evidence, legal sections, outcome. Only rely on confirmed user facts.
    4. SAFE LEGAL LANGUAGE RULE: Use cautious phrases ("May fall under", "Is commonly addressed under", "You may consider"). Never say ("You will win", "This guarantees").
    5. RISK ESCALATION RULE: If the issue involves Serious criminal charges, Arrest risk, Divorce litigation, Large property disputes, Constitutional issues -> Provide only general guidance and recommend consulting a licensed advocate.
    6. ILLEGAL REQUEST RULE: If user requests False complaint drafting, Fabricating evidence, Framing someone, Tax evasion, etc -> Politely refuse (Set safety_status to "UNSAFE").

    [LEGAL DOMAIN CLASSIFICATION]
    Classify issues into (if unclear, ask clarification):
    - Motor Vehicle Accident
    - Theft / Cheating
    - Assault
    - Cybercrime
    - Property Dispute
    - Money Recovery
    - Consumer Complaint
    - Employment Dispute
    - Domestic Violence
    - Defamation
    - Public Nuisance

    [GLOBAL CONSTRAINT]
    You MUST extract only FACTUAL information. 
    You MUST NOT extract legal conclusions, sections, acts, or court jurisdictions.
    
    [CANONICAL FACT DIMENSIONS - NORMALIZATION RULES]
    To eliminate semantic repetition, you MUST map user inputs to these Abstract Canonical Dimensions:
    1. **Jurisdiction & Time**: `state`, `district`, `incident_date` (MANDATORY)
    2. **Event Dimension**: `primary_event_overview`, `incident_description`
    3. **Party Dimension**: `counterparty_name`, `counterparty_address`, `counterparty_role`, `user_role`, `witness_details`
    4. **Personal Dimension**: `user_full_name`, `user_address`, `user_phone`
    5. **Place/Context Dimension**: `incident_location`, `product_name`, `defect_description`, `prior_complaints`
    6. **Impact/Financial Dimension**: `financial_loss_value`, `payment_details`, `harm_description`, `stolen_items`
    7. **Evidence Dimension**: `evidence_available`

    [CONSISTENCY & REDUNDANCY CHECK]
    - Dedup: Compare with [CURRENT FACTS].
    
    [TASK]
    Analyze the conversation history.
    1. **Identify Intent**: classify into one of the domains listed above.
    2. **Fact Extraction**: Extract facts using the CANONICAL KEYS above. Ignore fields the user has NOT mentioned.
    3. **Schema Definition**: Define `required_keys_schema` as a smart, contextual list of keys logically necessary.
       - ALWAYS include: `state`, `district`, `incident_date`, `incident_description`.
       - DO NOT badger the user with unnecessary details. Limit to 10 keys total.
    
    {recent_question_context}
    
    [CURRENT FACTS]
    Critical: {json.dumps(current_critical)}
    Optional: {json.dumps(current_optional)}
    
    [CONVERSATION HISTORY]
    {conversation_history}
    
    [TIME CONTEXT]
    The current date and time is: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}.
    If the user mentions relative times like "today", "yesterday", "this morning", "last week", calculate and extract the EXACT DATE (DD-MM-YYYY) and include it instead of the relative term. Do not extract just "yesterday" - extract the actual calendar date it corresponds to.

    [SAFETY CHECK (CRITICAL)]
    Check Immediate danger to life or ILLEGAL requests. Set safety_status to "UNSAFE" if found. Otherwise "SAFE".
    
    [OUTPUT FORMAT]
    Return a VALID JSON object (no markdown):
    {{{{
        "intent": "Motor Vehicle Accident / Theft / Cheating / etc.",
        "safety_status": "SAFE" or "UNSAFE",
        "extracted_critical_facts": {{{{ "CANONICAL_KEY": "value" }}}},
        "extracted_optional_facts": {{{{ "CANONICAL_KEY": "value" }}}},
        "required_keys_schema": ["CANONICAL_KEY_1", "CANONICAL_KEY_2"]
    }}}}
    """
    
    print("DEBUG PROMPT RECENT CONTEXT:", f"Asked facts: {asked_facts}")
    if asked_facts:
        print("DEBUG RECENT_QUESTION_CONTEXT activated line:", f"The system's most recent question was trying to figure out the key: `{list(asked_facts)[-1]}`.")
    
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
        print(f"DEBUG: LLM Raw Critical Extracted: {new_critical}")
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
        print(f"DEBUG: Required Keys Output from LLM: {required_keys}")

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
            if v is None:
                continue
            
            str_v = str(v).lower()
            if any(hallucination in str_v for hallucination in ["none", "null", "not_available", "unknown", "(unknown)", "tbd", "n/a"]):
                continue
                
            if str(v).upper() == "EXPLICITLY_DENIED":
                v = "EXPLICITLY_DENIED"
            else:
                v = normalize_value(v)
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

                if existing_val == "EXPLICITLY_DENIED" and new_val != "EXPLICITLY_DENIED":
                    # User clarified a previously denied/unknown fact. Overwrite it.
                    answered_facts[k] = new_val
                    updated_critical[k] = new_val
                elif existing_val != "EXPLICITLY_DENIED" and new_val == "EXPLICITLY_DENIED":
                    # LLM wrongly flagged as denied when we already have a valid value. Ignore.
                    pass
                # 1. Exact Match: No Op
                elif existing_val.lower() == new_val.lower():
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
                    newly_added_facts_count += 1
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
            val = answered_facts.get(key)
            if val is not None and str(val).strip() != "" and str(val).lower() not in ["none", "null", "not_available", "unknown"]:
                present_critical_count += 1
                continue  # already answered with valid content
            elif val == "EXPLICITLY_DENIED":
                # Explicitly locked by user
                present_critical_count += 1
                continue
            
            missing_critical_fields.append(key)

                
        # --- READINESS CALCULATION ---
        # Base readiness dynamically on the required_keys_schema the LLM decided on
        total_required = present_critical_count + len(missing_critical_fields)
        
        readiness_score = 0
        if total_required > 0:
            readiness_score = int((present_critical_count / total_required) * 100)
            
        # Fallback for generic intents
        if total_required == 0 and len(answered_facts) > 3:
            readiness_score = 50
            
        # Guard 0: Prevent backwards movement of score if LLM adds many missing fields suddenly
        previous_score = state.get("readiness_score", 0)
        if readiness_score < previous_score:
             readiness_score = previous_score
            
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
                
            # Explicit Approval -> Generate Options or Document
            # STRICT KEYWORD: "CONFIRM"
            elif "CONFIRM" in last_msg:
                if selected_action:
                    # User already chose an action, we were just collecting missing details.
                    next_step = "generate_document"
                    new_stage = "completed"
                else:
                    next_step = "ask_action_choice"
                    new_stage = "action_choice"
                
            # Anything else -> Repeat Confirmation Question
            else:
                next_step = "ask_confirmation" 
                
        elif current_stage == "action_choice":
            last_msg = messages[-1].content.strip()
            if last_msg.startswith("ACTION:") or last_msg.startswith("action:"):
                # User selected an action
                intent = last_msg.replace("ACTION:", "").replace("action:", "").strip()
                selected_action = intent
                # Instead of immediate generation, ask for second confirmation according to requirements
                next_step = "ask_action_confirm"
                new_stage = "action_confirm"
            else:
                next_step = "ask_action_choice"
                new_stage = "action_choice"
                
        elif current_stage == "action_confirm":
            last_msg = messages[-1].content.strip().upper()
            if "CONFIRM" in last_msg:
                if len(missing_critical_fields) > 0:
                    # We don't have enough info for the selected document. Ask for missing details!
                    next_step = "ask_question"
                    new_stage = "investigation"
                else:
                    next_step = "generate_document"
                    new_stage = "completed"
            elif "EDIT" in last_msg or "CHANGE" in last_msg:
                new_stage = "action_choice"
                next_step = "ask_action_choice"
                selected_action = None # Clear it
            else:
                next_step = "ask_action_confirm"
                
        else:
            # Investigation stage
            # If conflicts exist, we MUST stay in investigation/questioning
            if len(fact_conflicts) > 0:
                next_step = "ask_question"
            # If we haven't asked at least one question (turn 1), forbid confirmation
            elif current_turn_count < 2:
                 next_step = "ask_question"
            elif readiness_score >= 100:
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
            "selected_action": selected_action,
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

# Node: Generate Question (Structured Interview Approach)
# Intent-specific mandatory fields — always ask for these regardless of LLM schema
INTENT_REQUIRED_FIELDS = {
    "default": ["user_full_name", "state", "district", "incident_date", "incident_description", "incident_location"],
    "theft": ["user_full_name", "user_address", "user_phone", "state", "district", "incident_date", "incident_location", "incident_description", "stolen_items", "financial_loss_value", "evidence_available"],
    "cheating": ["user_full_name", "user_address", "user_phone", "state", "district", "incident_date", "counterparty_name", "counterparty_address", "incident_description", "financial_loss_value", "evidence_available"],
    "consumer": ["user_full_name", "user_address", "user_phone", "state", "district", "incident_date", "counterparty_name", "counterparty_address", "product_name", "defect_description", "financial_loss_value", "evidence_available"],
    "motor": ["user_full_name", "user_address", "user_phone", "state", "district", "incident_date", "incident_location", "counterparty_name", "incident_description", "harm_description", "financial_loss_value", "evidence_available"],
    "assault": ["user_full_name", "user_address", "user_phone", "state", "district", "incident_date", "incident_location", "counterparty_name", "counterparty_address", "incident_description", "harm_description", "witness_details", "evidence_available"],
    "cybercrime": ["user_full_name", "user_address", "user_phone", "state", "district", "incident_date", "incident_description", "financial_loss_value", "evidence_available"],
    "property": ["user_full_name", "user_address", "user_phone", "state", "district", "incident_date", "counterparty_name", "counterparty_address", "incident_description", "evidence_available"],
    "employment": ["user_full_name", "user_address", "user_phone", "state", "district", "incident_date", "counterparty_name", "counterparty_address", "incident_description", "financial_loss_value", "evidence_available"],
    "domestic": ["user_full_name", "user_address", "user_phone", "state", "district", "incident_date", "counterparty_name", "incident_description", "harm_description", "witness_details", "evidence_available"],
    "defamation": ["user_full_name", "user_address", "user_phone", "state", "district", "incident_date", "counterparty_name", "incident_description", "evidence_available"],
    "money": ["user_full_name", "user_address", "user_phone", "state", "district", "incident_date", "counterparty_name", "counterparty_address", "incident_description", "financial_loss_value", "payment_details", "evidence_available"],
}

def _get_intent_required_fields(intent: str) -> list:
    """Return the minimum required fields for a given intent."""
    if not intent:
        return INTENT_REQUIRED_FIELDS["default"]
    il = intent.lower()
    if any(t in il for t in ["theft", "stolen", "robbery", "burglary"]):
        return INTENT_REQUIRED_FIELDS["theft"]
    elif any(t in il for t in ["cheat", "fraud", "scam"]):
        return INTENT_REQUIRED_FIELDS["cheating"]
    elif any(t in il for t in ["consumer", "product", "service", "refund", "defective"]):
        return INTENT_REQUIRED_FIELDS["consumer"]
    elif any(t in il for t in ["motor", "accident", "vehicle", "car"]):
        return INTENT_REQUIRED_FIELDS["motor"]
    elif any(t in il for t in ["assault", "attack", "hurt", "battery"]):
        return INTENT_REQUIRED_FIELDS["assault"]
    elif any(t in il for t in ["cyber", "online", "hack", "phish"]):
        return INTENT_REQUIRED_FIELDS["cybercrime"]
    elif any(t in il for t in ["property", "land", "real estate", "trespass"]):
        return INTENT_REQUIRED_FIELDS["property"]
    elif any(t in il for t in ["employ", "salary", "wage", "job", "termination"]):
        return INTENT_REQUIRED_FIELDS["employment"]
    elif any(t in il for t in ["domestic", "violence", "dowry", "harass"]):
        return INTENT_REQUIRED_FIELDS["domestic"]
    elif any(t in il for t in ["defam", "slander", "libel"]):
        return INTENT_REQUIRED_FIELDS["defamation"]
    elif any(t in il for t in ["money", "loan", "debt", "recover"]):
        return INTENT_REQUIRED_FIELDS["money"]
    return INTENT_REQUIRED_FIELDS["default"]

def generate_question_node(state: LegalState):
    lang = state.get("user_language", "en")
    intent = state.get("intent", "General Legal Issue")
    next_step = state.get("next_step", "ask_question")
    messages = state.get("messages", [])
    current_turn = state.get("turn_count", 0)
    
    asked_facts = state.get("asked_facts", [])
    answered_facts = state.get("answered_facts", {})
    fact_conflicts = state.get("fact_conflicts", {})
    
    # Enforce intent-specific required fields as missing_fields if not already in state
    state_missing = state.get("missing_fields", [])
    intent_required = _get_intent_required_fields(intent)
    # Fields that are needed but not yet answered
    answered_keys = set(k for k, v in answered_facts.items() if v and str(v).lower() not in ["none", "null", "not_available", "unknown", "explicitly_denied"])
    intent_missing = [f for f in intent_required if f not in answered_keys]
    # Merge: use intent_missing if state_missing is empty or smaller
    if intent_missing and (not state_missing or len(intent_missing) > len(state_missing)):
        effective_missing = intent_missing
    else:
        effective_missing = state_missing
    
    # Safety refusal
    if next_step == "refusal":
        return {
            "generated_content": "I cannot assist with this request. If you are in immediate danger or facing an emergency, please contact the police or emergency services immediately. This system is for legal documentation assistance only.",
            "asked_facts": asked_facts
        }
    
    # Confirmation stage
    if next_step == "ask_confirmation":
        summary_points = []
        for k, v in answered_facts.items():
            if v != "NOT_AVAILABLE":
                display_key = k.replace("_", " ").title()
                summary_points.append(f"• {display_key}: {v}")
        
        summary_text = "\n".join(summary_points) if summary_points else "No details collected yet."
        
        confirmation_msg = f"""Based on our conversation, here's what I've understood:

{summary_text}

Please review the above information carefully.
• Type CONFIRM if everything is correct and you want to generate the document
• Type EDIT if you want to make changes or add more information"""
        
        # Translate if needed
        if lang != "en":
            prompt = f"""Translate the following message to {lang}, maintaining the structure and formatting:

{confirmation_msg}

Return ONLY the translated message."""
            response = llm.invoke([HumanMessage(content=prompt)])
            confirmation_msg = response.content.strip()
        
        return {
            "generated_content": confirmation_msg,
            "next_step": "ask_confirmation",
            "stage": "confirmation",
            "asked_facts": asked_facts
        }
    
    # Conflict resolution
    if len(fact_conflicts) > 0:
        conflict_key = list(fact_conflicts.keys())[0]
        conflict_vals = fact_conflicts[conflict_key]
        
        question = f"I noticed conflicting information about {conflict_key.replace('_', ' ')}. You mentioned both '{conflict_vals[0]}' and '{conflict_vals[1]}'. Which one is correct?"
        
        if lang != "en":
            prompt = f"Translate to {lang}: {question}"
            response = llm.invoke([HumanMessage(content=prompt)])
            question = response.content.strip()
        
        return {
            "generated_content": question,
            "asked_facts": asked_facts
        }
    
    # Action Choice Generation
    if next_step == "ask_action_choice":
        facts = state.get("legal_facts", {})
        suggestions_prompt = f"""Based on the legal intent '{intent}' and the provided facts:
        1. Specifically suggest 2 to 4 distinct legal cases or actions the user can file for.
        2. Provide a short list of pros and cons for each.
        Format the output STRICTLY as a JSON array of objects, with NO markdown formatting:
        [
          {{"title": "Action Name", "pros": ["Pro 1"], "cons": ["Con 1"]}}
        ]
        Facts: {json.dumps(facts)}"""
        if lang != "en":
            suggestions_prompt += f"\nPlease translate the 'title', 'pros', and 'cons' strings to {lang}, but MUST keep the JSON array structure and keys 'title', 'pros', 'cons' exactly in English."
            
        response = llm.invoke([SystemMessage(content="Output valid JSON array only."), HumanMessage(content=suggestions_prompt)])
        content = response.content.strip()
        import re
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            content = match.group(0)
        else:
            content = content.replace("```json", "").replace("```", "").strip()
            
        return {
            "generated_content": f"ACTION_CHOICES:{content}",
            "next_step": "ask_action_choice",
            "stage": "action_choice",
            "asked_facts": asked_facts
        }
        
    # Action Confirmation stage
    if next_step == "ask_action_confirm":
        # The user has selected an action (intent)
        msg = f"You have selected: **{intent}**.\n\nAre you sure you want to proceed and generate the legal draft for this action?\n• Type CONFIRM to generate the document\n• Type EDIT to go back and choose a different action"
        
        # Translate if needed
        if lang != "en":
            prompt = f"Translate the following message to {lang}, maintaining the structure and formatting:\n\n{msg}\n\nReturn ONLY the translated message."
            response = llm.invoke([HumanMessage(content=prompt)])
            msg = response.content.strip()
            
        return {
            "generated_content": msg,
            "next_step": "ask_action_confirm",
            "stage": "action_confirm",
            "asked_facts": asked_facts
        }
    
    # STRUCTURED INTERVIEW - Ask specific questions based on what's missing
    # Use effective_missing which merges intent-required fields with state-missing fields
    missing_fields = effective_missing
    
    if missing_fields:
        # Choose the first missing field that hasn't been asked yet; 
        # if all have been asked cycle through to avoid infinite loop
        target_field = missing_fields[0]
        for field in missing_fields:
            if field not in asked_facts:
                target_field = field
                break
                
        asked_facts.append(target_field)
        
        # Format recent conversation history for context
        recent_msgs = messages[-4:] if len(messages) >= 4 else messages
        history_text = "\n".join([f"{'User' if m.type == 'human' else 'Assistant'}: {m.content}" for m in recent_msgs])
        
        # Human-readable field labels
        FIELD_LABELS = {
            "user_full_name": "your full legal name",
            "user_address": "your complete residential address",
            "user_phone": "your contact phone number",
            "state": "the state where the incident occurred",
            "district": "the district where the incident occurred",
            "incident_date": "the exact date the incident occurred",
            "incident_location": "the exact location/address of the incident",
            "incident_description": "a detailed description of what exactly happened",
            "counterparty_name": "the full name of the person/company responsible",
            "counterparty_address": "the address of the person/company responsible",
            "counterparty_role": "the role or relation of the accused (e.g. seller, employer, neighbor)",
            "stolen_items": "what exactly was stolen (item description, brand, model)",
            "financial_loss_value": "the total monetary loss in Indian Rupees (₹)",
            "payment_details": "details of any payment made (amount, date, mode, reference number)",
            "harm_description": "description of physical or psychological harm suffered",
            "product_name": "the name and model of the product/service involved",
            "defect_description": "description of the defect or service failure",
            "prior_complaints": "any prior complaints already filed for this issue",
            "witness_details": "names and contact details of any witnesses",
            "evidence_available": "what evidence you have (photos, receipts, messages, CCTV etc.)",
        }
        human_label = FIELD_LABELS.get(target_field, target_field.replace("_", " "))
        
        # Ask LLM to generate the next conversational question
        prompt = f"""
        You are Satta Vizhi, a free Indian legal guidance assistant.
        Your tone must be calm, respectful, clear, empathetic, and neutral.
        
        [CONTEXT]
        Legal Issue / Intent: {intent}
        We still need to know: '{human_label}' (internal key: {target_field})
        Language to respond in: {lang}
        
        [RECENT CONVERSATION]
        {history_text}
        
        [TASK]
        1. ONE QUESTION RULE: Ask exactly ONE natural, warm, conversational question to get '{human_label}'.
        2. Be specific — explain WHY this information is important for their legal document.
        3. DO NOT invent other questions. DO NOT ask for anything other than '{human_label}'.
        4. DO NOT use markdown. DO NOT wrap in quotes.
        5. If this is a sensitive field (like address or phone), reassure them their info is safe.
        
        Respond ONLY with the exact question text in {lang}.
        """
        
        response = llm.invoke([SystemMessage(content="You are a conversational legal question generator."), HumanMessage(content=prompt)])
        question_text = response.content.strip()
        
        return {
            "generated_content": question_text,
            "asked_facts": asked_facts
        }
    
    # All required fields answered — move to confirmation
    return {
        "generated_content": "Thank you for providing the information. Let me prepare a summary for your review.",
        "next_step": "ask_confirmation",
        "stage": "confirmation",
        "asked_facts": asked_facts
    }


def get_question_sequence(intent: str, answered_facts: dict, asked_facts: list) -> list:
    """
    Returns a prioritized list of questions to ask based on intent and what's already known.
    Each question is a dict with 'field' and 'question' keys.
    """
    
    # Define comprehensive question templates for different legal scenarios
    all_questions = {
        # PERSONAL DETAILS (Always needed)
        "user_full_name": {
            "question": "What is your full name as it should appear in the legal document?",
            "priority": 1
        },
        "user_address": {
            "question": "What is your complete residential address (including street, area, city, state, and PIN code)?",
            "priority": 1
        },
        "user_phone": {
            "question": "What is your contact phone number?",
            "priority": 1
        },
        "user_email": {
            "question": "What is your email address? (Optional, but recommended)",
            "priority": 2
        },
        
        # INCIDENT DETAILS (Core information)
        "state": {
            "question": "In which state did this incident occur?",
            "priority": 1
        },
        "district": {
            "question": "In which district did this incident occur?",
            "priority": 1
        },
        "incident_date": {
            "question": "When exactly did this incident occur? Please provide the date (and time if relevant).",
            "priority": 1
        },
        "incident_location": {
            "question": "Where did this incident take place? Please provide the complete address or location details.",
            "priority": 1
        },
        "incident_description": {
            "question": "Please describe what happened in detail. Include the sequence of events, what was said or done, and any relevant context.",
            "priority": 1
        },
        
        # PARTIES INVOLVED
        "counterparty_name": {
            "question": "Who is the other party involved in this matter? (Name of person, company, or organization)",
            "priority": 1
        },
        "counterparty_address": {
            "question": "What is the address of the other party? (If known)",
            "priority": 2
        },
        "counterparty_role": {
            "question": "What is the relationship or role of the other party? (e.g., landlord, employer, seller, service provider)",
            "priority": 2
        },
        
        # WITNESSES
        "witness_details": {
            "question": "Were there any witnesses to this incident? If yes, please provide their names and contact information.",
            "priority": 2
        },
        
        # FINANCIAL DETAILS
        "financial_loss_value": {
            "question": "What is the monetary value involved or lost in this matter? Please specify the exact amount in rupees.",
            "priority": 1
        },
        "payment_details": {
            "question": "How was the payment made? (e.g., cash, cheque, online transfer, UPI). Please provide transaction details if available.",
            "priority": 2
        },
        
        # EVIDENCE
        "evidence_available": {
            "question": "What evidence do you have to support your case? (e.g., receipts, contracts, emails, messages, photos, videos, documents)",
            "priority": 1
        },
        
        # PRIOR ACTIONS
        "prior_complaints": {
            "question": "Have you already filed any complaint or taken any action regarding this matter? If yes, please provide details.",
            "priority": 2
        },
        
        # HARM/IMPACT
        "harm_description": {
            "question": "How has this incident affected you? Please describe any physical, emotional, or financial impact.",
            "priority": 2
        },
        
        # SPECIFIC TO POLICE COMPLAINTS
        "stolen_items": {
            "question": "What items were stolen or lost? Please list them with approximate values.",
            "priority": 1,
            "applicable_for": ["theft", "robbery", "burglary", "police"]
        },
        "fir_station": {
            "question": "Which police station has jurisdiction over the area where the incident occurred?",
            "priority": 1,
            "applicable_for": ["theft", "robbery", "assault", "police"]
        },
        
        # SPECIFIC TO CONSUMER COMPLAINTS
        "product_name": {
            "question": "What is the name and model of the product or service in question?",
            "priority": 1,
            "applicable_for": ["consumer", "product", "service"]
        },
        "purchase_date": {
            "question": "When did you purchase this product or avail this service?",
            "priority": 1,
            "applicable_for": ["consumer", "product", "service"]
        },
        "defect_description": {
            "question": "What is the defect or problem with the product/service?",
            "priority": 1,
            "applicable_for": ["consumer", "product", "service", "defective"]
        },
        
        # SPECIFIC TO RTI
        "rti_department": {
            "question": "Which government department or public authority are you seeking information from?",
            "priority": 1,
            "applicable_for": ["rti", "information", "government"]
        },
        "information_sought": {
            "question": "What specific information are you requesting under the RTI Act?",
            "priority": 1,
            "applicable_for": ["rti", "information"]
        },
        
        # SPECIFIC TO LANDLORD/TENANT
        "property_address": {
            "question": "What is the complete address of the rental property?",
            "priority": 1,
            "applicable_for": ["rent", "landlord", "tenant", "eviction"]
        },
        "rent_amount": {
            "question": "What is the monthly rent amount?",
            "priority": 1,
            "applicable_for": ["rent", "landlord", "tenant"]
        },
        "deposit_amount": {
            "question": "What is the security deposit amount?",
            "priority": 1,
            "applicable_for": ["rent", "landlord", "tenant", "deposit"]
        },
        "lease_start_date": {
            "question": "When did the rental agreement start?",
            "priority": 2,
            "applicable_for": ["rent", "landlord", "tenant"]
        }
    }
    
    # Filter questions based on intent and what's already answered/asked
    intent_lower = intent.lower()
    applicable_questions = []
    
    for field, q_data in all_questions.items():
        # Skip if already answered or asked
        if field in answered_facts or field in asked_facts:
            continue
        
        # Check if question is applicable for this intent
        if "applicable_for" in q_data:
            if not any(keyword in intent_lower for keyword in q_data["applicable_for"]):
                continue
        
        applicable_questions.append({
            "field": field,
            "question": q_data["question"],
            "priority": q_data.get("priority", 3)
        })
    
    # Sort by priority (lower number = higher priority)
    applicable_questions.sort(key=lambda x: x["priority"])
    
    return applicable_questions


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
    
    # Generate final suggestions (maybe simpler since they already chose, but let's keep it minimal)
    suggestions_prompt = f"""Based on the legal intent '{intent}' and the provided facts:
    List 3 concrete next steps to proceed with this selected action.
    Make it concise, easy to read, and bulleted.
    Facts: {json.dumps(facts)}"""
    if lang != "en":
        suggestions_prompt += f"\nPlease translate the output to {lang}."
    suggestions_response = llm.invoke([HumanMessage(content=suggestions_prompt)])
    suggestions = suggestions_response.content.strip()
    
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

## Suggestions / Next Steps
{suggestions}

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
        "ask_confirmation": "generate_question",
        "ask_action_choice": "generate_question",
        "ask_action_confirm": "generate_question",  # ← NEW: second law-choice confirmation
        "refusal": "generate_question",
        "generate_document": "generate_document",
        "completed": "generate_document"
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
    current_input_hash = hashlib.md5(user_input.encode()).hexdigest()
    current_state = app.get_state(config).values
    last_processed_hash = current_state.get("last_input_hash", "")

    if last_processed_hash == current_input_hash:
        print(f"Idempotency: Skipping duplicate input for thread {thread_id}")
        generated_content = current_state.get("generated_content", "")
        facts = current_state.get("legal_facts", {})
        intent = current_state.get("intent", "")
        score = current_state.get("readiness_score", 0)
        next_step = current_state.get("next_step", "")
        stage = current_state.get("stage", "intake")
        checklist = current_state.get("checklist", {})
        bilingual_doc = current_state.get("bilingual_document")
        return _build_response(generated_content, facts, intent, score, next_step, stage, checklist, bilingual_doc)

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
    stage = final_state.get("stage", "intake")
    checklist = final_state.get("checklist", {})
    bilingual_doc = final_state.get("bilingual_document")
    return _build_response(generated_content, facts, intent, score, next_step, stage, checklist, bilingual_doc)


def _build_response(generated_content, facts, intent, score, next_step, stage, checklist, bilingual_doc):
    """Build the standardized API response for Stage 1-9 workflow."""
    readiness_status = "NOT_READY"
    if score >= 100:
        readiness_status = "LEGALLY_READY"
    elif score >= 80:
        readiness_status = "NEARLY_READY"
    elif score >= 50:
        readiness_status = "PARTIALLY_READY"

    suggested_sections = _get_suggested_sections(intent)
    filing_guidance = _get_filing_guidance(intent, facts)

    response = {
        "content": generated_content,
        "entities": facts,
        "intent": intent,
        "readiness_score": score,
        "readiness_status": readiness_status,
        "is_document": next_step in ["generate_document", "completed"] or stage == "completed",
        "is_confirmation": next_step == "ask_confirmation",
        "is_action_choice": next_step == "ask_action_choice",
        "current_stage": stage,
        "checklist": checklist,
        "suggested_sections": suggested_sections,
        "filing_guidance": filing_guidance
    }

    if bilingual_doc:
        response["bilingual_document"] = bilingual_doc

    return response


def _get_suggested_sections(intent: str) -> str:
    """Return relevant Indian legal sections based on detected intent."""
    if not intent or intent == "SAFETY_REFUSAL":
        return ""
    intent_lower = intent.lower()
    sections = []
    if any(t in intent_lower for t in ["theft", "stolen", "robbery", "burglary"]):
        sections = ["Section 378 IPC (Theft)", "Section 379 IPC (Punishment)", "Section 380 IPC (Theft in dwelling)"]
    elif any(t in intent_lower for t in ["cheating", "fraud"]):
        sections = ["Section 415 IPC (Cheating)", "Section 420 IPC (Inducing dishonestly)", "Section 406 IPC (Criminal breach of trust)"]
    elif any(t in intent_lower for t in ["assault", "attack", "hurt"]):
        sections = ["Section 319 IPC (Hurt)", "Section 320 IPC (Grievous hurt)", "Section 323 IPC (Voluntarily causing hurt)"]
    elif any(t in intent_lower for t in ["consumer", "product", "service", "refund", "defective"]):
        sections = ["Consumer Protection Act 2019 – Section 2(7)", "Consumer Protection Act 2019 – Section 35", "Section 420 IPC (Cheating)"]
    elif any(t in intent_lower for t in ["cybercrime", "online", "hacking", "phishing"]):
        sections = ["IT Act 2000 – Section 66 (Computer related offences)", "IT Act 2000 – Section 66C (Identity theft)", "IT Act 2000 – Section 66D (Cheating by personation)"]
    elif any(t in intent_lower for t in ["property", "land", "real estate"]):
        sections = ["Transfer of Property Act 1882", "Section 420 IPC (Cheating)", "Section 447 IPC (Criminal trespass)"]
    elif any(t in intent_lower for t in ["domestic", "violence", "dowry"]):
        sections = ["Protection of Women from Domestic Violence Act 2005", "Section 498A IPC (Cruelty by husband)", "Section 304B IPC (Dowry death)"]
    elif any(t in intent_lower for t in ["motor", "accident", "vehicle"]):
        sections = ["Motor Vehicles Act 1988 – Section 166", "Section 304A IPC (Death by negligence)"]
    elif any(t in intent_lower for t in ["employment", "salary", "wages"]):
        sections = ["Payment of Wages Act 1936", "Industrial Disputes Act 1947", "Minimum Wages Act 1948"]
    elif any(t in intent_lower for t in ["defamation", "slander"]):
        sections = ["Section 499 IPC (Defamation)", "Section 500 IPC (Punishment for defamation)"]
    if sections:
        return " | ".join(sections[:3])
    return ""


def _get_filing_guidance(intent: str, facts: dict) -> dict:
    """Return filing authority, enclosures, and next steps based on intent."""
    if not intent:
        return {}
    intent_lower = intent.lower()
    state = facts.get("state", "your state")
    district = facts.get("district", "your district")
    guidance = {
        "authority": "",
        "jurisdiction_hint": f"{district}, {state}",
        "enclosures": [],
        "next_steps": []
    }
    if any(t in intent_lower for t in ["theft", "assault", "robbery", "cheating", "cybercrime"]):
        guidance["authority"] = f"Police Station, {district} (Cyber Crime Cell for online offences)"
        guidance["enclosures"] = ["Government ID proof", "Evidence documents", "Witness details", "FIR draft"]
        guidance["next_steps"] = ["Visit nearest police station", "File an FIR", "Collect FIR receipt", "Contact a lawyer if FIR refused"]
    elif any(t in intent_lower for t in ["consumer", "product", "service", "refund"]):
        guidance["authority"] = f"District Consumer Disputes Redressal Commission, {district}"
        guidance["enclosures"] = ["Original bills/receipts", "Product photos", "Warranty card", "Communication with seller", "ID proof"]
        guidance["next_steps"] = ["File complaint at Consumer Commission", "Attach all bills and evidence", "Pay nominal court fee", "Attend hearing"]
    elif any(t in intent_lower for t in ["motor", "accident", "vehicle"]):
        guidance["authority"] = f"Motor Accident Claims Tribunal (MACT), {district}"
        guidance["enclosures"] = ["FIR copy", "Medical reports", "Vehicle documents", "Insurance papers"]
        guidance["next_steps"] = ["File FIR at police station", "Get medical certificate", "Contact insurance company", "File MACT claim within 2 years"]
    elif any(t in intent_lower for t in ["domestic", "violence", "dowry"]):
        guidance["authority"] = f"Protection Officer / Magistrate Court, {district}"
        guidance["enclosures"] = ["ID proof", "Marriage certificate", "Medical reports", "Evidence"]
        guidance["next_steps"] = ["Contact Protection Officer under PWDVA", "File complaint at Magistrate Court", "Seek immediate protection order", "Contact legal aid services"]
    else:
        guidance["authority"] = f"Civil Court / Magistrate Court, {district}"
        guidance["enclosures"] = ["All relevant documents", "ID proof", "Evidence"]
        guidance["next_steps"] = ["Consult a local lawyer", "Draft legal notice", "File complaint at appropriate authority"]
    return guidance
