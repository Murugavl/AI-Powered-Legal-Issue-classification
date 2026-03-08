"""
Bilingual Document Generator — Fully case-agnostic.

Document template (From/To formal Indian petition format):

  From
  [Victim's Full Name],
  S/o or D/o [Father/Mother name if available],
  [Full Residential Address],
  [City],
  [District] - [Pincode],
  [State]

  To
  [Authority Name],
  [Authority Address]

  Sub: [Short description of incident]

  Respected Sir/Madam,

  [Body — written in FIRST PERSON by the victim, 3-5 paragraphs]

  Thank You,

  Date: [DD/MM/YYYY]

  Signature: ___________________________
  [Full Name]
  [Phone Number]

  DISCLAIMER — NOT LEGAL ADVICE
  [disclaimer text]

Rules:
  - Every sentence is from the victim's perspective ("I", "my", "me") — never third person
  - No section headings (COMPLAINANT DETAILS, INCIDENT DETAILS etc.)
  - No bold, no markdown, no bullet points in the body
  - Single disclaimer at the bottom only
"""

import json
import re
from datetime import date, datetime
from llm_provider import llm
from langchain_core.messages import HumanMessage, SystemMessage


# ── Language names ─────────────────────────────────────────────────────────────
LANGUAGE_NAMES = {
    "en": "English", "hi": "Hindi",  "ta": "Tamil",
    "te": "Telugu",  "kn": "Kannada","ml": "Malayalam",
    "mr": "Marathi", "bn": "Bengali","gu": "Gujarati",
}

# ── Single disclaimer (used once at the bottom) ────────────────────────────────
DISCLAIMER_EN = (
    "This document has been automatically generated based solely on information provided by the user. "
    "It is intended for informational and documentation purposes only and does not constitute legal advice. "
    "Users are strongly advised to review or verify this document with a qualified legal professional "
    "before official submission."
)

DISCLAIMER_TRANSLATIONS = {
    "ta": (
        "இந்த ஆவணம் பயனர் வழங்கிய தகவல்களின் அடிப்படையில் மட்டுமே தானாக உருவாக்கப்பட்டது. "
        "இது தகவல் மற்றும் ஆவணத் தயாரிப்பு நோக்கத்திற்காக மட்டுமே வழங்கப்படுகிறது. "
        "இது சட்ட ஆலோசனையாக கருதப்படக்கூடாது. "
        "அதிகாரப்பூர்வமாக சமர்ப்பிப்பதற்கு முன் தகுதியான சட்ட நிபுணரால் சரிபார்க்கப்பட வேண்டும்."
    ),
    "hi": (
        "यह दस्तावेज़ उपयोगकर्ता द्वारा प्रदान की गई जानकारी के आधार पर स्वचालित रूप से तैयार किया गया है। "
        "यह केवल सूचना और दस्तावेज़ीकरण उद्देश्यों के लिए है और कानूनी सलाह नहीं है। "
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
    text = re.sub(r'__(.+?)__',     r'\1', text)
    text = re.sub(r'#{1,6}\s*',     '',    text)
    return text.replace("```", "").strip()


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```\s*$',       '', raw, flags=re.MULTILINE)
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        raw = m.group(0)
    return json.loads(raw)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Classify intent → document type, authority, ref prefix
# ═══════════════════════════════════════════════════════════════════════════════
def _classify_intent(intent: str, facts: dict) -> dict:
    clean = _clean_facts(facts)
    prompt = f"""You are an Indian legal document classifier.

Given this legal issue and facts, determine:
1. The correct document type
2. The exact authority name to address the document to
3. A 3-6 letter uppercase reference prefix

LEGAL ISSUE: {intent}

FACTS:
{_facts_text(clean)}

DOCUMENT TYPES:
- police_complaint_fir      → theft, robbery, assault, fraud, cheating, harassment
- cyber_fraud_complaint     → online fraud, UPI fraud, phishing, ATM/card fraud, OTP fraud
- consumer_complaint        → defective product, service deficiency, refund, e-commerce
- legal_notice              → landlord-tenant, contracts, demand for money
- workplace_complaint       → salary, harassment at work, wrongful termination
- family_petition           → divorce, custody, maintenance
- banking_complaint         → bank account, loan, EMI, cheque bounce
- rti_application           → RTI request for government information
- property_dispute          → land encroachment, ownership dispute
- insurance_complaint       → claim denial, policy dispute
- civil_petition            → civil court matters
- general_petition          → any other

AUTHORITY (be specific — use facts where possible):
- Theft/crime → "The Station House Officer" (do NOT include police station name)
- Consumer → "The President, District Consumer Dispute Redressal Commission"
- Employer → "The HR Manager / Internal Complaints Committee"
- Bank → "The Branch Manager" (add bank name from facts if available)
- RTI → "The Public Information Officer"

Return valid JSON only:
{{
  "doc_type": "police_complaint_fir",
  "authority": "The Station House Officer",
  "ref_prefix": "PCF"
}}
"""
    try:
        resp = llm.invoke([
            SystemMessage(content="Legal classifier. JSON only."),
            HumanMessage(content=prompt)
        ])
        data = _parse_json(resp.content)
        return {
            "doc_type":   str(data.get("doc_type",   "general_petition")),
            "authority":  str(data.get("authority",  "The Concerned Authority")),
            "ref_prefix": str(data.get("ref_prefix", "SV")).upper(),
        }
    except Exception as e:
        print(f"[_classify_intent] error: {e}")
        return {"doc_type": "general_petition", "authority": "The Concerned Authority", "ref_prefix": "GEN"}


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Extract scalar header values
# ═══════════════════════════════════════════════════════════════════════════════
def _extract_scalars(intent: str, facts: dict, language: str) -> dict:
    """
    Pulls the scalar values needed to fill the From/To header.
    Falls back directly to facts dict for every field.
    """
    clean = _clean_facts(facts)
    lang_name = LANGUAGE_NAMES.get(language, "English")

    # Build subject from intent
    prompt = f"""Write a short subject line (max 10 words) for an Indian legal complaint.
Language: {lang_name}
Legal issue: {intent}
Facts: {_facts_text(clean)}

Return JSON only: {{"subject": "<one-line subject in {lang_name}>"}}
"""
    subject = ""
    try:
        resp = llm.invoke([
            SystemMessage(content="Subject line writer. JSON only."),
            HumanMessage(content=prompt)
        ])
        d = _parse_json(resp.content)
        subject = d.get("subject", "").strip()
    except Exception as e:
        print(f"[_extract_scalars/subject] {e}")

    # Fallback subject
    if not subject:
        subject = f"Complaint regarding {intent[:60]}"

    def f(*keys, default=""):
        for k in keys:
            v = str(clean.get(k, "")).strip()
            if v and v.lower() not in {"not available", "none", "n/a", ""}:
                return v
        return default

    full_name    = f("user_full_name",  "complainant_name")
    full_address = f("user_full_address", "complainant_address")
    city         = f("user_city_state", "complainant_city_state")
    district     = f("user_district",   "complainant_district")
    state        = f("user_state",      "complainant_state")
    pincode      = f("user_pincode",    "complainant_pincode")
    phone        = f("user_phone",      "complainant_phone")

    # Try to parse city from address if not available directly
    if not city and full_address:
        parts = [p.strip() for p in full_address.split(",")]
        if len(parts) >= 2:
            city = parts[-1]

    return {
        "full_name":    full_name,
        "full_address": full_address,
        "city":         city,
        "district":     district,
        "state":        state,
        "pincode":      pincode,
        "phone":        phone,
        "subject":      subject,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Generate body in FIRST PERSON (plain text, no JSON)
# ═══════════════════════════════════════════════════════════════════════════════
def _generate_body(intent: str, facts: dict, language: str) -> tuple[str, str]:
    """
    Returns (body_paragraphs, documents_list).
    body_paragraphs: 3-5 prose paragraphs, FIRST PERSON ("I", "my", "me").
    documents_list:  numbered list of evidence.
    Both in `language`.
    """
    lang_name = LANGUAGE_NAMES.get(language, "English")
    clean     = _clean_facts(facts)

    prompt = f"""You are writing a formal complaint letter for an Indian citizen to submit to authorities.
Write ENTIRELY in {lang_name}.

Legal issue: "{intent}"

CONFIRMED FACTS — use ONLY these, do not add anything else:
{_facts_text(clean)}

INSTRUCTIONS:
Write 3 to 5 paragraphs describing what happened, IN FIRST PERSON.
Use "I", "my", "me" throughout — NEVER "the complainant", "the victim", "he", "she", or "the owner".
Be factual, specific, and formal. Use only information from the confirmed facts.

Then write "---DOCUMENTS---" on its own line.

Below that, list available evidence as a numbered list:
1. [evidence item]
2. [evidence item]
If no evidence was mentioned, write: Documents will be submitted upon request.

STRICT RULES:
- First person ONLY throughout ("I", "my", "me").
- Write ENTIRELY in {lang_name}.
- No markdown, no asterisks, no bold, no bullet points in the paragraphs.
- Do NOT include name, phone number, or address in the body text.
- Do NOT cite specific law section numbers.
- Do NOT invent facts.
- No placeholders like [TO BE FILLED] or [INSERT].
"""
    try:
        resp = llm.invoke([
            SystemMessage(content="First-person legal letter writer. Plain text only. No markdown."),
            HumanMessage(content=prompt)
        ])
        raw = _strip_md(resp.content)
    except Exception as e:
        print(f"[_generate_body] LLM error: {e}")
        raw = f"I respectfully submit that {intent}.\n\n---DOCUMENTS---\nDocuments will be submitted upon request."

    # Split at ---DOCUMENTS--- marker
    if "---DOCUMENTS---" in raw:
        body_part, doc_part = raw.split("---DOCUMENTS---", 1)
    else:
        lines = raw.strip().splitlines()
        split_idx = None
        for i, line in enumerate(lines):
            if re.match(r'^\d+\.', line.strip()):
                split_idx = i
                break
        if split_idx is not None:
            body_part = "\n".join(lines[:split_idx])
            doc_part  = "\n".join(lines[split_idx:])
        else:
            body_part = raw
            doc_part  = "Documents will be submitted upon request."

    body_paragraphs = body_part.strip()
    documents_list  = doc_part.strip() or "Documents will be submitted upon request."

    return body_paragraphs, documents_list


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Assemble the From/To template
# ═══════════════════════════════════════════════════════════════════════════════
def _assemble_letter(scalars: dict, body_paragraphs: str, documents_list: str,
                     authority: str, today_str: str, disclaimer: str = "",
                     reference_number: str = "") -> str:
    """
    Assembles the Indian petition/complaint in From/To format.

    From
    [Name],
    [Full Address],
    [City],
    [District] - [Pincode],
    [State]

    To
    [Authority],
    [City, District]

    Sub: [subject]

    Respected Sir/Madam,

    [body — first person]

    Relevant documents attached:
    [numbered list]

    Thank You,

    Date: [date]

    Signature: ___________________________
    [Name]
    [Phone]

    DISCLAIMER — NOT LEGAL ADVICE
    [disclaimer]
    """
    name     = scalars.get("full_name",    "")
    address  = scalars.get("full_address", "")
    city     = scalars.get("city",         "")
    district = scalars.get("district",     "")
    state    = scalars.get("state",        "")
    pincode  = scalars.get("pincode",      "")
    phone    = scalars.get("phone",        "")
    subject  = scalars.get("subject",      "")

    # Build district-pincode line
    dist_pin = ""
    if district and pincode:
        dist_pin = f"{district} - {pincode}"
    elif district:
        dist_pin = district
    elif pincode:
        dist_pin = pincode

    # Build authority address line (city + district if available)
    auth_location_parts = [p for p in [city, district] if p]
    auth_location = ", ".join(auth_location_parts) if auth_location_parts else (state or "India")

    # ── FROM block ────────────────────────────────────────────────────────────
    from_lines = ["From"]
    if name:        from_lines.append(f"{name},")
    if address:     from_lines.append(f"{address},")
    if city:        from_lines.append(f"{city},")
    if dist_pin:    from_lines.append(f"{dist_pin},")
    if state:       from_lines.append(state)

    # ── TO block ─────────────────────────────────────────────────────────────
    to_lines = ["To"]
    to_lines.append(f"{authority},")
    to_lines.append(auth_location)

    # ── Assemble ──────────────────────────────────────────────────────────────
    parts = from_lines + [""] + to_lines

    if reference_number:
        parts += ["", f"Ref No: {reference_number}"]

    parts += [
        "",
        f"Sub: {subject}",
        "",
        "Respected Sir/Madam,",
        "",
        body_paragraphs,
        "",
        "Relevant documents attached:",
        documents_list,
        "",
        "Thank You,",
        "",
        f"Date: {today_str}",
        "",
        "Signature: ___________________________",
    ]

    if name:
        parts.append(name)
    if phone:
        parts.append(phone)

    # ── SINGLE DISCLAIMER at bottom ───────────────────────────────────────────
    if disclaimer:
        parts += [
            "",
            "DISCLAIMER — NOT LEGAL ADVICE",
            disclaimer,
        ]

    return "\n".join(parts).strip()


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Readiness score
# ═══════════════════════════════════════════════════════════════════════════════
def _calculate_readiness(intent: str, facts: dict) -> int:
    clean = _clean_facts(facts)
    prompt = f"""Score the evidence readiness of this Indian legal complaint from 0 to 100.

Legal issue: {intent}
Facts:
{_facts_text(clean)}

Scoring:
- 90-100: Strong documentary evidence (receipts, bank statements, SMS, screenshots, witnesses)
- 60-89:  Some evidence but gaps
- 30-59:  Limited evidence, mostly verbal account
- 0-29:   No evidence at all

Return ONLY an integer. No text.
"""
    try:
        resp  = llm.invoke([HumanMessage(content=prompt)])
        score = int(re.search(r'\d+', resp.content).group())
        return max(0, min(100, score))
    except Exception:
        return min(100, len(clean) * 10)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def generate_bilingual_document(intent: str, facts: dict,
                                user_language: str = "en") -> dict:
    today_str    = date.today().strftime("%d/%m/%Y")
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Step 1: Classify
    classification = _classify_intent(intent, facts)
    doc_type   = classification["doc_type"]
    authority  = classification["authority"]
    ref_prefix = classification["ref_prefix"]
    ref_number = f"SV/{ref_prefix}/{date.today().year}/{date.today().strftime('%m%d')}/001"

    # Step 5: Readiness score
    readiness_score = _calculate_readiness(intent, facts)

    # ── English document ──────────────────────────────────────────────────────
    scalars_en        = _extract_scalars(intent, facts, "en")
    body_en, docs_en  = _generate_body(intent, facts, "en")
    english_content   = _assemble_letter(
        scalars_en, body_en, docs_en,
        authority, today_str,
        disclaimer=DISCLAIMER_EN,
        reference_number=ref_number,
    )

    # ── User-language document ────────────────────────────────────────────────
    disc_user = get_disclaimer(user_language)

    if user_language == "en":
        user_lang_content = english_content
    else:
        scalars_user          = _extract_scalars(intent, facts, user_language)
        body_user, docs_user  = _generate_body(intent, facts, user_language)
        user_lang_content     = _assemble_letter(
            scalars_user, body_user, docs_user,
            authority, today_str,
            disclaimer=disc_user,
            reference_number=ref_number,
        )

    return {
        "user_language_content": user_lang_content,
        "english_content":       english_content,
        "document_type":         doc_type,
        "readiness_score":       readiness_score,
        "user_language":         user_language,
        "disclaimer_en":         DISCLAIMER_EN,
        "disclaimer_user_lang":  disc_user,
        "reference_number":      ref_number,
        "generated_at":          generated_at,
    }
