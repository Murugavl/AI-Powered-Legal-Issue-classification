"""
graph.py — AI Legal Document Preparation Assistant

Flow:
  Turn 1  : Classify issue → generate a CASE-SPECIFIC interview plan (LLM)
  Turn 2+ : Extract answer to current question → advance plan
  Final   : Confirmation summary → document generation
"""

import os
import re
import json
import hashlib
from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from llm_provider import llm
from bilingual_generator import generate_bilingual_document


# ============================================================
# GREETING
# ============================================================

GREETING = (
    "Vanakkam! I am your AI Legal Document Assistant.\n"
    "I am not a lawyer and I do not provide legal advice.\n"
    "I can help you prepare a document based on the information you provide.\n\n"
    "Please describe your issue briefly."
)


# ============================================================
# STATE
# ============================================================

class LegalState(TypedDict):
    messages:               Annotated[List[BaseMessage], add_messages]
    thread_id:              str
    primary_language:       str
    collected_facts:        Dict[str, Any]
    interview_plan:         List[Dict]     # [{key, label, question, show_example}]
    answered_keys:          List[str]
    current_question_key:   str
    stage:                  str            # collecting | confirming | done
    next_step:              str
    intent:                 str
    category:               str
    turn_count:             int
    generated_content:      str
    readiness_score:        int
    last_input_hash:        str
    classification_shown:   bool


# ============================================================
# HELPERS
# ============================================================

SKIP_VALUES = {"", "null", "unknown", "not_available", "none", "n/a", "na",
               "not available", "not applicable", "not provided"}


def is_real_value(v) -> bool:
    if v is None:
        return False
    return str(v).strip().lower() not in SKIP_VALUES and len(str(v).strip()) > 0


def strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__',     r'\1', text)
    text = re.sub(r'#{1,6}\s+',     '',    text)
    return text.replace("```", "").strip()


def parse_llm_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```\s*$',       '', raw, flags=re.MULTILINE)
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


def is_final_confirmation(text: str) -> bool:
    upper    = text.strip().upper().rstrip(".!? ")
    stripped = upper.replace("THE ", "").replace(", ", " ").replace("THAT IS ", "").strip()
    return (
        upper in {
            "YES", "OK", "OKAY", "CORRECT", "CONFIRMED", "SURE", "YEP", "YA", "HAAN",
            "LOOKS GOOD", "THATS CORRECT", "YES IT IS", "YES CORRECT",
            "AAMAM", "SARI", "PROCEED", "GENERATE",
        }
        or any(p in stripped for p in [
            "YES ABOVE", "YES I CONFIRM", "EVERYTHING IS CORRECT", "ALL CORRECT",
            "INFORMATION IS CORRECT", "INFORMATION ARE CORRECT",
            "ABOVE INFORMATION", "DETAILS ARE CORRECT", "DATA IS CORRECT",
            "CORRECT PROCEED",
        ])
        or upper.startswith("YES")
    )


def is_edit_request(text: str) -> bool:
    upper = text.strip().upper()
    return any(p in upper for p in [
        "NO,", "NO ", "CHANGE", "EDIT", "WRONG", "INCORRECT", "NOT CORRECT",
        "WANT TO MAKE", "PLEASE CHANGE", "SOMETHING IS WRONG", "MODIFY",
    ])


# ── Questions that benefit from an example hint ─────────────────────────────
# These are address/location type questions where an example clarifies format.
EXAMPLE_HINTS = {
    "user_full_address":        "(e.g., 12, Anna Nagar 2nd Street, Chennai)",
    "incident_location":        "(e.g., 45 Mount Road, Teynampet, Chennai)",
    "office_location":          "(e.g., 45 Mount Road, Teynampet, Chennai)",
    "location_details":         "(e.g., Near XYZ Junction, Coimbatore)",
    "property_address":         "(e.g., Plot 5, Gandhi Street, Madurai)",
    "user_city_state":          "(e.g., Anna Nagar, Chennai, Tamil Nadu)",
    "complainant_address":      "(e.g., 12, Anna Nagar 2nd Street, Chennai, Tamil Nadu)",
    "product_purchase_location":"(e.g., XYZ Electronics, Anna Nagar, Chennai)",
    "bank_branch_address":      "(e.g., SBI, T. Nagar Branch, Chennai)",
}

# Personal keys — appended at END of every plan, in this fixed order
PERSONAL_KEYS = [
    {
        "key":      "user_full_name",
        "label":    "Your Full Name",
        "question": "What is your full name?",
    },
    {
        "key":      "user_full_address",
        "label":    "Your Full Residential Address",
        "question": "What is your full residential address?",
        # hint appended dynamically from EXAMPLE_HINTS
    },
    {
        "key":      "user_phone",
        "label":    "Your Phone Number",
        "question": "What is your phone number?",
    },
]
PERSONAL_KEY_SET = {s["key"] for s in PERSONAL_KEYS}


# ============================================================
# NODE 1 — DETECT LANGUAGE
# ============================================================

def detect_language_node(state: LegalState):
    if state.get("primary_language"):
        return {}
    messages = state.get("messages", [])
    if not messages:
        return {"primary_language": "en"}
    last_msg = messages[-1].content
    prompt = (
        "Detect the ISO 639-1 language code of this text.\n"
        "Return ONLY the 2-letter code. Valid: en ta hi te kn ml mr bn gu\n\n"
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
# NODE 2 — CLASSIFY + PLAN + EXTRACT
# ============================================================

def classify_and_plan_node(state: LegalState):
    messages        = state.get("messages", [])
    collected_facts = dict(state.get("collected_facts") or {})
    interview_plan  = list(state.get("interview_plan") or [])
    answered_keys   = list(state.get("answered_keys") or [])
    current_q_key   = state.get("current_question_key", "")
    stage           = state.get("stage", "collecting")
    turn_count      = (state.get("turn_count") or 0) + 1
    last_user_msg   = messages[-1].content.strip() if messages else ""
    lower_msg       = last_user_msg.lower()

    # ── Evidence upload ───────────────────────────────────────────────────
    if lower_msg.startswith("i have uploaded evidence:"):
        filename = last_user_msg.split(":", 1)[1].strip() if ":" in last_user_msg else "evidence file"
        existing = str(collected_facts.get("evidence_available", "")).strip()
        note     = f"Uploaded file: {filename}"
        collected_facts["evidence_available"] = (
            f"{existing}; {note}" if is_real_value(existing) else note
        )
        if "evidence_available" not in answered_keys:
            answered_keys.append("evidence_available")
        missing = [s for s in interview_plan if s["key"] not in answered_keys]
        return {
            "collected_facts": collected_facts, "answered_keys": answered_keys,
            "next_step": "ask_confirmation" if not missing else "ask_question",
            "stage":     "confirming"       if not missing else "collecting",
            "turn_count": turn_count, "current_question_key": current_q_key,
        }

    # ── CONFIRMING STAGE ─────────────────────────────────────────────────
    if stage == "confirming":
        if is_final_confirmation(last_user_msg):
            return {
                "stage": "done", "next_step": "generate_document",
                "turn_count": turn_count, "collected_facts": collected_facts,
                "interview_plan": interview_plan, "answered_keys": answered_keys,
            }
        elif is_edit_request(last_user_msg):
            return {
                "stage": "collecting", "next_step": "ask_question",
                "turn_count": turn_count, "collected_facts": collected_facts,
                "interview_plan": interview_plan, "answered_keys": answered_keys,
            }
        else:
            return {
                "stage": "confirming", "next_step": "ask_confirmation",
                "turn_count": turn_count, "collected_facts": collected_facts,
                "interview_plan": interview_plan, "answered_keys": answered_keys,
            }

    # ── TURN 1: Classify + generate interview plan ────────────────────────
    if turn_count == 1:
        prompt = f"""You are an Indian legal document intake assistant.
A user described their legal problem. Do the following:

1. Classify into ONE of:
   Theft / Robbery | Assault | Cyber crime | Consumer complaint |
   Salary / Employment dispute | Property dispute | Harassment / Threat |
   Cheating / Fraud | Family / Matrimonial | Banking issue |
   RTI Application | Insurance dispute | Other civil complaint

2. Safety routing:
   - "refuse"             → immediate life threat or illegal/unethical request
   - "refer_professional" → outside India, serious criminal liability, complex litigation
   - "allow"              → normal document preparation

3. Design a CASE-SPECIFIC interview plan — 4 to 7 questions for THIS exact problem.
   RULES:
   - THEFT / ROBBERY: what was stolen (make/model/reg if vehicle), date+time (combined one question),
     exact location, how discovered, cards/IDs stolen, any reporting already done.
   - CYBER CRIME: transaction date+time (one question), amount, card/account type,
     how fraud occurred, digital evidence available.
   - CONSUMER: product/service name, purchase date, exact defect, seller name, refund attempt.
   - EMPLOYMENT: employer name, issue type, dates, HR escalation, any written proof.
   - PROPERTY/RENT: property address, landlord name, specific dispute, rent amount.
   - COMBINE paired facts into ONE question (e.g. date + time → one key).
   - NEVER ask: suspect description, CCTV availability, police station name, whether FIR filed.
   - DO NOT include address/location questions — those are handled by PERSONAL_KEYS.

4. Extract facts ALREADY clearly stated in the user message.
   NEVER extract personal info: full_name, phone, address, city, state.
   Only extract case-specific facts that were clearly stated.

USER MESSAGE: "{last_user_msg}"

Return valid JSON only. No markdown.
{{
  "category": "<category>",
  "policy_action": "allow",
  "policy_message": "",
  "initial_facts": {{}},
  "interview_plan": [
    {{"key": "<snake_case>", "label": "<Human Label>", "question": "<exact question text>"}}
  ]
}}
"""
        try:
            resp = llm.invoke([
                SystemMessage(content="Legal intake planner. Valid JSON only. No markdown."),
                HumanMessage(content=prompt)
            ])
            data = parse_llm_json(resp.content)
        except Exception as e:
            print(f"[classify/turn1] error: {e}")
            data = {
                "category": "Other civil complaint",
                "policy_action": "allow", "policy_message": "",
                "initial_facts": {},
                "interview_plan": [
                    {"key": "incident_date_time",   "label": "Date and Time",
                     "question": "When did this incident occur? Please give the date and approximate time."},
                    {"key": "incident_location",    "label": "Location",
                     "question": "Where did this take place?"},
                    {"key": "incident_description", "label": "What Happened",
                     "question": "Please briefly describe what happened."},
                    {"key": "loss_suffered",        "label": "Loss or Harm",
                     "question": "What loss or harm have you suffered?"},
                    {"key": "evidence_available",   "label": "Evidence Available",
                     "question": "What evidence do you have — documents, messages, receipts, screenshots?"},
                ],
            }

        policy_action  = str(data.get("policy_action", "allow")).strip().lower()
        policy_message = str(data.get("policy_message", "")).strip()

        if policy_action == "refuse":
            return {"stage": "done", "next_step": "refusal", "turn_count": turn_count,
                    "generated_content": policy_message,
                    "collected_facts": {}, "interview_plan": [], "answered_keys": [],
                    "classification_shown": False}

        if policy_action == "refer_professional":
            return {"stage": "done", "next_step": "refer_professional", "turn_count": turn_count,
                    "generated_content": policy_message,
                    "collected_facts": {}, "interview_plan": [], "answered_keys": [],
                    "classification_shown": False}

        category = data.get("category", "Other civil complaint")
        plan     = list(data.get("interview_plan", []))

        # Strip personal keys from LLM plan, append fixed personal keys at end
        plan = [s for s in plan if s.get("key") not in PERSONAL_KEY_SET]
        plan += PERSONAL_KEYS

        # Deduplicate
        seen, deduped = set(), []
        for step in plan:
            if step["key"] not in seen:
                seen.add(step["key"])
                deduped.append(step)
        plan = deduped

        # Store initial_facts ONLY for keys that exist in the plan
        # (prevents stale general facts like "stolen_item: motorcycle" appearing in summary)
        plan_keys = {s["key"] for s in plan}
        for k, v in (data.get("initial_facts") or {}).items():
            if k in plan_keys and k not in PERSONAL_KEY_SET and is_real_value(v):
                collected_facts[k] = v

        new_answered = [k for k in collected_facts if k in plan_keys]
        intent = f"{category} — {last_user_msg[:200]}"

        return {
            "category":             category,
            "intent":               intent,
            "collected_facts":      collected_facts,
            "interview_plan":       plan,
            "answered_keys":        new_answered,
            "stage":                "collecting",
            "next_step":            "ask_question",
            "turn_count":           turn_count,
            "readiness_score":      0,
            "current_question_key": "",
            "classification_shown": False,
        }

    # ── SUBSEQUENT TURNS: Extract answer ──────────────────────────────────
    if not current_q_key:
        return {
            "next_step": "ask_question", "stage": "collecting",
            "turn_count": turn_count, "collected_facts": collected_facts,
            "interview_plan": interview_plan, "answered_keys": answered_keys,
        }

    current_label = next(
        (s["label"] for s in interview_plan if s["key"] == current_q_key),
        current_q_key.replace("_", " ").title()
    )

    extract_prompt = f"""Extract the answer for this question.

Question: "{current_q_key}" — {current_label}
User replied: "{last_user_msg}"

Rules:
- Extract exactly what the user stated.
- If user said "no", "none", "don't know" → value = "Not available"
- NEVER extract user_full_name, user_phone, user_full_address unless that was the exact question.
- Do NOT invent or infer anything.

Return JSON only:
{{
  "extracted": {{
    "{current_q_key}": "value here"
  }}
}}
"""
    try:
        resp      = llm.invoke([
            SystemMessage(content="Fact extractor. JSON only. No inference."),
            HumanMessage(content=extract_prompt)
        ])
        data      = parse_llm_json(resp.content)
        extracted = data.get("extracted", {})
    except Exception as e:
        print(f"[extract] error: {e}")
        extracted = {current_q_key: last_user_msg[:300]}

    candidate = extracted.get(current_q_key, "")
    collected_facts[current_q_key] = (
        candidate if is_real_value(candidate)
        else ("Not available" if lower_msg in SKIP_VALUES else last_user_msg[:300])
    )

    if current_q_key not in answered_keys:
        answered_keys.append(current_q_key)

    # Mark incidentally answered plan keys
    plan_keys = {s["key"] for s in interview_plan}
    for k, v in extracted.items():
        if k in plan_keys and k not in answered_keys and is_real_value(v):
            answered_keys.append(k)
            if k not in collected_facts:
                collected_facts[k] = v

    # ── Auto-extract district, state, pincode from full address ───────────
    if current_q_key == "user_full_address" and is_real_value(collected_facts.get("user_full_address")):
        addr = collected_facts["user_full_address"]
        addr_prompt = f"""From this Indian residential address: "{addr}"
Extract district, state, and pincode if present.
Return JSON only:
{{
  "district": "<district name or empty>",
  "state":    "<state name or empty>",
  "pincode":  "<6-digit pincode or empty>"
}}
If you cannot determine a value, use empty string "".
"""
        try:
            ar = llm.invoke([
                SystemMessage(content="Indian address parser. JSON only."),
                HumanMessage(content=addr_prompt)
            ])
            ad = parse_llm_json(ar.content)
            if ad.get("district"):  collected_facts["user_district"] = ad["district"]
            if ad.get("state"):     collected_facts["user_state"]    = ad["state"]
            if ad.get("pincode"):   collected_facts["user_pincode"]  = ad["pincode"]
        except Exception as e:
            print(f"[addr-parse] {e}")

    missing   = [s for s in interview_plan if s["key"] not in answered_keys]
    total     = len(interview_plan)
    readiness = int(((total - len(missing)) / total) * 100) if total > 0 else 0

    return {
        "collected_facts":      collected_facts,
        "answered_keys":        answered_keys,
        "interview_plan":       interview_plan,
        "next_step":            "ask_confirmation" if not missing else "ask_question",
        "stage":                "confirming"       if not missing else "collecting",
        "readiness_score":      readiness,
        "turn_count":           turn_count,
        "current_question_key": current_q_key,
    }


# ============================================================
# NODE 3 — RESPOND
# ============================================================

def respond_node(state: LegalState):
    next_step            = state.get("next_step", "ask_question")
    lang                 = state.get("primary_language", "en")
    category             = state.get("category", "")
    collected_facts      = state.get("collected_facts", {})
    interview_plan       = state.get("interview_plan", [])
    answered_keys        = state.get("answered_keys", [])
    classification_shown = state.get("classification_shown", False)

    # ── SAFETY ───────────────────────────────────────────────────────────
    if next_step == "refusal":
        msg = state.get("generated_content") or (
            "I am unable to assist with this request through this platform. "
            "If you are in immediate danger, please call 100 (Police) or 112 (Emergency) immediately."
        )
        return {"generated_content": msg}

    if next_step == "refer_professional":
        msg = state.get("generated_content") or (
            "This matter requires a qualified legal professional. "
            "I can only help with standard document preparation in India. "
            "Please consult a lawyer before proceeding."
        )
        return {"generated_content": msg}

    # ── CONFIRMATION SUMMARY ─────────────────────────────────────────────
    if next_step == "ask_confirmation":
        summary_lines = []
        # Only iterate plan keys — never extra facts outside the plan
        for step in interview_plan:
            k = step["key"]
            v = collected_facts.get(k)
            if is_real_value(v):
                summary_lines.append(f"{step.get('label', k)}: {v}")

        numbered = "\n".join(f"{i+1}. {line}" for i, line in enumerate(summary_lines)) \
                   if summary_lines else "(No details collected yet.)"

        prompt = f"""You are an AI Legal Document Assistant. NOT a lawyer.

Write a confirmation message in language code: {lang}

Translate ALL labels and instructions to {lang}. Keep fact VALUES unchanged.

Structure:
1. One sentence thanking the user for providing all the details.
2. "Please review the information below. If everything is correct, reply YES to generate your document."
3. This numbered list (copy EXACTLY, translate only the label before the colon):

{numbered}

4. "If anything needs to be changed, please let me know what to correct."

Rules: No markdown. Plain text only. Return ONLY the message.
"""
        resp = llm.invoke([HumanMessage(content=prompt)])
        return {"generated_content": strip_markdown(resp.content.strip())}

    # ── ASK NEXT QUESTION ────────────────────────────────────────────────
    missing = [s for s in interview_plan if s["key"] not in answered_keys]

    if not missing:
        return {
            "generated_content": "Thank you for providing all the details. Let me prepare a summary for your review.",
            "next_step": "ask_confirmation",
            "stage":     "confirming",
        }

    target         = missing[0]
    target_key     = target["key"]
    base_question  = target.get("question", f"Could you provide: {target.get('label', target_key)}?")

    # Append example hint for address/location fields only
    example_hint = EXAMPLE_HINTS.get(target_key, "")
    fixed_question = f"{base_question} {example_hint}".strip()

    # Classification context — shown EXACTLY ONCE
    cat_line = ""
    new_classification_shown = classification_shown
    if not classification_shown and category:
        cat_line = (
            f"Thank you for explaining the situation. "
            f"This may relate to: {category}, which is commonly addressed under Indian legal procedure. "
            f"I will ask a few questions to collect the details needed to prepare the document.\n\n"
        )
        new_classification_shown = True

    # Acknowledgment for subsequent answers
    ack = ""
    if answered_keys:
        last_val = collected_facts.get(answered_keys[-1], "")
        if is_real_value(last_val):
            ack = "Thank you, I have noted that.\n\n"

    if lang == "en":
        response = cat_line + ack + fixed_question
    else:
        translate_prompt = f"""Translate this question into language code: {lang}

English: "{fixed_question}"
{"Also prepend (translated): " + repr(cat_line) if cat_line else ""}
{"Also prepend a brief acknowledgment like 'Thank you, I have noted that.'" if ack else ""}

Rules: ONE question only. Short and polite. No markdown. Return ONLY the translated text.
"""
        resp     = llm.invoke([
            SystemMessage(content="Translator. Plain text only."),
            HumanMessage(content=translate_prompt)
        ])
        response = strip_markdown(resp.content.strip())

    return {
        "generated_content":    response,
        "current_question_key": target_key,
        "classification_shown": new_classification_shown,
    }


# ============================================================
# NODE 4 — GENERATE DOCUMENT + NEXT STEPS
# ============================================================

def generate_document_node(state: LegalState):
    facts    = state.get("collected_facts", {})
    intent   = state.get("intent", "Legal Issue")
    category = state.get("category", "")
    lang     = state.get("primary_language", "en")

    result     = generate_bilingual_document(intent, facts, lang)
    next_steps = _get_next_steps(category, intent, facts)

    payload = json.dumps({
        "document_type":         result["document_type"],
        "user_language":         lang,
        "readiness_score":       result["readiness_score"],
        "user_language_content": result["user_language_content"],
        "english_content":       result["english_content"],
        "disclaimer_en":         result["disclaimer_en"],
        "disclaimer_user_lang":  result["disclaimer_user_lang"],
        "reference_number":      result.get("reference_number", ""),
        "next_steps":            next_steps,
    }, ensure_ascii=False)

    return {
        "generated_content": f"DOCUMENT_READY\n{payload}",
        "readiness_score":   result["readiness_score"],
        "stage":             "done",
    }


def _get_next_steps(category: str, intent: str, facts: dict) -> list:
    clean = {k: v for k, v in facts.items()
             if v and str(v).strip().lower() not in
             {"", "null", "unknown", "not available", "none", "n/a", "na"}}
    facts_text = "\n".join(
        f"  {k.replace('_', ' ').title()}: {v}" for k, v in clean.items()
    )
    prompt = f"""You are an Indian legal document assistant.
A user just received a drafted legal document. Give them 3 to 5 practical next steps.

Category: {category}
Legal issue: {intent}

Case facts:
{facts_text}

Rules:
- Specific to this exact case and facts.
- Mention specific Indian portals, helplines, or authorities.
- Most urgent action first.
- Each step is ONE clear sentence.
- No legal advice — only practical filing/reporting actions.
- Return ONLY a JSON array of strings. No explanation, no markdown.

Example: ["Step one.", "Step two.", "Step three."]
"""
    try:
        resp  = llm.invoke([
            SystemMessage(content="Next steps advisor. Return a JSON array of strings only."),
            HumanMessage(content=prompt)
        ])
        raw   = resp.content.strip()
        raw   = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw   = re.sub(r'\s*```\s*$',       '', raw, flags=re.MULTILINE)
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        steps = json.loads(raw)
        if isinstance(steps, list):
            return [str(s).strip() for s in steps if s]
    except Exception as e:
        print(f"[_get_next_steps] error: {e}")
    return []


# ============================================================
# ROUTING
# ============================================================

def route_after_classify(state: LegalState):
    step = state.get("next_step", "ask_question")
    return "generate_document" if step == "generate_document" else "respond"


# ============================================================
# GRAPH ASSEMBLY
# ============================================================

workflow = StateGraph(LegalState)
workflow.add_node("detect_language",   detect_language_node)
workflow.add_node("classify_and_plan", classify_and_plan_node)
workflow.add_node("respond",           respond_node)
workflow.add_node("generate_document", generate_document_node)

workflow.set_entry_point("detect_language")
workflow.add_edge("detect_language", "classify_and_plan")
workflow.add_conditional_edges("classify_and_plan", route_after_classify, {
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
    DB_URL = raw_db_url.replace("jdbc:", "", 1) if raw_db_url.startswith("jdbc:") else raw_db_url

    with ConnectionPool(conninfo=DB_URL, min_size=1, max_size=1, kwargs={"autocommit": True}) as p:
        PostgresSaver(p).setup()

    pool         = ConnectionPool(conninfo=DB_URL, max_size=20)
    checkpointer = PostgresSaver(pool)
    print("[graph] Postgres checkpointer connected.")
except Exception as e:
    print(f"[graph] Using in-memory checkpointer. ({e})")
    checkpointer = MemorySaver()

graph_app = workflow.compile(checkpointer=checkpointer)


# ============================================================
# PUBLIC ENTRY POINT
# ============================================================

def process_message(thread_id: str, user_input: str) -> dict:
    if not user_input or not user_input.strip():
        return {
            "content": GREETING, "entities": {}, "intent": "",
            "readiness_score": 0, "is_document": False,
            "is_confirmation": False, "next_steps": [],
        }

    config = {"configurable": {"thread_id": thread_id}}

    current_state = graph_app.get_state(config).values
    current_stage = current_state.get("stage", "")
    input_hash    = hashlib.md5(user_input.encode()).hexdigest()
    last_hash     = current_state.get("last_input_hash", "")

    # Skip dedup when in confirming stage — "yes" must always be processed
    if (input_hash == last_hash) and current_stage not in ("confirming", "done", ""):
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

    next_steps = []
    if is_doc:
        try:
            payload_data = json.loads(content[len("DOCUMENT_READY"):].strip())
            next_steps   = payload_data.get("next_steps", [])
        except Exception:
            pass

    return {
        "content":         content,
        "entities":        state.get("collected_facts", {}),
        "intent":          state.get("intent", ""),
        "readiness_score": state.get("readiness_score", 0),
        "is_document":     is_doc,
        "is_confirmation": (next_step == "ask_confirmation"),
        "next_steps":      next_steps,
    }
