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
# NOTE: user_phone is intentionally excluded here — users log in with their phone
# number, so we pre-populate it from the auth token instead of asking again.
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
]
PERSONAL_KEY_SET = {s["key"] for s in PERSONAL_KEYS}
# user_phone is still in SKIP_PERSONAL so the LLM doesn’t ask it either
PERSONAL_KEY_SET.add("user_phone")

# Evidence question — always appended just before personal keys
EVIDENCE_KEY = {
    "key":      "evidence_available",
    "label":    "Evidence Available",
    "question": "What evidence do you have? For example: SMS alerts, screenshots, receipts, photographs, medical reports, or any documents related to this incident.",
}


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
        
    collected = dict(state.get("collected_facts") or {})
    collected["_language_"] = lang
    return {"primary_language": lang, "collected_facts": collected}


# ============================================================
# NODE 2 — CLASSIFY + PLAN + EXTRACT
# ============================================================

def get_evidence_question(category: str) -> dict:
    """Generate case-specific evidence question with relevant examples"""
    
    base_q = "What evidence do you have to support this complaint?"
    
    # Category-specific examples
    if category == "Consumer complaint":
        examples = "purchase receipt, invoice, warranty card, product photos, defect photos, email/SMS with seller, packaging"
    elif category in ["Theft / Robbery", "Assault", "Harassment / Threat"]:
        examples = "witness statements, CCTV footage if available, photographs of injuries or scene, medical reports if injured, FIR copy if already filed"
    elif category == "Cyber crime":
        examples = "screenshots of fraudulent messages, bank transaction details, account statements, email headers, chat logs, UPI transaction receipts"
    elif category in ["Salary / Employment dispute", "Workplace Complaints"]:
        examples = "appointment letter, salary slips, bank statements showing salary, employment contract, email correspondence with employer"
    elif category == "Banking issue":
        examples = "bank statements, transaction SMS, passbook entries, loan agreement, email/letter from bank, cheque copies"
    elif category == "Insurance dispute":
        examples = "insurance policy copy, premium payment receipts, claim forms, rejection letter, correspondence with insurance company"
    elif category in ["Property dispute", "Landlord / Tenant dispute"]:
        examples = "sale deed, rental agreement, rent receipts, property tax receipts, possession documents, photographs"
    elif category == "RTI Application":
        examples = "previous correspondence with department if any, copies of earlier applications, proof of fees paid"
    elif category == "Cheating / Fraud":
        examples = "written agreement, payment receipts, bank transfer details, WhatsApp/SMS conversations, witness statements"
    else:
        examples = "receipts, written agreements, photographs, email/SMS correspondence, witness contact information"
    
    return {
        "key": "evidence_available",
        "label": "Evidence Available",
        "question": f"{base_q} For this type of case, relevant evidence includes: {examples}."
    }

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

    # ── Pre-fill facts injected by Java backend (phone number, name etc.) ────
    if last_user_msg.startswith("__PREFILL__"):
        prefill_part, _, actual_msg = last_user_msg.partition(" || ")
        
        # Robustly parse key=value or key="multi word value"
        import re
        tokens = re.findall(r'(\w+)=([^"\s]+|"[^"]+")', prefill_part)
        for k, v in tokens:
            v_clean = v.strip('"')
            if is_real_value(v_clean) and k not in collected_facts:
                collected_facts[k] = v_clean
                if k not in answered_keys:
                    answered_keys.append(k)
                    
        last_user_msg = actual_msg.strip()
        lower_msg     = last_user_msg.lower()

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
   Salary / Employment dispute | Property dispute | Landlord / Tenant dispute | Harassment / Threat |
   Cheating / Fraud | Family / Matrimonial | Banking issue |
   RTI Application | Insurance dispute | Other civil complaint

   IMPORTANT CLASSIFICATION RULES:
   - Threatening phone calls, messages, or in-person threats demanding money or causing fear = Harassment / Threat
   - Extortion, blackmail, criminal intimidation = Harassment / Threat
   - Online fraud, UPI fraud, phishing = Cyber crime (NOT Banking issue)
   - Defective product or service = Consumer complaint (NOT Cheating / Fraud)
   - Salary not paid by employer = Salary / Employment dispute (NOT Cheating / Fraud)
   - NEVER classify threatening calls as "Other civil complaint"

2. Safety routing:
   - "refuse"             → immediate life threat or illegal/unethical request
   - "refer_professional" → outside India, serious criminal liability, complex litigation
   - "allow"              → normal document preparation

3. Design a CASE-SPECIFIC interview plan — 4 to 7 questions for THIS exact problem.
   RULES:
   - Identify the EXACT core facts needed for the specific type of legal document being requested.
   - For example: if property/tenant, ask about agreements, dates, landlords, amounts. If a loan, ask dates, amounts, proofs. If theft, ask what/when/where. If consumer, ask product/seller/defect.
   - You must DYNAMICALLY generate precise questions tailored to the exact situation described by the user.
   - COMBINE paired facts into ONE question (e.g. date + time → one key).
   - NEVER ask: suspect description, CCTV availability, police station name, whether FIR filed.
   - DO NOT include general address/location/personal/name questions — those are ALWAYS handled automatically by our PERSONAL_KEYS. Focus ONLY on the incident/issue facts.

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

        # ═══ Add authority-specific location questions based on category ═══

        # For criminal complaints → ask for police station
        if category in [
            "Theft / Robbery", 
            "Assault", 
            "Harassment / Threat", 
            "Cheating / Fraud",
            "Cyber crime"
        ]:
            plan.append({
                "key": "police_station_name",
                "label": "Police Station Jurisdiction",
                "question": "Which police station has jurisdiction over your area? If unsure, please mention your locality name. (Example: Anna Nagar Police Station, Chennai OR just 'Anna Nagar, Chennai')"
            })

        # For consumer complaints → ask for seller details and forum location
        elif category == "Consumer complaint":
            plan.append({
                "key": "seller_name_location",
                "label": "Seller/Company Name and Location",
                "question": "What is the complete name and location of the seller or company you are complaining about? (Example: XYZ Electronics, T. Nagar, Chennai)"
            })
            plan.append({
                "key": "consumer_forum_district",
                "label": "Your District for Consumer Forum",
                "question": "Which district do you live in? Consumer complaints are typically filed in your district's consumer forum. (Example: Salem District, Tamil Nadu)"
            })

        # For banking complaints → ask for branch details
        elif category == "Banking issue":
            plan.append({
                "key": "bank_branch_details",
                "label": "Bank Branch Name and Location",
                "question": "Which bank branch are you dealing with? Please provide the complete branch name and location. (Example: State Bank of India, Main Branch, T. Nagar, Chennai - 600017)"
            })

        # For insurance complaints → ask for office/branch
        elif category == "Insurance dispute":
            plan.append({
                "key": "insurance_office_location",
                "label": "Insurance Company Office",
                "question": "Which insurance company office or branch are you dealing with? Provide the office name and location. (Example: LIC Branch Office, Anna Salai, Chennai)"
            })

        # For employment/workplace → ask for employer details
        elif category == "Salary / Employment dispute":
            plan.append({
                "key": "employer_name_address",
                "label": "Employer Name and Office Address",
                "question": "What is your employer's full company name and complete office address?"
            })

        # For property disputes → ask for property location
        elif category == "Property dispute":
            plan.append({
                "key": "property_exact_location",
                "label": "Property Location",
                "question": "What is the exact location/address of the disputed property? Include survey numbers if available."
            })

        # For landlord/tenant → ask for property address and landlord name
        elif category == "Landlord / Tenant dispute":
            plan.append({
                "key": "rental_property_address",
                "label": "Rental Property Address",
                "question": "What is the complete address of the rental property in question?"
            })
            plan.append({
                "key": "other_party_name",
                "label": "Landlord / Other Party Name",
                "question": "What is the full name of the landlord (or the other party in this dispute)?"
            })

        # For property disputes → ask for the other party name (builder, neighbour, etc.)
        elif category == "Property dispute":
            plan.append({
                "key": "other_party_name",
                "label": "Builder / Other Party Name",
                "question": "What is the full name of the builder or the other party involved in this dispute? (e.g., ABC Builders Pvt. Ltd.)"
            })

        # For RTI applications → ask for department/office
        elif category == "RTI Application":
            plan.append({
                "key": "rti_department_name",
                "label": "Government Department/Office",
                "question": "Which government department or office are you seeking information from? Provide the complete name. (Example: Revenue Department, Collectorate Office, Salem District)"
            })

        # Strip personal keys from LLM plan
        plan = [s for s in plan if s.get("key") not in PERSONAL_KEY_SET]
        # Also remove evidence_available if LLM included it (we add our own below)
        plan = [s for s in plan if s.get("key") != "evidence_available"]
        # Always append: evidence question → then personal keys
        evidence_q = get_evidence_question(category)
        plan += [evidence_q] + PERSONAL_KEYS

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

    extract_prompt = f"""Extract the factual answer for this question from the user's message.

Question: "{current_q_key}" — {current_label}
User replied: "{last_user_msg}"

Rules:
- EXTRACT ONLY THE DATA. Strip conversational filler (e.g. "My name is", "I live at", "My address is").
- If user said "My name is S. Karthik", extract ONLY "S. Karthik".
- Keep original casing and script.
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

    # Validate phone number
    if current_q_key == "user_phone":
        phone_value = str(collected_facts.get("user_phone", "")).strip()
        # Check if it's a valid 10-digit Indian phone number
        if not re.match(r'^\d{10}$', phone_value):
            # Invalid - re-ask
            return {
                "generated_content": "Please provide a valid 10-digit mobile number (Example: 9876543210)",
                "collected_facts": collected_facts,
                "interview_plan": interview_plan,
                "answered_keys": [k for k in answered_keys if k != "user_phone"],
                "current_question_key": "user_phone",
                "next_step": "ask_question",
                "stage": "collecting",
                "turn_count": turn_count,
            }

    # Validate evidence input
    if current_q_key == "evidence_available":
        evidence_value = str(collected_facts.get("evidence_available", "")).strip().upper()
        
        # If user just said YES/NO/NONE without describing actual evidence
        if evidence_value in ["YES", "NO", "NONE", "NOTHING", "NOT AVAILABLE", "N/A", "NA"]:
            return {
                "generated_content": "Please describe the specific evidence you have. For example: 'Purchase receipt from XYZ Store dated 1 March 2024, warranty card, photographs of the defect, email exchange with seller'. If you have no evidence, say 'I have no documentary evidence at this time'.",
                "collected_facts": {k: v for k, v in collected_facts.items() if k != "evidence_available"},
                "interview_plan": interview_plan,
                "answered_keys": [k for k in answered_keys if k != "evidence_available"],
                "current_question_key": "evidence_available",
                "next_step": "ask_question",
                "stage": "collecting",
                "turn_count": turn_count,
            }

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
        translate_prompt = f"""Translate this entire text into language code: {lang}
        
TEXT: "{cat_line + ack + fixed_question}"

RULES:
1. RESPONSE MUST BE IN {lang.upper()} SCRIPT ONLY (e.g. Tamil characters for Tamil).
2. DO NOT USE "Tanglish" or Romanized script for regional words. No "Vanakkam", only "வணக்கம்".
3. Keep it formal, polite, and strictly one or two short sentences.
4. Explanations of legal terms can be in primary script. No markdown.
5. Return ONLY the translated string.
"""
        resp     = llm.invoke([
            SystemMessage(content="Professional legal translator. Regional script only."),
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
    current_q_key = current_state.get("current_question_key", "")
    input_hash    = hashlib.md5((user_input + current_q_key).encode()).hexdigest()
    last_hash     = current_state.get("last_input_hash", "")

    # Dedup: only skip if the same answer was already processed for the SAME question.
    # Including current_question_key in the hash means identical answers to DIFFERENT
    # questions (e.g. two consecutive "No" answers) are never skipped.
    # Never dedup when in confirming/done stage.
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
