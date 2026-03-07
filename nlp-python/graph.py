import os
import json
import hashlib
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from llm_provider import llm
from bilingual_generator import generate_bilingual_document

# ============================================================
# STATE
# ============================================================

class LegalState(TypedDict):
    messages:             Annotated[List[BaseMessage], add_messages]
    thread_id:            str
    primary_language:     str
    collected_facts:      Dict[str, Any]
    required_keys:        List[str]      # ordered interview queue
    answered_keys:        List[str]      # keys that have been asked AND answered
    current_question_key: str            # key we are currently waiting answer for
    stage:                str            # collecting | confirming | done
    next_step:            str
    intent:               str
    turn_count:           int
    generated_content:    str
    readiness_score:      int
    last_input_hash:      str


# ============================================================
# INTERVIEW PLAN
# Each case type maps to an ORDERED list of keys to ask.
# The assistant will ask exactly one key per turn in this order.
# ============================================================

BASE_KEYS = [
    "incident_description",   # confirm/expand the problem
    "incident_date",          # when did it happen
    "counterparty_name",      # who is the other party
    "evidence_available",     # what evidence do they have
    "user_full_name",         # complainant personal details
    "user_city_state",
    "user_phone",
]

EXTRA_KEYS_BY_INTENT = {
    "cyber_fraud":       ["financial_loss_value", "counterparty_upi_or_id", "counterparty_platform", "payment_date"],
    "online_fraud":      ["financial_loss_value", "counterparty_upi_or_id", "counterparty_platform", "payment_date"],
    "consumer":          ["product_name", "defect_description"],
    "consumer_complaint":["product_name", "defect_description"],
    "theft":             ["stolen_items", "witness_details"],
    "assault":           ["witness_details", "harm_description"],
    "harassment":        ["witness_details", "harm_description"],
    "rti":               ["rti_department", "information_sought"],
    "rent":              ["property_address", "rent_amount", "deposit_amount"],
    "landlord":          ["property_address", "rent_amount", "deposit_amount"],
}

def build_required_keys(intent: str) -> List[str]:
    """Return the ordered interview queue for this intent."""
    keys = list(BASE_KEYS)  # copy
    intent_lower = intent.lower()
    for keyword, extras in EXTRA_KEYS_BY_INTENT.items():
        if keyword in intent_lower:
            for k in extras:
                if k not in keys:
                    # Insert case-specific keys BEFORE the personal detail block
                    personal_idx = keys.index("user_full_name") if "user_full_name" in keys else len(keys)
                    keys.insert(personal_idx, k)
            break
    return keys


# ============================================================
# HELPERS
# ============================================================

SKIP_VALUES = {"", "null", "unknown", "not_available", "none", "n/a"}

def is_real_value(v) -> bool:
    return v is not None and str(v).strip().lower() not in SKIP_VALUES

KEY_LABELS = {
    "user_full_name":        "Complainant Name",
    "user_address":          "Address",
    "user_city_state":       "City / State",
    "user_phone":            "Phone Number",
    "user_email":            "Email",
    "incident_date":         "Date of Incident",
    "incident_location":     "Location",
    "incident_description":  "Description of Incident",
    "counterparty_name":     "Other Party Name",
    "counterparty_upi_or_id":"UPI ID / Account",
    "counterparty_platform": "Platform / Channel",
    "counterparty_role":     "Other Party Role",
    "counterparty_address":  "Other Party Address",
    "financial_loss_value":  "Amount Involved / Lost",
    "payment_method":        "Payment Method",
    "payment_date":          "Payment Date",
    "payment_reference":     "Payment Reference",
    "evidence_available":    "Evidence Available",
    "product_name":          "Product / Service",
    "defect_description":    "Defect / Problem",
    "stolen_items":          "Stolen / Missing Items",
    "witness_details":       "Witnesses",
    "harm_description":      "Impact / Harm",
    "prior_complaints":      "Previous Actions Taken",
    "rti_department":        "Government Department",
    "information_sought":    "Information Requested",
    "property_address":      "Property Address",
    "rent_amount":           "Monthly Rent",
    "deposit_amount":        "Security Deposit",
}

def label(key: str) -> str:
    return KEY_LABELS.get(key, key.replace("_", " ").title())


# ============================================================
# NODE 1 — DETECT LANGUAGE (locked on first message)
# ============================================================

def detect_language_node(state: LegalState):
    if state.get("primary_language"):
        return {}   # already set, do nothing

    messages = state.get("messages", [])
    if not messages:
        return {"primary_language": "en"}

    last_msg = messages[-1].content
    prompt = (
        'Detect the ISO 639-1 language code of the text below.\n'
        'Return ONLY the 2-letter code. Valid values: en ta hi te kn ml mr bn gu\n\n'
        f'Text: "{last_msg}"'
    )
    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        lang = resp.content.strip().lower()[:2]
        if lang not in {"en", "ta", "hi", "te", "kn", "ml", "mr", "bn", "gu"}:
            lang = "en"
    except Exception:
        lang = "en"

    return {"primary_language": lang}


# ============================================================
# NODE 2 — CLASSIFY INTENT (only on turn 1)
# ============================================================

def classify_intent_node(state: LegalState):
    """
    On the very first user message: extract intent and build the interview queue.
    On subsequent turns: just extract the answer to the current question.
    """
    messages        = state.get("messages", [])
    collected_facts = dict(state.get("collected_facts") or {})
    required_keys   = list(state.get("required_keys") or [])
    answered_keys   = list(state.get("answered_keys") or [])
    current_q_key   = state.get("current_question_key", "")
    stage           = state.get("stage", "collecting")
    turn_count      = (state.get("turn_count") or 0) + 1
    lang            = state.get("primary_language", "en")

    last_user_msg = messages[-1].content.strip() if messages else ""

    # ── CONFIRMATION STAGE: just check yes/no ──────────────────────────────
    if stage == "confirming":
        upper = last_user_msg.upper()
        confirmed   = any(p in upper for p in ["YES, THE ABOVE", "YES THE ABOVE", "CONFIRM", "YES I CONFIRM"])
        # Also accept plain "yes" only if it's a short message (avoids matching "yes but...")
        if not confirmed and upper.strip() in {"YES", "YES.", "YES!"}:
            confirmed = True
        wants_edit  = any(p in upper for p in ["NO,", "NO I", "CHANGE", "EDIT", "WRONG", "INCORRECT", "NOT CORRECT", "WANT TO MAKE"])

        if confirmed:
            return {"stage": "done", "next_step": "generate_document",
                    "turn_count": turn_count, "collected_facts": collected_facts,
                    "required_keys": required_keys, "answered_keys": answered_keys}
        elif wants_edit:
            return {"stage": "collecting", "next_step": "ask_question",
                    "turn_count": turn_count, "collected_facts": collected_facts,
                    "required_keys": required_keys, "answered_keys": answered_keys}
        else:
            return {"stage": "confirming", "next_step": "ask_confirmation",
                    "turn_count": turn_count, "collected_facts": collected_facts,
                    "required_keys": required_keys, "answered_keys": answered_keys}

    # ── TURN 1: Classify intent, build interview queue ─────────────────────
    if turn_count == 1:
        prompt = f"""You are a legal issue classifier for India.

Read the user's message and return JSON with:
1. "intent" — a SHORT description of the legal issue type (e.g. "cyber fraud", "workplace harassment",
   "consumer complaint", "RTI petition", "theft", "assault", "rent dispute", "cheating", etc.)
2. "safety_status" — "SAFE" unless there is an ACTIVE IMMEDIATE threat to life RIGHT NOW (not past events)
3. "initial_facts" — a dict of facts EXPLICITLY mentioned in this message ONLY
   (e.g. product price, platform used, amount paid — but NEVER name, phone, city unless literally written)

STRICT: Do not extract user_full_name, user_phone, user_city_state, user_email from the opening message
unless the user literally wrote those details. They are describing a problem, not introducing themselves.

User message:
"{last_user_msg}"

Return valid JSON only. No markdown.
{{
  "intent": "...",
  "safety_status": "SAFE",
  "initial_facts": {{}}
}}
"""
        try:
            resp = llm.invoke([
                SystemMessage(content="Legal classifier. Output valid JSON only."),
                HumanMessage(content=prompt)
            ])
            raw = resp.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(raw)
        except Exception as e:
            print(f"[classify] parse error: {e}")
            data = {"intent": "legal complaint", "safety_status": "SAFE", "initial_facts": {}}

        if data.get("safety_status") == "UNSAFE":
            return {"stage": "done", "next_step": "refusal", "turn_count": turn_count,
                    "intent": "SAFETY_REFUSAL", "collected_facts": collected_facts,
                    "required_keys": [], "answered_keys": []}

        intent = data.get("intent", "legal complaint")

        # Build the ordered interview queue
        new_req_keys = build_required_keys(intent)

        # Merge any initial facts — but skip personal keys from turn 1
        NEVER_FROM_TURN1 = {"user_full_name", "user_phone", "user_city_state", "user_email", "user_address"}
        init_facts = {k: v for k, v in (data.get("initial_facts") or {}).items()
                      if k not in NEVER_FROM_TURN1 and is_real_value(v)}
        collected_facts.update(init_facts)

        # Mark facts already extracted as answered
        new_answered = [k for k in init_facts if k in new_req_keys]

        return {
            "intent":               intent,
            "collected_facts":      collected_facts,
            "required_keys":        new_req_keys,
            "answered_keys":        new_answered,
            "stage":                "collecting",
            "next_step":            "ask_question",
            "turn_count":           turn_count,
            "readiness_score":      0,
            "current_question_key": "",
        }

    # ── SUBSEQUENT TURNS: Extract answer to current_question_key ──────────
    if not current_q_key:
        # Safety — shouldn't happen but handle gracefully
        return {"next_step": "ask_question", "stage": "collecting",
                "turn_count": turn_count, "collected_facts": collected_facts,
                "required_keys": required_keys, "answered_keys": answered_keys}

    history = "\n".join([
        f"{'User' if m.type == 'human' else 'Assistant'}: {m.content}"
        for m in messages
    ])

    extract_prompt = f"""You are a fact extraction engine for a legal assistant.

The assistant just asked the user about: "{current_q_key}" ({label(current_q_key)})
The user's reply was: "{last_user_msg}"

Extract the value for "{current_q_key}" from the user's reply.

Rules:
- Extract ONLY what the user explicitly stated.
- If the user said "no", "none", "I don't know", "not available" — value is "Not available".
- Do NOT infer or fabricate. If unclear, value is "Not available".
- You may ALSO extract other clearly stated facts if the user volunteered them.
  But do NOT extract user_full_name, user_phone, user_city_state from casual mentions.

Context (recent conversation):
{history[-2000:]}

Return valid JSON only:
{{
  "extracted": {{
    "{current_q_key}": "value here"
  }}
}}
"""
    try:
        resp = llm.invoke([
            SystemMessage(content="Fact extractor. JSON only. No markdown."),
            HumanMessage(content=extract_prompt)
        ])
        raw = resp.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        extracted = data.get("extracted", {})
    except Exception as e:
        print(f"[extract] parse error: {e}")
        extracted = {current_q_key: last_user_msg[:200]}  # fallback: store raw answer

    # Merge extracted facts
    for k, v in extracted.items():
        if is_real_value(v):
            collected_facts[k] = v

    # Mark current key as answered (always — even if "Not available")
    if current_q_key not in answered_keys:
        answered_keys.append(current_q_key)
    for k in extracted:
        if k in required_keys and k not in answered_keys:
            answered_keys.append(k)

    # Determine next step
    missing = [k for k in required_keys if k not in answered_keys]

    # Readiness score
    total    = len(required_keys)
    have     = total - len(missing)
    readiness = int((have / total) * 100) if total > 0 else 0

    if not missing:
        next_step = "ask_confirmation"
        new_stage = "confirming"
    else:
        next_step = "ask_question"
        new_stage = "collecting"

    return {
        "collected_facts": collected_facts,
        "answered_keys":   answered_keys,
        "required_keys":   required_keys,
        "next_step":       next_step,
        "stage":           new_stage,
        "readiness_score": readiness,
        "turn_count":      turn_count,
    }


# ============================================================
# NODE 3 — RESPOND
# ============================================================

def respond_node(state: LegalState):
    next_step       = state.get("next_step", "ask_question")
    lang            = state.get("primary_language", "en")
    intent          = state.get("intent", "legal issue")
    collected_facts = state.get("collected_facts", {})
    required_keys   = state.get("required_keys", [])
    answered_keys   = state.get("answered_keys", [])
    turn_count      = state.get("turn_count", 1)
    messages        = state.get("messages", [])

    # ── SAFETY REFUSAL ─────────────────────────────────────────────────────
    if next_step == "refusal":
        return {"generated_content": (
            "I am unable to assist with this request through this platform. "
            "If you are in immediate danger, please call 100 (Police) or 112 (Emergency) immediately. "
            "Satta Vizhi is designed for legal documentation assistance only."
        )}

    # ── CONFIRMATION SUMMARY ───────────────────────────────────────────────
    if next_step == "ask_confirmation":
        real_facts = {k: v for k, v in collected_facts.items() if is_real_value(v)
                      and str(v).strip().lower() not in {"not available", "not applicable"}}

        # Build summary text
        summary_lines = []
        for k in required_keys:
            v = collected_facts.get(k)
            if is_real_value(v) and str(v).strip().lower() not in {"not available", "not applicable"}:
                summary_lines.append(f"{label(k)}: {v}")
        # Add any extra facts collected
        for k, v in collected_facts.items():
            if k not in required_keys and is_real_value(v) and str(v).strip().lower() not in {"not available", "not applicable"}:
                summary_lines.append(f"{label(k)}: {v}")

        summary_text = "\n".join(summary_lines) if summary_lines else "(No details collected yet.)"
        q_number = len(answered_keys) + 1

        prompt = f"""You are 'Satta Vizhi', a warm and professional Indian legal document assistant.
You are NOT a lawyer. You never give legal advice.

Write a confirmation message in {lang} language.

The message must:
1. Thank the user warmly for their patience and cooperation (1 sentence).
2. Say "Here is a summary of the information I have collected:"
3. Present each item as a clean numbered list — no markdown, no asterisks, no bold:
   1. Label: Value
   2. Label: Value
   etc.

The items to include (translate labels to {lang} if not English):
{summary_text}

4. Ask the user to review each item carefully.
5. End with this EXACT instruction (translate to {lang}):
   To confirm everything is correct, please reply:
   "Yes, the above information is correct."
   If anything needs to be changed, please tell me what to correct.

CRITICAL RULES:
- Do NOT use markdown. No **, no *, no #, no backticks.
- Use plain numbered list only. Clean line breaks between items.
- Keep the tone warm but concise.
- Return the message text ONLY in {lang}.
"""
        resp = llm.invoke([HumanMessage(content=prompt)])
        # Strip any accidental markdown the LLM produces
        content = resp.content.strip()
        content = content.replace("**", "").replace("__", "")
        return {"generated_content": content}

    # ── ASK NEXT QUESTION ──────────────────────────────────────────────────
    missing      = [k for k in required_keys if k not in answered_keys]
    target_key   = missing[0] if missing else None

    if not target_key:
        # All keys answered — move to confirmation
        return {
            "generated_content": "Thank you for all the details. Let me now prepare a summary for your review.",
            "next_step": "ask_confirmation",
            "stage":     "confirming",
        }

    # Count how many questions have been asked so far
    q_number = len(answered_keys) + 1

    # Recent history for context
    recent       = messages[-6:] if len(messages) >= 6 else messages
    history_text = "\n".join([
        f"{'User' if m.type == 'human' else 'Assistant'}: {m.content}"
        for m in recent
    ])

    # On question 1, acknowledge the issue type
    opening_hint = ""
    if turn_count == 1:
        opening_hint = (
            f'Start by briefly acknowledging the legal issue in 1 sentence using cautious language '
            f'(e.g. "Situations like this may relate to [area], which is commonly addressed under '
            f'[law/authority] in India."). Then ask the question.\n'
        )

    # On questions 2+, acknowledge the previous answer
    acknowledge_hint = ""
    if turn_count > 1 and answered_keys:
        last_key = answered_keys[-1] if answered_keys else ""
        last_val = collected_facts.get(last_key, "")
        if last_key and is_real_value(last_val):
            acknowledge_hint = (
                f'Start with a brief acknowledgment of the previous answer '
                f'(e.g. "Thank you, I have noted that."). Then ask the question.\n'
            )

    prompt = f"""You are 'Satta Vizhi', a warm, empathetic Indian legal document assistant.
You are NOT a lawyer. You NEVER give legal advice. You collect facts to help draft documents.

[LEGAL ISSUE]
{intent}

[FACTS COLLECTED SO FAR]
{json.dumps({k: v for k, v in collected_facts.items() if is_real_value(v)}, ensure_ascii=False, indent=2)}

[RECENT CONVERSATION]
{history_text}

{opening_hint}{acknowledge_hint}

[YOUR TASK]
Ask question number {q_number} to collect the information for: "{target_key}" ({label(target_key)})

STRICT RULES:
- Ask ONLY about "{target_key}" — ONE question, nothing else.
- Do NOT ask about anything already collected.
- Do NOT bundle multiple questions.
- Be empathetic and clear — users may be stressed.
- Respond ONLY in {lang}. Do not mix languages.
- Do NOT use markdown, asterisks, bullet points, or hashtags. Plain text only.
- Return ONLY: [optional 1-line acknowledgment] + [the single question]
"""

    resp = llm.invoke([
        SystemMessage(content="Legal intake assistant. One question per turn. Plain text. No markdown."),
        HumanMessage(content=prompt)
    ])

    return {
        "generated_content":    resp.content.strip(),
        "current_question_key": target_key,
    }


# ============================================================
# NODE 4 — GENERATE DOCUMENT
# ============================================================

def generate_document_node(state: LegalState):
    facts  = state.get("collected_facts", {})
    intent = state.get("intent", "Legal Issue")
    lang   = state.get("primary_language", "en")

    result = generate_bilingual_document(intent, facts, lang)

    payload = json.dumps({
        "document_type":         result["document_type"],
        "user_language":         lang,
        "readiness_score":       result["readiness_score"],
        "user_language_content": result["user_language_content"],
        "english_content":       result["english_content"],
        "disclaimer_en":         result["disclaimer_en"],
        "disclaimer_user_lang":  result["disclaimer_user_lang"],
    }, ensure_ascii=False)

    return {
        "generated_content": f"DOCUMENT_READY\n{payload}",
        "readiness_score":   result["readiness_score"],
        "stage":             "done",
    }


# ============================================================
# ROUTING
# ============================================================

def route_after_classify(state: LegalState):
    step = state.get("next_step", "ask_question")
    if step == "generate_document": return "generate_document"
    if step == "ask_confirmation":  return "respond"
    if step == "refusal":           return "respond"
    return "respond"   # ask_question


# ============================================================
# GRAPH
# ============================================================

workflow = StateGraph(LegalState)
workflow.add_node("detect_language",   detect_language_node)
workflow.add_node("classify_intent",   classify_intent_node)
workflow.add_node("respond",           respond_node)
workflow.add_node("generate_document", generate_document_node)

workflow.set_entry_point("detect_language")
workflow.add_edge("detect_language",   "classify_intent")
workflow.add_conditional_edges("classify_intent", route_after_classify, {
    "respond":           "respond",
    "generate_document": "generate_document",
})
workflow.add_edge("respond",           END)
workflow.add_edge("generate_document", END)


# ============================================================
# PERSISTENCE
# ============================================================

from langgraph.checkpoint.memory import MemorySaver
try:
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool

    raw_db_url = os.getenv("DB_URL", "postgresql://postgres:1234@localhost:5432/legal_db")
    DB_URL     = raw_db_url.replace("jdbc:", "", 1) if raw_db_url.startswith("jdbc:") else raw_db_url

    with ConnectionPool(conninfo=DB_URL, min_size=1, max_size=1, kwargs={"autocommit": True}) as p:
        PostgresSaver(p).setup()

    pool         = ConnectionPool(conninfo=DB_URL, max_size=20)
    checkpointer = PostgresSaver(pool)
    print("[Satta Vizhi] ✓ Postgres checkpointer connected.")
except Exception as e:
    print(f"[Satta Vizhi] Using in-memory checkpointer. ({e})")
    checkpointer = MemorySaver()

graph_app = workflow.compile(checkpointer=checkpointer)


# ============================================================
# PUBLIC ENTRY POINT
# ============================================================

def process_message(thread_id: str, user_input: str) -> dict:
    if not user_input or not user_input.strip():
        return {
            "content": (
                "Vanakkam! I am Satta Vizhi, your legal document assistant. "
                "I am not a lawyer and I do not provide legal advice. "
                "Please describe your legal issue and I will help you prepare the necessary documents."
            ),
            "entities": {}, "intent": "", "readiness_score": 0,
            "is_document": False, "is_confirmation": False,
        }

    config     = {"configurable": {"thread_id": thread_id}}
    input_hash = hashlib.md5(user_input.encode()).hexdigest()

    current_state = graph_app.get_state(config).values
    if current_state.get("last_input_hash") == input_hash:
        print(f"[Satta Vizhi] Idempotency hit for thread {thread_id}")
        return _build_response(current_state)

    graph_app.invoke(
        {"messages": [HumanMessage(content=user_input)], "last_input_hash": input_hash},
        config=config,
    )

    return _build_response(graph_app.get_state(config).values)


def _build_response(state: dict) -> dict:
    content   = state.get("generated_content", "")
    is_doc    = content.startswith("DOCUMENT_READY")
    next_step = state.get("next_step", "")
    return {
        "content":         content,
        "entities":        state.get("collected_facts", {}),
        "intent":          state.get("intent", ""),
        "readiness_score": state.get("readiness_score", 0),
        "is_document":     is_doc,
        "is_confirmation": (next_step == "ask_confirmation"),
    }
