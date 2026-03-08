"""
Bilingual Document Generator — Fully case-agnostic.

Strategy:
  1. LLM determines document type, authority, and reference prefix from intent.
  2. LLM extracts scalar values (single-line JSON — reliable).
  3. LLM writes body prose as plain text (no JSON — zero parsing failures).
  4. Python assembles everything into the fixed template.
  5. Readiness score is LLM-computed from actual fact content.
"""

import json
import re
from datetime import date
from llm_provider import llm
from langchain_core.messages import HumanMessage, SystemMessage


# ── Language names ────────────────────────────────────────────────────────────
LANGUAGE_NAMES = {
    "en": "English", "hi": "Hindi",  "ta": "Tamil",
    "te": "Telugu",  "kn": "Kannada","ml": "Malayalam",
    "mr": "Marathi", "bn": "Bengali","gu": "Gujarati",
}

# ── Disclaimers ───────────────────────────────────────────────────────────────
DISCLAIMER_EN = (
    "This document has been automatically generated based solely on information provided by the user. "
    "It is intended for informational and documentation purposes only and does not constitute legal advice. "
    "Users are strongly advised to review or verify this document with a qualified legal professional "
    "before official submission."
)

DISCLAIMER_TRANSLATIONS = {
    "ta": (
        "இந்த ஆவணம் பயனர் வழங்கிய தகவல்களின் அடிப்படையில் மட்டுமே தானாக உருவாக்கப்பட்டது. "
        "இது தகவல் மற்றும் ஆவணத் தயாரிப்பு நோக்கத்திற்காக மட்டுமே வழங்கப்படுகிறது — "
        "இது சட்ட ஆலோசனையாக கருதப்படக்கூடாது. "
        "அதிகாரப்பூர்வமாக சமர்ப்பிப்பதற்கு முன் தகுதியான சட்ட நிபுணரால் சரிபார்க்கப்பட வேண்டும்."
    ),
    "hi": (
        "यह दस्तावेज़ उपयोगकर्ता द्वारा प्रदान की गई जानकारी के आधार पर स्वचालित रूप से तैयार किया गया है। "
        "यह केवल सूचना और दस्तावेज़ीकरण उद्देश्यों के लिए है — यह कानूनी सलाह नहीं है। "
        "आधिकारिक प्रस्तुति से पहले किसी योग्य कानूनी पेशेवर से समीक्षा कराने की सलाह दी जाती है।"
    ),
    "te": (
        "ఈ పత్రం వినియోగదారు అందించిన సమాచారం ఆధారంగా స్వయంచాలకంగా రూపొందించబడింది. "
        "ఇది సమాచార మరియు డాక్యుమెంటేషన్ ప్రయోజనాల కోసం మాత్రమే — చట్టపరమైన సలహా కాదు."
    ),
    "kn": (
        "ಈ ದಾಖಲೆಯನ್ನು ಬಳಕೆದಾರರು ಒದಗಿಸಿದ ಮಾಹಿತಿಯ ಆಧಾರದ ಮೇಲೆ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ರಚಿಸಲಾಗಿದೆ. "
        "ಇದು ಕೇವಲ ಮಾಹಿತಿ ಮತ್ತು ದಾಖಲಾತಿ ಉದ್ದೇಶಗಳಿಗಾಗಿ ಮಾತ್ರ — ಕಾನೂನು ಸಲಹೆ ಅಲ್ಲ."
    ),
    "ml": (
        "ഈ രേഖ ഉപയോക്താവ് നൽകിയ വിവരങ്ങളുടെ അടിസ്ഥാനത്തിൽ സ്വയംചാലകമായി സൃഷ്ടിക്കപ്പെട്ടതാണ്. "
        "ഇത് വിവരണ, ഡോക്യുമെന്റേഷൻ ആവശ്യങ്ങൾക്ക് മാത്രമുള്ളതാണ് — നിയമ ഉപദേശമല്ല."
    ),
}


def get_disclaimer(lang: str) -> str:
    return DISCLAIMER_TRANSLATIONS.get(lang, DISCLAIMER_EN)


def _clean_facts(facts: dict) -> dict:
    """Remove empty / null / placeholder values."""
    SKIP = {"", "null", "unknown", "not available", "not applicable",
            "none", "n/a", "na", "not provided", "no"}
    return {k: v for k, v in facts.items()
            if v and str(v).strip().lower() not in SKIP}


def _facts_text(clean: dict) -> str:
    return "\n".join(
        f"  {k.replace('_', ' ').title()}: {v}" for k, v in clean.items()
    )


def _strip_md(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    return text.replace("```", "").strip()


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```\s*$', '', raw, flags=re.MULTILINE)
    return json.loads(raw.strip())


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — LLM classifies intent → document type, authority, reference prefix
# ═══════════════════════════════════════════════════════════════════════════════
def _classify_intent(intent: str, facts: dict) -> dict:
    """
    Fully LLM-driven classification — no hardcoded keyword lists.
    Works for any Indian legal case type.
    """
    clean = _clean_facts(facts)
    prompt = f"""You are an Indian legal document classifier.

Given this legal issue and collected facts, determine:
1. The correct document type (one of the values listed below)
2. The appropriate authority to address the document to
3. A short reference code prefix (3-6 uppercase letters, e.g. FIR, LN, CON)

LEGAL ISSUE: {intent}

FACTS COLLECTED:
{_facts_text(clean)}

DOCUMENT TYPE OPTIONS:
- police_complaint_fir      → crimes, theft, robbery, assault, fraud, cheating, harassment by unknown person
- cyber_fraud_complaint     → online fraud, UPI fraud, phishing, ATM card fraud, OTP fraud, social media scam
- consumer_complaint        → defective product, service deficiency, refund, e-commerce issues
- legal_notice              → landlord-tenant, rent, property, contracts, demand for money/action
- workplace_complaint       → employer issues, salary, harassment at work, wrongful termination
- family_petition           → divorce, custody, maintenance, matrimonial disputes
- banking_complaint         → bank account issues, loan disputes, EMI, cheque bounce
- rti_application           → request for government information under RTI Act
- property_dispute          → land encroachment, boundary dispute, ownership dispute
- insurance_complaint       → insurance claim denial, policy disputes
- education_application     → school/college fee, admission, certificate issues
- civil_petition            → civil court matters not covered above
- general_petition          → any other legal matter

AUTHORITY EXAMPLES (use the most appropriate one for this specific case):
- police: "The Station House Officer"
- consumer: "The President, District Consumer Dispute Redressal Commission"
- workplace: "The HR Manager / Internal Complaints Committee"
- rent/contract: "The Landlord / Opposite Party" (or the specific party's name if known from facts)
- bank: "The Branch Manager, [Bank Name]" (use bank name from facts if available)
- RTI: "The Public Information Officer, [Department Name]"
- court: "The Hon'ble [Court Name]"

Return valid JSON only. No markdown.
{{
  "doc_type": "legal_notice",
  "authority": "The Landlord / Opposite Party",
  "ref_prefix": "LN"
}}
"""
    try:
        resp = llm.invoke([
            SystemMessage(content="Indian legal classifier. Return JSON only. No markdown."),
            HumanMessage(content=prompt)
        ])
        data = _parse_json(resp.content)
        return {
            "doc_type":   data.get("doc_type", "general_petition"),
            "authority":  data.get("authority", "The Concerned Authority"),
            "ref_prefix": data.get("ref_prefix", "SV").upper(),
        }
    except Exception as e:
        print(f"[_classify_intent] error: {e}")
        return {
            "doc_type":   "general_petition",
            "authority":  "The Concerned Authority",
            "ref_prefix": "GEN",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Extract scalar header values (single-line JSON — always reliable)
# ═══════════════════════════════════════════════════════════════════════════════
def _extract_scalars(intent: str, facts: dict, language: str, authority: str) -> dict:
    """
    Extracts only simple one-line values needed for the letter header and signature.
    Single-line strings never break JSON parsing.
    """
    lang_name = LANGUAGE_NAMES.get(language, "English")
    clean = _clean_facts(facts)

    prompt = f"""You are filling header fields for an Indian legal letter.
Language: {lang_name}
Legal issue: {intent}
Authority: {authority}

COLLECTED FACTS:
{_facts_text(clean)}

Extract these values. Each must be a SINGLE LINE — absolutely no newlines inside any value.
Write text values in {lang_name}.

Return JSON only:
{{
  "city_district": "<city from facts, or empty>",
  "state": "<state from facts, or empty>",
  "subject": "<one factual sentence summarising the complaint, max 15 words, in {lang_name}>",
  "full_name": "<complainant full name from facts>",
  "full_address": "<city and state combined, from facts>",
  "loss_or_damages": "<one sentence: what financial or personal harm was suffered — from facts only, in {lang_name}>",
  "phone_number": "<phone number from facts, or empty>",
  "email_address": "<email from facts, or empty>"
}}

Rules:
- If a field is not in the facts, use empty string "".
- No newlines, no markdown, no brackets like [TO BE FILLED].
- Return valid JSON only.
"""
    resp = llm.invoke([
        SystemMessage(content="Header extractor. Single-line values. JSON only."),
        HumanMessage(content=prompt)
    ])

    raw = resp.content.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```\s*$', '', raw, flags=re.MULTILINE)

    try:
        values = json.loads(raw.strip())
    except Exception as e:
        print(f"[_extract_scalars] JSON error: {e}\nRaw: {raw[:300]}")
        city_state = clean.get("user_city_state", "")
        parts = [p.strip() for p in city_state.split(",", 1)] if "," in city_state else [city_state, ""]
        values = {
            "city_district":   parts[0],
            "state":           parts[1] if len(parts) > 1 else "",
            "subject":         f"Complaint regarding {intent}",
            "full_name":       clean.get("user_full_name", ""),
            "full_address":    city_state,
            "loss_or_damages": "inconvenience and distress caused by this matter",
            "phone_number":    clean.get("user_phone", ""),
            "email_address":   clean.get("user_email", ""),
        }

    def v(key, fallback=""):
        val = str(values.get(key, fallback)).strip()
        val = re.sub(r'\[.*?\]', '', val).strip()  # remove any [placeholder] remnants
        return val or fallback

    # Derive fallbacks directly from facts for critical fields
    city_state_fb = clean.get("user_city_state", "")
    return {
        "city_district":   v("city_district"),
        "state":           v("state"),
        "subject":         v("subject", f"Complaint regarding {intent}"),
        "full_name":       v("full_name", clean.get("user_full_name", "")),
        "full_address":    v("full_address", city_state_fb),
        "loss_or_damages": v("loss_or_damages", "inconvenience and distress caused by this matter"),
        "phone_number":    v("phone_number", clean.get("user_phone", "")),
        "email_address":   v("email_address", clean.get("user_email", "")),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Generate body paragraphs as plain text (zero JSON fragility)
# ═══════════════════════════════════════════════════════════════════════════════
def _generate_body(intent: str, facts: dict, language: str) -> tuple:
    """
    Returns (body_text, documents_list) as plain strings.
    Uses a plain-text output format with a simple separator — no JSON at all.
    This is 100% reliable regardless of case type.
    """
    lang_name = LANGUAGE_NAMES.get(language, "English")
    clean = _clean_facts(facts)

    prompt = f"""You are a legal letter writer for India. Write in {lang_name}.

Legal issue: "{intent}"

CONFIRMED FACTS — use ONLY these, do not invent anything:
{_facts_text(clean)}

Write the body of a formal legal letter. Return EXACTLY two sections split by "---DOCUMENTS---".

=== SECTION 1: BODY PARAGRAPHS ===
Write 3 to 5 flowing prose paragraphs covering:
- Paragraph 1: Who the complainant is and the purpose of writing this letter.
- Paragraph 2: What happened — when it happened, where it happened, and what occurred (using the exact facts).
- Paragraph 3: Specific details from the facts (amounts, dates, names, IDs, reference numbers — everything relevant).
- Paragraph 4: Any steps already taken (communication with the other party, bank, police, etc.) — only if facts mention it.
- Paragraph 5: What specific action the complainant is requesting.

---DOCUMENTS---

=== SECTION 2: EVIDENCE / DOCUMENTS LIST ===
List each piece of evidence or document mentioned in the facts.
Format: one numbered item per line starting with "1."
If no evidence is mentioned in the facts, write only: Documents will be submitted upon request.

RULES (follow strictly):
- Write ENTIRELY in {lang_name}. Every word.
- NO section headers, NO labels like "Body:", "Section 1:", etc. — just the content.
- NO markdown — no asterisks, no bold, no bullet points, no hashtags.
- ONLY numbered list allowed (in Section 2).
- Use cautious language: "may relate to", "appears to involve", "situations like this may be addressed under"
- DO NOT cite specific law section numbers.
- DO NOT include the complainant's name, phone, or address in the body paragraphs (those go in the signature).
- DO NOT invent any fact not present in the confirmed facts above.
"""

    resp = llm.invoke([
        SystemMessage(content="Legal letter body writer. Plain text. No markdown. Two sections separated by ---DOCUMENTS---."),
        HumanMessage(content=prompt)
    ])

    raw = _strip_md(resp.content)

    if "---DOCUMENTS---" in raw:
        parts    = raw.split("---DOCUMENTS---", 1)
        body     = parts[0].strip()
        docs     = parts[1].strip()
    else:
        # Fallback: treat everything as body
        body = raw.strip()
        docs = "Documents will be submitted upon request."

    if not docs or docs.lower() in {"", "none", "n/a", "nil"}:
        docs = "Documents will be submitted upon request."

    # ── Strip any placeholder remnants the LLM might have inserted ────────
    _PLACEHOLDER_RE = re.compile(
        r'\[(?:TO BE FILLED|INSERT|SPECIFY|N\/A|TBD|FILL IN|YOUR [A-Z ]+|ADD [A-Z ]+)[^\]]*\]',
        re.IGNORECASE
    )
    body = _PLACEHOLDER_RE.sub('', body)
    docs = _PLACEHOLDER_RE.sub('', docs)

    # Remove lines that became empty after stripping
    body = '\n'.join(ln for ln in body.splitlines() if ln.strip())
    docs = '\n'.join(ln for ln in docs.splitlines() if ln.strip())

    if not docs.strip():
        docs = "Documents will be submitted upon request."

    return body, docs


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — LLM-computed readiness score
# ═══════════════════════════════════════════════════════════════════════════════
def _calculate_readiness_score(intent: str, facts: dict) -> int:
    """
    LLM evaluates the actual evidence present in the facts.
    Falls back to a keyword heuristic if LLM call fails.
    """
    clean = _clean_facts(facts)
    if not clean:
        return 0

    facts_text = _facts_text(clean)

    prompt = f"""You are evaluating evidence quality for an Indian legal complaint.

Legal issue: {intent}

COLLECTED FACTS:
{facts_text}

Score the evidence strength from 0 to 100 based on what is present.

Scoring guide:
- 0-20:  Very limited — only basic details, no documentary/digital/physical evidence
- 21-40: Some evidence — dates/amounts known but no supporting documents yet
- 41-60: Moderate — has some documentary or digital proof (SMS, bank statement, receipt, etc.)
- 61-80: Good — multiple types of evidence (documents + digital proof, or documents + witness)
- 81-100: Strong — comprehensive evidence across multiple categories

Consider:
- Documentary evidence: agreements, receipts, bank statements, notices, certificates
- Digital/payment evidence: SMS alerts, screenshots, emails, UPI/transaction records, WhatsApp chats
- Physical/media evidence: CCTV, photos, videos, recordings, IMEI, vehicle registration
- Witness evidence: named witnesses, bystanders who can testify
- Completeness: full name, dates, amounts, location all present

Return a single integer between 0 and 100. Nothing else.
"""
    try:
        resp = llm.invoke([
            SystemMessage(content="Evidence scorer. Return a single integer only. Nothing else."),
            HumanMessage(content=prompt)
        ])
        score_str = resp.content.strip().split()[0]
        score = int(re.sub(r'[^0-9]', '', score_str))
        return max(0, min(100, score))
    except Exception as e:
        print(f"[_calculate_readiness_score] LLM error, using heuristic: {e}")
        return _heuristic_score(facts)


def _heuristic_score(facts: dict) -> int:
    """Keyword-based fallback score."""
    all_text = " ".join(str(v).lower() for v in facts.values() if v)
    score = 0
    if any(k in all_text for k in ["agreement", "contract", "receipt", "bill", "invoice",
                                     "statement", "notice", "certificate", "deed"]):
        score += 25
    if any(k in all_text for k in ["screenshot", "email", "message", "whatsapp", "sms",
                                     "chat", "upi", "transaction", "payment", "bank", "log"]):
        score += 25
    if any(k in all_text for k in ["photo", "video", "recording", "cctv", "audio",
                                     "imei", "registration", "serial"]):
        score += 25
    if any(k in all_text for k in ["witness", "colleague", "testimony", "statement"]):
        score += 25
    bonus = sum([
        5 if facts.get("user_full_name") else 0,
        5 if any(facts.get(k) for k in ["incident_date", "incident_date_time"]) else 0,
        5 if facts.get("incident_description") else 0,
    ])
    final = min(score + bonus, 100)
    return final if final > 0 else (20 if len(facts) >= 3 else 0)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Assemble final letter using fixed template
# ═══════════════════════════════════════════════════════════════════════════════
def _assemble_letter(scalars: dict, body: str, docs: str,
                     authority: str, today_str: str) -> str:
    """
    Slots all generated content into the fixed Indian legal letter template.
    This function never calls the LLM — pure Python string assembly.
    """
    city_state_parts = [p for p in [scalars["city_district"], scalars["state"]] if p]
    city_state_line  = ", ".join(city_state_parts) or scalars.get("full_address", "India")

    sig = ["Yours faithfully,", "", "___________________________", scalars["full_name"]]
    if scalars["phone_number"]:
        sig.append(scalars["phone_number"])
    if scalars["email_address"]:
        sig.append(scalars["email_address"])

    # Build optional loss/damages sentence only when the value is real
    _SKIP_VALS = {"inconvenience and distress caused by this matter", "", "n/a", "none"}
    loss_sentence = (
        f"Due to this matter, I have suffered {scalars['loss_or_damages']}.\n\n"
        if scalars.get('loss_or_damages', '').strip().lower() not in _SKIP_VALS
           and scalars.get('loss_or_damages', '').strip()
        else ""
    )

    return (
        f"To\n"
        f"{authority}\n"
        f"{city_state_line}\n"
        f"\n"
        f"Date: {today_str}\n"
        f"\n"
        f"Subject: {scalars['subject']}\n"
        f"\n"
        f"Respected Sir/Madam,\n"
        f"\n"
        f"I, {scalars['full_name']}, residing at {scalars['full_address']}, "
        f"respectfully submit the following:\n"
        f"\n"
        f"{body}\n"
        f"\n"
        f"{loss_sentence}"
        f"I therefore request the appropriate authority to kindly take necessary action as per law.\n"
        f"\n"
        f"Relevant documents attached:\n"
        f"{docs}\n"
        f"\n"
        f"Thanking you.\n"
        f"\n"
        f"{chr(10).join(sig)}"
    ).strip()


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def generate_bilingual_document(intent: str, facts: dict, user_language: str) -> dict:
    today_str = date.today().strftime("%d/%m/%Y")

    # Step 1: Classify — fully LLM-driven, works for any case type
    classification = _classify_intent(intent, facts)
    doc_type   = classification["doc_type"]
    authority  = classification["authority"]
    ref_prefix = classification["ref_prefix"]
    ref_number = f"SV/{ref_prefix}/{date.today().year}/{date.today().strftime('%m%d')}/001"

    # Step 2: Readiness score — LLM-evaluated
    readiness = _calculate_readiness_score(intent, facts)

    # Step 3: Scalar header values (user language)
    scalars_user = _extract_scalars(intent, facts, user_language, authority)

    # Step 4: Body prose (user language)
    body_user, docs_user = _generate_body(intent, facts, user_language)

    # Step 5: Assemble user-language letter
    user_lang_content = _assemble_letter(scalars_user, body_user, docs_user, authority, today_str)

    # Step 6: English version (skip duplicate if already English)
    if user_language == "en":
        english_content = user_lang_content
    else:
        scalars_en = _extract_scalars(intent, facts, "en", authority)
        body_en, docs_en = _generate_body(intent, facts, "en")
        english_content = _assemble_letter(scalars_en, body_en, docs_en, authority, today_str)

    return {
        "user_language_content": user_lang_content,
        "english_content":       english_content,
        "document_type":         doc_type,
        "readiness_score":       readiness,
        "user_language":         user_language,
        "disclaimer_en":         DISCLAIMER_EN,
        "disclaimer_user_lang":  get_disclaimer(user_language),
        "reference_number":      ref_number,
    }
