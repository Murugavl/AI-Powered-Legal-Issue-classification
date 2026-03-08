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
# STATE
# ============================================================

class LegalState(TypedDict):
    messages:             Annotated[List[BaseMessage], add_messages]
    thread_id:            str
    primary_language:     str
    collected_facts:      Dict[str, Any]
    interview_plan:       List[Dict]
    answered_keys:        List[str]
    current_question_key: str
    stage:                str            # collecting | confirming | done
    next_step:            str
    intent:               str
    turn_count:           int
    generated_content:    str
    readiness_score:      int
    last_input_hash:      str


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
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = text.replace("```", "")
    return text.strip()


def parse_llm_json(raw: str) -> dict:
    """Reliably parse JSON from LLM output, stripping markdown fences."""
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```\s*$', '', raw, flags=re.MULTILINE)
    raw = raw.strip()
    # Find the first { ... } block if there's surrounding text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


# ============================================================
# NODE 1 — DETECT LANGUAGE (locked on first message only)
# ============================================================

def detect_language_node(state: LegalState):
    if state.get("primary_language"):
        return {}

    messages = state.get("messages", [])
    if not messages:
        return {"primary_language": "en"}

    last_msg = messages[-1].content
    prompt = (
        'Detect the ISO 639-1 language code of the text below.\n'
        'Return ONLY the 2-letter code. Valid codes: en ta hi te kn ml mr bn gu\n\n'
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

    # ── CONFIRMING STAGE ─────────────────────────────────────────────────
    if stage == "confirming":
        upper = last_user_msg.strip().upper().rstrip(".!?")
        confirmed = upper in {
            "YES", "OK", "OKAY", "CORRECT", "CONFIRMED", "SURE",
            "LOOKS GOOD", "THAT IS CORRECT", "THATS CORRECT", "YES IT IS", "YES CORRECT"
        } or any(p in upper for p in [
            "YES, THE ABOVE", "YES THE ABOVE", "YES I CONFIRM",
            "EVERYTHING IS CORRECT", "ALL CORRECT", "INFORMATION IS CORRECT",
            "ABOVE INFORMATION IS CORRECT",
        ])
        wants_edit = any(p in upper for p in [
            "NO", "CHANGE", "EDIT", "WRONG", "INCORRECT", "NOT CORRECT",
            "WANT TO MAKE", "PLEASE CHANGE", "SOMETHING IS WRONG",
        ])

        if confirmed:
            return {
                "stage": "done", "next_step": "generate_document",
                "turn_count": turn_count, "collected_facts": collected_facts,
                "interview_plan": interview_plan, "answered_keys": answered_keys,
            }
        elif wants_edit:
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

    # ── TURN 1: Build interview plan ─────────────────────────────────────
    if turn_count == 1:
        plan_prompt = f"""You are a legal document intake planner for India.

A user has described their legal problem. Do three things:
1. Identify the legal issue type (intent) — short, specific description.
2. Check safety: is this an ACTIVE immediate threat to life RIGHT NOW? (UNSAFE only if yes)
3. Design a precise interview plan — ordered list of facts to collect.

USER'S MESSAGE:
"{last_user_msg}"

INTERVIEW PLAN RULES:
- Each step collects ONE specific fact relevant to THIS exact case.
- Study the user's problem carefully. Design steps specific to it.
  Ask about the details that MATTER for this type of complaint — amounts, dates, parties involved,
  what happened, what evidence exists, what action was taken.
- COMBINE naturally paired facts into one key:
    date + time → single key (e.g. incident_date_time, label "Date and Time of Incident")
    make + model → single key (e.g. vehicle_details, label "Vehicle Make, Model and Color")
- OMIT questions that are irrelevant to document drafting for this case.
- 5 to 9 steps total. Quality over quantity.
- ALWAYS end with EXACTLY these 3 keys as the last 3 steps (in this order):
    user_full_name  / "Your Full Name"
    user_city_state / "City and State"
    user_phone      / "Your Phone Number"

INITIAL FACTS:
- Extract facts the user ALREADY stated in their message.
- NEVER extract user_full_name, user_phone, or user_city_state from the first message.

Return valid JSON only. No markdown.
{{
  "intent": "<short description of the legal issue>",
  "safety_status": "SAFE",
  "initial_facts": {{
    "<key>": "<value from first message if explicitly stated>"
  }},
  "interview_plan": [
    {{"key": "<fact_key>", "label": "<Human Readable Label>"}},
    {{"key": "user_full_name", "label": "Your Full Name"}},
    {{"key": "user_city_state", "label": "City and State"}},
    {{"key": "user_phone", "label": "Your Phone Number"}}
  ]
}}
"""
        try:
            resp = llm.invoke([
                SystemMessage(content="Legal intake planner. Return valid JSON only. No markdown."),
                HumanMessage(content=plan_prompt)
            ])
            data = parse_llm_json(resp.content)
        except Exception as e:
            print(f"[classify_and_plan/turn1] error: {e}")
            data = {
                "intent": "legal complaint",
                "safety_status": "SAFE",
                "initial_facts": {},
                "interview_plan": [
                    {"key": "incident_date_time",   "label": "Date and Time of Incident"},
                    {"key": "incident_location",    "label": "Location of Incident"},
                    {"key": "incident_description", "label": "Description of What Happened"},
                    {"key": "harm_suffered",        "label": "Loss or Harm Suffered"},
                    {"key": "evidence_available",   "label": "Evidence You Have"},
                    {"key": "user_full_name",        "label": "Your Full Name"},
                    {"key": "user_city_state",       "label": "City and State"},
                    {"key": "user_phone",            "label": "Your Phone Number"},
                ]
            }

        if data.get("safety_status") == "UNSAFE":
            return {
                "stage": "done", "next_step": "refusal", "turn_count": turn_count,
                "intent": "SAFETY_REFUSAL", "collected_facts": collected_facts,
                "interview_plan": [], "answered_keys": [],
            }

        intent = data.get("intent", "legal complaint")
        plan   = data.get("interview_plan", [])

        # Enforce personal details always at end
        PERSONAL = ["user_full_name", "user_city_state", "user_phone"]
        plan = [s for s in plan if s["key"] not in PERSONAL]
        plan += [
            {"key": "user_full_name",  "label": "Your Full Name"},
            {"key": "user_city_state", "label": "City and State"},
            {"key": "user_phone",      "label": "Your Phone Number"},
        ]

        # Deduplicate
        seen, deduped = set(), []
        for step in plan:
            if step["key"] not in seen:
                seen.add(step["key"])
                deduped.append(step)
        plan = deduped

        # Merge initial facts — never accept personal keys from turn 1
        NEVER_EARLY = {"user_full_name", "user_phone", "user_city_state", "user_email"}
        for k, v in (data.get("initial_facts") or {}).items():
            if k not in NEVER_EARLY and is_real_value(v):
                collected_facts[k] = v

        plan_keys    = {s["key"] for s in plan}
        new_answered = [k for k in collected_facts if k in plan_keys]

        return {
            "intent":               intent,
            "collected_facts":      collected_facts,
            "interview_plan":       plan,
            "answered_keys":        new_answered,
            "stage":                "collecting",
            "next_step":            "ask_question",
            "turn_count":           turn_count,
            "readiness_score":      0,
            "current_question_key": "",
        }

    # ── SUBSEQUENT TURNS: Extract answer to current question ─────────────
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

    history = "\n".join([
        f"{'User' if m.type == 'human' else 'Assistant'}: {m.content}"
        for m in messages[-8:]
    ])

    extract_prompt = f"""Extract the answer for the question that was asked.

Question asked: "{current_q_key}" — {current_label}
User's reply: "{last_user_msg}"

Rules:
- Extract exactly what the user stated for this question.
- If user said "no", "none", "don't know", "not available" → value = "Not available"
- You may also extract other facts clearly volunteered in this reply.
- NEVER extract user_full_name, user_phone, user_city_state unless that was the question asked.
- Do NOT infer or invent anything.

Recent conversation context:
{history[-1200:]}

Return JSON only:
{{
  "extracted": {{
    "{current_q_key}": "value here"
  }}
}}
"""
    try:
        resp      = llm.invoke([
            SystemMessage(content="Fact extractor. JSON only. No inference. No markdown."),
            HumanMessage(content=extract_prompt)
        ])
        data      = parse_llm_json(resp.content)
        extracted = data.get("extracted", {})
    except Exception as e:
        print(f"[extract] error: {e}")
        extracted = {current_q_key: last_user_msg[:300]}

    for k, v in extracted.items():
        if is_real_value(v):
            collected_facts[k] = v

    if current_q_key not in answered_keys:
        answered_keys.append(current_q_key)

    plan_keys = {s["key"] for s in interview_plan}
    for k in extracted:
        if k in plan_keys and k not in answered_keys:
            answered_keys.append(k)

    missing   = [s for s in interview_plan if s["key"] not in answered_keys]
    total     = len(interview_plan)
    readiness = int(((total - len(missing)) / total) * 100) if total > 0 else 0

    return {
        "collected_facts":      collected_facts,
        "answered_keys":        answered_keys,
        "interview_plan":       interview_plan,
        "next_step":            "ask_confirmation" if not missing else "ask_question",
        "stage":                "confirming" if not missing else "collecting",
        "readiness_score":      readiness,
        "turn_count":           turn_count,
        "current_question_key": current_q_key,
    }


# ============================================================
# NODE 3 — RESPOND
# ============================================================

def respond_node(state: LegalState):
    next_step       = state.get("next_step", "ask_question")
    lang            = state.get("primary_language", "en")
    intent          = state.get("intent", "legal issue")
    collected_facts = state.get("collected_facts", {})
    interview_plan  = state.get("interview_plan", [])
    answered_keys   = state.get("answered_keys", [])
    turn_count      = state.get("turn_count", 1)
    messages        = state.get("messages", [])

    # ── SAFETY REFUSAL ───────────────────────────────────────────────────
    if next_step == "refusal":
        return {"generated_content": (
            "I am unable to assist with this request through this platform. "
            "If you are in immediate danger, please call 100 (Police) or 112 (Emergency) immediately."
        )}

    # ── CONFIRMATION SUMMARY ─────────────────────────────────────────────
    if next_step == "ask_confirmation":
        summary_lines  = []
        plan_keys_seen = set()

        for step in interview_plan:
            k = step["key"]
            v = collected_facts.get(k)
            plan_keys_seen.add(k)
            if is_real_value(v):
                lbl = step.get("label", k.replace("_", " ").title())
                summary_lines.append(f"{lbl}: {v}")

        for k, v in collected_facts.items():
            if k not in plan_keys_seen and is_real_value(v):
                summary_lines.append(f"{k.replace('_', ' ').title()}: {v}")

        numbered = "\n".join(f"{i+1}. {line}" for i, line in enumerate(summary_lines)) \
                   if summary_lines else "(No details collected yet.)"

        prompt = f"""You are a warm Indian legal document assistant. NOT a lawyer.

Write a short confirmation message in language code: {lang}

Format (translate all labels and instructions to {lang}, keep fact VALUES unchanged):
- One warm sentence thanking the user for providing all the information.
- "Here is a summary of the information I have collected:"
- The numbered list below — copy values EXACTLY, only translate the labels:

{numbered}

- "Please review the above information."
- "To confirm, please reply: Yes, the above information is correct."
- "If anything needs to be corrected, please let me know."

Rules: No markdown. Plain text only. Return ONLY the message.
"""
        resp = llm.invoke([HumanMessage(content=prompt)])
        return {"generated_content": strip_markdown(resp.content.strip())}

    # ── ASK NEXT QUESTION ────────────────────────────────────────────────
    missing = [s for s in interview_plan if s["key"] not in answered_keys]

    if not missing:
        return {
            "generated_content": "Thank you. Let me now prepare a summary for your review.",
            "next_step": "ask_confirmation",
            "stage":     "confirming",
        }

    target       = missing[0]
    target_key   = target["key"]
    target_label = target.get("label", target_key.replace("_", " ").title())

    history_text = "\n".join([
        f"{'User' if m.type == 'human' else 'Assistant'}: {m.content}"
        for m in (messages[-6:] if len(messages) >= 6 else messages)
    ])

    already_collected = {k: v for k, v in collected_facts.items() if is_real_value(v)}

    # First question only: one-time classification context
    classification_context = ""
    if turn_count <= 2:
        classification_context = (
            "Begin with ONE sentence of cautious issue context: "
            "'Situations like this may relate to [area], which is commonly addressed under "
            "[relevant Indian law/authority].' Then ask your question immediately. "
            "Do NOT repeat this classification sentence in any future question.\n\n"
        )

    # Brief acknowledgment with the actual value confirmed — gives a running recap like GPT
    ack_instruction = ""
    if answered_keys and turn_count > 2:
        last_key = answered_keys[-1]
        last_val = collected_facts.get(last_key, "")
        last_label = next(
            (s["label"] for s in interview_plan if s["key"] == last_key),
            last_key.replace("_", " ").title()
        )
        if is_real_value(last_val):
            ack_instruction = (
                f"Start with exactly one sentence acknowledging the previous answer: "
                f"'Thank you, I have noted: {last_label} — {last_val}.' "
                f"Then immediately ask the next question on a new line.\n\n"
            )

    prompt = f"""You are a warm, empathetic Indian legal document assistant (NOT a lawyer).
You collect facts one at a time to draft legal documents. You never give legal advice.

Legal issue: {intent}
Facts collected so far: {json.dumps(already_collected, ensure_ascii=False)}

Conversation so far:
{history_text}

{classification_context}{ack_instruction}Ask ONE focused question to collect:
Key: "{target_key}"
Label: "{target_label}"

RULES:
1. ONE question only. Never combine two questions.
2. Make it specific to this exact case and label. Ask for the concrete detail described by the label.
3. Do NOT ask for anything already in the facts above.
4. Do NOT summarise or repeat previously collected information.
5. No section headers, no lists, no bullet points.
6. Respond ONLY in language code: {lang}.
7. No markdown, no asterisks, no hashtags.
8. Return ONLY: [optional 1-line ack] + [the single question].
"""
    resp = llm.invoke([
        SystemMessage(content="Legal intake. One question per turn. Plain text. No markdown."),
        HumanMessage(content=prompt)
    ])

    return {
        "generated_content":    strip_markdown(resp.content.strip()),
        "current_question_key": target_key,
    }


# ============================================================
# NODE 4 — GENERATE DOCUMENT + NEXT STEPS
# ============================================================

def generate_document_node(state: LegalState):
    facts  = state.get("collected_facts", {})
    intent = state.get("intent", "Legal Issue")
    lang   = state.get("primary_language", "en")

    result     = generate_bilingual_document(intent, facts, lang)
    doc_type   = result.get("document_type", "")
    next_steps = _get_next_steps(doc_type, intent, facts)

    payload = json.dumps({
        "document_type":         result["document_type"],
        "user_language":         lang,
        "readiness_score":       result["readiness_score"],
        "user_language_content": result["user_language_content"],
        "english_content":       result["english_content"],
        "disclaimer_en":         result["disclaimer_en"],
        "disclaimer_user_lang":  result["disclaimer_user_lang"],
        "next_steps":            next_steps,
    }, ensure_ascii=False)

    return {
        "generated_content": f"DOCUMENT_READY\n{payload}",
        "readiness_score":   result["readiness_score"],
        "stage":             "done",
    }


def _get_next_steps(doc_type: str, intent: str, facts: dict) -> list:
    """
    Fully LLM-generated next steps — no hardcoded case logic.
    The LLM reads the actual intent, doc_type, and facts and gives
    specific, actionable steps for whatever case this is.
    """
    clean = {k: v for k, v in facts.items()
             if v and str(v).strip().lower() not in
             {"", "null", "unknown", "not available", "none", "n/a", "na"}}
    facts_text = "\n".join(
        f"  {k.replace('_', ' ').title()}: {v}" for k, v in clean.items()
    )

    prompt = f"""You are an Indian legal assistant. A user just received a drafted legal document.
Give them 3 to 5 practical next steps to take immediately.

Legal issue: {intent}
Document type: {doc_type}

Case facts:
{facts_text}

Rules:
- Be SPECIFIC to this exact case. Read the facts carefully.
- Mention specific Indian portals, helplines, or authorities relevant to this case type.
- If facts mention a city or state, include state-specific resources if known.
- Put the most urgent action first.
- Each step is ONE clear sentence.
- Return ONLY a JSON array of strings. No explanation, no markdown, no preamble.

Example output format:
["Urgent step here.", "Second step here.", "Third step here."]
"""
    try:
        resp = llm.invoke([
            SystemMessage(content="Next steps advisor. Return a JSON array of strings only."),
            HumanMessage(content=prompt)
        ])
        raw = resp.content.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s*```\s*$', '', raw, flags=re.MULTILINE)
        # Find JSON array
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
    if step == "generate_document":
        return "generate_document"
    return "respond"


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
            "content": (
                "Vanakkam! I am your AI Legal Document Assistant. "
                "I am not a lawyer and I do not provide legal advice. "
                "Please describe your legal issue in your own words and I will help you "
                "prepare the necessary documents."
            ),
            "entities": {}, "intent": "", "readiness_score": 0,
            "is_document": False, "is_confirmation": False, "next_steps": [],
        }

    config     = {"configurable": {"thread_id": thread_id}}
    input_hash = hashlib.md5(user_input.encode()).hexdigest()

    current_state = graph_app.get_state(config).values
    if current_state.get("last_input_hash") == input_hash:
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
