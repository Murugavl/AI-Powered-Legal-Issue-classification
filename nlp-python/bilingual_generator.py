"""
Bilingual Document Generator — Fully case-agnostic.

TWO document modes based on doc_type:

MODE A — "petition_to_authority" (sent to police/court/commission)
  Used for: police_complaint_fir, cyber_fraud_complaint, consumer_complaint,
            banking_complaint, insurance_complaint, rti_application,
            workplace_complaint, property_dispute, civil_petition, general_petition

  Layout:
    Ref No: ...
    Date: DD/MM/YYYY

    From
    [Sender Name],
    [Sender Address],
    [District - Pincode],
    [State]

    To
    [Authority Name],          <- government/institutional authority
    [District, State]

    Sub: ...
    Respected Sir/Madam,
    [3 body paragraphs - first person]
    Relevant documents attached:
    1. ...
    Thank You,
    Signature: ___
    [Name]
    [Phone]
    DISCLAIMER

MODE B - "demand_letter_to_party" (sent directly to other party)
  Used for: legal_notice, family_petition (maintenance demand), workplace_complaint
            when directed at employer directly

  Layout:
    Ref No: ...
    Date: DD/MM/YYYY

    From
    [Sender Name],
    [Sender Address],
    [District - Pincode],
    [State]

    To
    [Other Party Name],        <- landlord / employer / debtor etc.
    [Other Party Address/City]

    Sub: ...
    Dear Mr./Ms. [Other Party Name],
    [3 body paragraphs - first person, assertive demand tone]
    Yours faithfully,
    Signature: ___
    [Name]
    [Phone]
    DISCLAIMER

Rules for all modes:
  - Date always at the very TOP before From
  - First person throughout ("I", "my", "me") - never third person
  - No section headings (COMPLAINANT DETAILS, INCIDENT DETAILS etc.)
  - No filler phrases ("I hope", "I trust", "I am confident")
  - Evidence list uses actual items, not placeholder text
  - No disclaimer in document
"""

import json
import re
from datetime import date, datetime
from llm_provider import llm
from langchain_core.messages import HumanMessage, SystemMessage


LANGUAGE_NAMES = {
    "en": "English", "hi": "Hindi",  "ta": "Tamil",
    "te": "Telugu",  "kn": "Kannada","ml": "Malayalam",
    "mr": "Marathi", "bn": "Bengali","gu": "Gujarati",
}

# ── Helpers ────────────────────────────────────────────────────────────────
def strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__',     r'\1', text)
    text = re.sub(r'#{1,6}\s+',     '',    text)
    return text.replace("```", "").strip()

def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```\s*$',       '', raw, flags=re.MULTILINE)
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match: raw = match.group(0)
    return json.loads(raw)

DOC_LABELS = {
    "en": {
        "date": "Date:", "from": "From:", "to": "To:", "sub": "Sub:",
        "respected": "Respected Sir/Madam,", "thank_you": "Thank you.",
        "faithfully": "Yours faithfully,", "signature": "(Signature)",
        "name": "Name:", "contact": "Contact:", "place": "Place:",
        "legal_provs": "Applicable Legal Provisions:",
        "enclosures": "Enclosures:",
        "attachments": "Relevant documents attached:",
        "dear": "Dear",
    },
    "ta": {
        "date": "தேதி:", "from": "அனுப்புநர்:", "to": "பெறுநர்:", "sub": "பொருள்:",
        "respected": "மதிப்பிற்குரிய ஐயா/அம்மா,", "thank_you": "நன்றி.",
        "faithfully": "இப்படிக்கு,", "signature": "(கையெழுத்து)",
        "name": "பெயர்:", "contact": "தொடர்பு எண்:", "place": "இடம்:",
        "legal_provs": "பொருந்தக்கூடிய சட்ட விதிகள்:",
        "enclosures": "இணைப்புகள்:",
        "attachments": "இணைக்கப்பட்டுள்ள ஆவணங்கள்:",
        "dear": "மதிப்பிற்குரிய",
    },
    "hi": {
        "date": "दिनांक:", "from": "प्रेषक:", "to": "सेवा में:", "sub": "विषय:",
        "respected": "आदरणीय महोदय/महोदया,", "thank_you": "धन्यवाद।",
        "faithfully": "भवदीय,", "signature": "(हस्ताक्षर)",
        "name": "नाम:", "contact": "संपर्क:", "place": "स्थान:",
        "legal_provs": "लागू कानूनी प्रावधान:",
        "enclosures": "संलग्नक:",
        "attachments": "संलग्न दस्तावेज:",
        "dear": "प्रिय",
    }
}

TAMIL_DAYS = {
    0: "திங்கள்", 1: "செவ்வாய்", 2: "புதன்",
    3: "வியாழன்", 4: "வெள்ளி", 5: "சனி", 6: "ஞாயிறு"
}

# Doc types that go DIRECTLY to the other party (not an authority)
DEMAND_LETTER_TYPES = {
    "legal_notice",      # landlord, tenant, debtor, contractor disputes
    "family_petition",   # maintenance demand to spouse/family member
}

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


def is_real_value(v) -> bool:
    """Check if a value is real (not empty, null, or placeholder)"""
    if v is None:
        return False
    SKIP_VALUES = {"", "null", "unknown", "not available", "not applicable",
                   "none", "n/a", "na", "not provided"}
    return str(v).strip().lower() not in SKIP_VALUES and len(str(v).strip()) > 0


def _clean_facts(facts: dict) -> dict:
    SKIP = {"", "null", "unknown", "not available", "not applicable",
            "none", "n/a", "na", "not provided", "no"}
    return {k: v for k, v in facts.items()
            if v and str(v).strip().lower() not in SKIP}


def _facts_text(clean: dict) -> str:
    return "\n".join(
        f"  {k.replace('_', ' ').title()}: {v}" for k, v in clean.items()
    )


def _norm(s: str) -> str:
    """Normalise for overlap detection: lowercase, strip spaces/dashes/commas."""
    s = s.lower()
    s = re.sub(r'[\s,\-\u2013\u2014]+', '', s)
    return s


def _already_in(text: str, value: str) -> bool:
    if not value or not text:
        return True
    return _norm(value) in _norm(text)


# ---------------------------------------------------------------------------
# STEP 1 - Classify intent
# ---------------------------------------------------------------------------
def _classify_intent(intent: str, facts: dict) -> dict:
    clean = _clean_facts(facts)
    prompt = f"""You are an Indian legal document classifier with deep knowledge of Indian law.
Carefully read the legal issue and facts, then make the CORRECT classification.

LEGAL ISSUE: {intent}

FACTS:
{_facts_text(clean)}

CLASSIFICATION RULES:

STEP 1 - Determine the nature of the dispute:
  A) Criminal matter (theft, robbery, assault, serious criminal cheating/fraud by strangers, harassment) -> police or court
  B) Civil/contractual dispute between two private parties -> demand letter / legal notice to the OTHER PARTY
     CRITICAL: Disputes over rental deposits, rent, unpaid loans, breach of contract, employment dues
     are ALWAYS CIVIL (legal_notice). Do NOT classify as police_complaint_fir.
  C) Consumer grievance (defective product, e-commerce, insurance, telecom) -> consumer commission
  D) Government/public grievance (RTI, government scheme) -> government authority

STEP 2 - Pick the most logical doc_type:
  Valid values: police_complaint_fir, cyber_fraud_complaint, consumer_complaint,
  legal_notice, workplace_complaint, family_petition, banking_complaint,
  rti_application, property_dispute, insurance_complaint, civil_petition, general_petition

STEP 3 - Determine the correct recipient.
  If AUTHORITY -> fill "authority" with official title (e.g. "The Station House Officer").
  If PRIVATE PARTY -> fill "other_party" with their name, "other_party_location" with address.

IMPORTANT CLASSIFICATION RULES:
  - Threatening phone calls, extortion, blackmail = Harassment / Threat -> police_complaint_fir
  - Online fraud, UPI fraud = cyber_fraud_complaint
  - Defective product/service = consumer_complaint
  - Salary dispute = workplace_complaint
  - NEVER classify threatening calls as general_petition

Return valid JSON only - no markdown:
{{
  "doc_type": "legal_notice",
  "authority": "",
  "other_party": "R. Kumar",
  "other_party_location": "Salem, Tamil Nadu",
  "ref_prefix": "LN",
  "reasoning": "civil contractual dispute"
}}
"""
    try:
        resp = llm.invoke([
            SystemMessage(content="Indian legal classifier. Return JSON only, no markdown."),
            HumanMessage(content=prompt)
        ])
        data = _parse_json(resp.content)
        doc_type = str(data.get("doc_type", "general_petition")).strip()
        print(f"[_classify_intent] doc_type={doc_type}, reasoning={data.get('reasoning','')}")

        authority_location = ""
        authority_name = str(data.get("authority", "The Concerned Authority")).strip()

        police_station   = str(facts.get("police_station_name", "")).strip()
        forum_district   = str(facts.get("consumer_forum_district", "")).strip()
        bank_branch      = str(facts.get("bank_branch_details", "")).strip()
        insurance_office = str(facts.get("insurance_office_location", "")).strip()
        employer_address = str(facts.get("employer_name_address", "")).strip()
        rti_department   = str(facts.get("rti_department_name", "")).strip()

        if police_station and is_real_value(police_station):
            authority_location = police_station
            if "police station" not in police_station.lower():
                authority_location = f"{police_station} Police Station"
            authority_name = "The Station House Officer"

        elif bank_branch and is_real_value(bank_branch):
            authority_location = bank_branch
            authority_name = "The Branch Manager"

        elif forum_district and is_real_value(forum_district):
            if "district consumer forum" in forum_district.lower() or "consumer forum" in forum_district.lower():
                authority_location = forum_district
            else:
                authority_location = f"District Consumer Forum, {forum_district}"
            authority_name = "The President, District Consumer Disputes Redressal Commission"

        elif insurance_office and is_real_value(insurance_office):
            authority_location = insurance_office
            authority_name = "The Branch Manager"

        elif rti_department and is_real_value(rti_department):
            authority_location = rti_department

        elif employer_address and is_real_value(employer_address):
            authority_location = employer_address

        if not authority_location:
            district = str(facts.get("user_district", "")).strip()
            state    = str(facts.get("user_state", "")).strip()
            authority_location = ", ".join(p for p in [district, state] if p and is_real_value(p))

        if not authority_location:
            authority_location = "India"

        llm_other_party     = str(data.get("other_party", "")).strip()
        llm_other_party_loc = str(data.get("other_party_location", "")).strip()

        known_other_party = (
            str(facts.get("other_party_name",     "")).strip() or
            str(facts.get("landlord_name_contact", "")).strip() or
            str(facts.get("landlord_name",         "")).strip()
        )
        other_party_final = known_other_party if is_real_value(known_other_party) else llm_other_party

        known_other_party_loc = (
            str(facts.get("property_exact_location", "")).strip() or
            str(facts.get("rental_property_address", "")).strip() or
            llm_other_party_loc
        )

        return {
            "doc_type":             doc_type,
            "authority":            authority_name,
            "authority_location":   authority_location,
            "other_party":          other_party_final,
            "other_party_location": known_other_party_loc,
            "ref_prefix":           str(data.get("ref_prefix", "SV")).upper().strip(),
            "is_demand_letter":     doc_type in DEMAND_LETTER_TYPES,
        }
    except Exception as e:
        print(f"[_classify_intent] error: {e}")
        return {
            "doc_type": "general_petition",
            "authority": "The Concerned Authority",
            "authority_location": "India",
            "other_party": "",
            "other_party_location": "",
            "ref_prefix": "GEN",
            "is_demand_letter": False,
        }


# ---------------------------------------------------------------------------
# STEP 2 - Extract scalar header values
# ---------------------------------------------------------------------------
def _extract_scalars(intent: str, facts: dict, language: str) -> dict:
    clean     = _clean_facts(facts)
    lang_name = LANGUAGE_NAMES.get(language, "English")

    subject = ""
    try:
        resp = llm.invoke([
            SystemMessage(content="Subject line writer. JSON only."),
            HumanMessage(content=(
                f"Write a short subject line (max 10 words) for an Indian legal complaint.\n"
                f"Language: {lang_name}\nLegal issue: {intent}\n"
                f"Facts: {_facts_text(clean)}\n\n"
                f'Return JSON only: {{"subject": "<one-line subject in {lang_name}>"}}'
            ))
        ])
        subject = _parse_json(resp.content).get("subject", "").strip()
    except Exception as e:
        print(f"[_extract_scalars/subject] {e}")
    if not subject:
        subject = f"Complaint regarding {intent[:60]}"

    def fv(*keys, default=""):
        for k in keys:
            v = str(clean.get(k, "")).strip()
            if v and v.lower() not in {"not available", "none", "n/a", ""}:
                return v
        return default

    full_name    = fv("user_full_name",    "complainant_name")
    full_address = fv("user_full_address", "complainant_address")
    district     = fv("user_district",     "complainant_district")
    state        = fv("user_state",        "complainant_state")
    pincode      = fv("user_pincode",      "complainant_pincode")
    phone        = fv("user_phone",        "complainant_phone")

    return {
        "full_name":     full_name,
        "full_address":  full_address,
        "district":      "" if _already_in(full_address, district) else district,
        "state":         "" if _already_in(full_address, state)    else state,
        "pincode":       "" if _already_in(full_address, pincode)  else pincode,
        "district_raw":  district,
        "state_raw":     state,
        "phone":         phone,
        "subject":       subject,
    }


# ---------------------------------------------------------------------------
# STEP 3 - Generate body + evidence list
# ---------------------------------------------------------------------------
def _generate_body(intent: str, facts: dict, language: str,
                   is_demand_letter: bool = False,
                   other_party: str = "") -> tuple:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    clean     = _clean_facts(facts)

    evidence_keys = ["evidence_available", "evidence_details",
                     "documents_available", "proof_available"]
    evidence_raw_parts = []
    for k in evidence_keys:
        v = str(clean.get(k, "")).strip()
        if v:
            doc_keywords = ["receipt", "bill", "sms", "screenshot", "photo", "video",
                            "cctv", "statement", "certificate", "agreement", "contract",
                            "report", "invoice", "bank", "email", "whatsapp", "message",
                            "proof", "record", "document", "evidence"]
            has_doc_keyword = any(kw in v.lower() for kw in doc_keywords)
            if has_doc_keyword or len(v) < 50:
                evidence_raw_parts.append(v)
    evidence_raw = " | ".join(evidence_raw_parts).strip()

    if is_demand_letter:
        tone_instruction = (
            "This is a formal DEMAND LETTER / LEGAL NOTICE sent directly to the other party.\n"
            "Tone: firm, assertive, and formal.\n"
            f"The letter is addressed to: {other_party if other_party else 'the other party'}.\n"
            "Paragraph 3: one clear demand with a deadline, state consequences if not complied.\n"
        )
    else:
        tone_instruction = (
            "This is a formal COMPLAINT / PETITION to a government authority.\n"
            "Tone: respectful and factual.\n"
            "Paragraph 3: clearly request the authority to take specific action.\n"
        )

    prompt = f"""You are a formal Indian legal document writer.
Write the letter ENTIRELY in {lang_name} script (except for proper names/IDs).

PRIME DIRECTIVE:
Use professional, formal legal vocabulary.
If writing in Tamil, use proper formal Tamil (not conversational).
Ensure the tone is respectful yet factual.
Do NOT use robotic or overly simplified translations.

Legal issue: "{intent}"

CONFIRMED FACTS - use ONLY these:
{_facts_text(clean)}

{tone_instruction}

PART 1: BODY (exactly 3 SHORT paragraphs)
Write IN FIRST PERSON ("I", "my", "me").
Each paragraph: 2 to 3 sentences MAXIMUM.

Paragraph 1 - Facts: What happened. Dates, amounts, agreed terms.
Paragraph 2 - Harm: Specific loss or harm caused and why other party is at fault.
Paragraph 3 - Demand/Request: Specific action demanded or requested, with deadline if applicable.

CRITICAL RULES:
- 2-3 sentences per paragraph ONLY
- First person ONLY: "I", "my", "me"
- Include specific amounts (Rs.), dates (DD/MM/YYYY), and names from facts
- NO filler phrases
- No markdown, no bold, no bullets
- Do NOT include sender's name, phone, or address in body text
- Do NOT cite law section numbers
- Do NOT invent facts

Write this EXACT marker after the 3 paragraphs:
---DOCUMENTS---

PART 2: EVIDENCE LIST
Evidence from facts: "{evidence_raw}"

Rules:
- If specific document types mentioned -> list EACH as a numbered item.
- If no specific documents -> write: 1. Relevant documents and evidence will be submitted upon request.
- NEVER list complaint narrative as evidence.
"""
    try:
        resp = llm.invoke([
            SystemMessage(content="Legal letter writer. Plain text only. No markdown."),
            HumanMessage(content=prompt)
        ])
        raw = strip_markdown(resp.content)
    except Exception as e:
        print(f"[_generate_body] error: {e}")
        raw = ("I respectfully submit the following.\n\n"
               "I have suffered loss due to the matter described.\n\n"
               "I request immediate resolution of this matter.\n\n"
               "---DOCUMENTS---\n"
               "1. Relevant documents and evidence will be submitted upon request.")

    if "---DOCUMENTS---" in raw:
        body_part, doc_part = raw.split("---DOCUMENTS---", 1)
    else:
        lines = raw.strip().splitlines()
        split_idx = next(
            (i for i, ln in enumerate(lines) if re.match(r'^\d+\.', ln.strip())),
            None
        )
        if split_idx is not None:
            body_part = "\n".join(lines[:split_idx])
            doc_part  = "\n".join(lines[split_idx:])
        else:
            body_part = raw
            doc_part  = ""

    body_paragraphs = body_part.strip()
    documents_list  = doc_part.strip() or "1. Relevant documents and evidence will be submitted upon request."

    # Strip phone numbers leaked into body
    body_paragraphs = re.sub(r'\b(?:\+91[\s\-]?)?[6-9]\d{9}\b', '[number redacted]', body_paragraphs)
    body_paragraphs = re.sub(r'\b0\d{2,4}[\s\-]?\d{6,8}\b', '[number redacted]', body_paragraphs)

    return body_paragraphs, documents_list


# ---------------------------------------------------------------------------
# STEP 4A - Applicable laws
# ---------------------------------------------------------------------------
def get_applicable_laws(doc_type: str, facts: dict) -> list:
    applicable_laws = []
    facts_text = " ".join(str(v).lower() for v in facts.values() if v)

    if doc_type == "police_complaint_fir":
        applicable_laws.append("Code of Criminal Procedure 1973, Section 154 - Registration of FIR")
        if any(k in facts_text for k in ["theft", "stolen", "robbery", "burglary", "stole"]):
            applicable_laws.append("Indian Penal Code 1860, Section 379 - Punishment for theft")
            if "house" in facts_text or "home" in facts_text:
                applicable_laws.append("Indian Penal Code 1860, Section 380 - Theft in dwelling house")
        if any(k in facts_text for k in ["assault", "attack", "beat", "hit", "violence", "hurt"]):
            applicable_laws.append("Indian Penal Code 1860, Section 323 - Voluntarily causing hurt")
        if any(k in facts_text for k in ["cheat", "fraud", "dishonest", "deceive"]):
            applicable_laws.append("Indian Penal Code 1860, Section 420 - Cheating")
        if any(k in facts_text for k in ["harass", "modesty", "woman", "female", "girl"]):
            applicable_laws.append("Indian Penal Code 1860, Section 354 - Outraging modesty")
            applicable_laws.append("Indian Penal Code 1860, Section 509 - Insulting modesty of a woman")
        if any(k in facts_text for k in ["threat", "intimidate", "blackmail"]):
            applicable_laws.append("Indian Penal Code 1860, Section 506 - Criminal intimidation")

    elif doc_type == "cyber_fraud_complaint":
        applicable_laws.append("Information Technology Act 2000, Section 66C - Identity theft")
        applicable_laws.append("Information Technology Act 2000, Section 66D - Cheating by personation")
        applicable_laws.append("Indian Penal Code 1860, Section 420 - Cheating")

    elif doc_type == "consumer_complaint":
        applicable_laws.append("Consumer Protection Act 2019, Section 35 - Consumer disputes redressal")
        applicable_laws.append("Consumer Protection Act 2019, Section 2(7) - Definition of consumer")
        if any(k in facts_text for k in ["defective", "defect", "faulty", "not working"]):
            applicable_laws.append("Consumer Protection Act 2019, Section 2(10) - Definition of defect")
        if any(k in facts_text for k in ["unfair", "misleading"]):
            applicable_laws.append("Consumer Protection Act 2019, Section 2(47) - Unfair trade practice")

    elif doc_type == "legal_notice":
        if any(k in facts_text for k in ["property", "land", "house", "rent", "landlord", "tenant"]):
            applicable_laws.append("Transfer of Property Act 1882")
            applicable_laws.append("Specific Relief Act 1963, Section 9 - Specific performance")
        if any(k in facts_text for k in ["contract", "agreement", "breach"]):
            applicable_laws.append("Indian Contract Act 1872, Section 73 - Compensation for breach")
        if any(k in facts_text for k in ["loan", "debt", "owe", "borrow", "repay"]):
            applicable_laws.append("Civil Procedure Code 1908, Order 37 - Summary Procedure")

    elif doc_type == "workplace_complaint":
        applicable_laws.append("Industrial Disputes Act 1947, Section 2(s) - Definition of workman")
        if any(k in facts_text for k in ["salary", "wage", "payment", "unpaid"]):
            applicable_laws.append("Payment of Wages Act 1936, Section 5 - Time of payment")
        if any(k in facts_text for k in ["terminate", "dismiss", "fire", "retrench"]):
            applicable_laws.append("Industrial Disputes Act 1947, Section 25F - Retrenchment conditions")
        if any(k in facts_text for k in ["harassment", "sexual", "misconduct"]):
            applicable_laws.append("Sexual Harassment of Women at Workplace Act 2013")

    elif doc_type == "banking_complaint":
        applicable_laws.append("Banking Regulation Act 1949")
        applicable_laws.append("Reserve Bank of India Act 1934")
        if any(k in facts_text for k in ["unauthorized", "debit", "transaction", "fraud"]):
            applicable_laws.append("Payment and Settlement Systems Act 2007")

    elif doc_type == "insurance_complaint":
        applicable_laws.append("Insurance Act 1938")
        applicable_laws.append("Insurance Regulatory and Development Authority Act 1999")
        if any(k in facts_text for k in ["claim", "reject", "denial"]):
            applicable_laws.append("IRDAI (Protection of Policyholders' Interests) Regulations 2017")

    elif doc_type == "rti_application":
        applicable_laws.append("Right to Information Act 2005, Section 6 - Request for information")
        applicable_laws.append("Right to Information Act 2005, Section 7 - Disposal of request")

    elif doc_type == "property_dispute":
        applicable_laws.append("Transfer of Property Act 1882")
        applicable_laws.append("Indian Easements Act 1882")
        if any(k in facts_text for k in ["encroachment", "boundary", "trespass"]):
            applicable_laws.append("Specific Relief Act 1963, Section 38 - Perpetual injunction")

    elif doc_type == "family_petition":
        if any(k in facts_text for k in ["maintenance", "alimony", "spouse", "wife", "husband"]):
            applicable_laws.append("Code of Criminal Procedure 1973, Section 125 - Maintenance")
            applicable_laws.append("Hindu Marriage Act 1955, Section 24 - Maintenance pendente lite")
        if any(k in facts_text for k in ["divorce", "separation"]):
            applicable_laws.append("Hindu Marriage Act 1955, Section 13 - Divorce")

    seen = set()
    return [law for law in applicable_laws if not (law in seen or seen.add(law))]


# ---------------------------------------------------------------------------
# Helper: split address into lines, merging number-only prefixes
# ---------------------------------------------------------------------------
def _split_address_lines(raw_addr: str) -> list:
    """Split comma-separated address into clean lines.
    Merges a standalone number prefix (e.g. "7") with the next part so
    "7, Mariamman Koil Street" renders as one line, not two."""
    if not raw_addr:
        return []
    raw_parts = [p.strip().rstrip(',').strip() for p in raw_addr.split(',')]
    merged = []
    i = 0
    while i < len(raw_parts):
        part = raw_parts[i]
        # If this part is just a number or short plot prefix, merge with next part
        if part and re.match(r'^\d+[A-Za-z]?$', part) and i + 1 < len(raw_parts):
            merged.append(f"{part}, {raw_parts[i + 1]}")
            i += 2
        elif part:
            merged.append(part)
            i += 1
        else:
            i += 1
    return merged


# ---------------------------------------------------------------------------
# STEP 4A - Assemble petition to authority
# ---------------------------------------------------------------------------
def _assemble_petition(scalars: dict, body_paragraphs: str, documents_list: str,
                       authority: str, authority_location: str, today_str: str,
                       doc_type: str, facts: dict,
                       disclaimer: str = "", reference_number: str = "") -> str:
    lbl = DOC_LABELS.get(scalars.get("user_language", "en"), DOC_LABELS["en"])
    language = scalars.get("user_language", "en")

    name     = scalars.get("full_name",    "")
    address  = scalars.get("full_address", "")
    phone    = scalars.get("phone",        "")
    subject  = scalars.get("subject",      "")
    district_raw = scalars.get("district_raw", "")
    state_raw    = scalars.get("state_raw",    "")

    # Format date with regional day name if Tamil
    today    = date.today()
    day_name = TAMIL_DAYS[today.weekday()] if language == "ta" else today.strftime("%A")
    date_str = today.strftime("%d/%m/%Y") + f" ({day_name})"
    today_str = date_str  # sync

    auth_loc   = authority_location if authority_location else "India"
    addr_clean = re.sub(r'[\s,\-\u2013\u2014]+$', '', address).strip() if address else ""

    applicable_laws = get_applicable_laws(doc_type, facts)
    addr_lines      = _split_address_lines(addr_clean)

    parts = []
    parts.append(f"{lbl['date']} {date_str}")
    parts.append("")

    parts.append(lbl['from'])
    if name:
        parts.append(name.strip().rstrip(','))
    for line in addr_lines:
        parts.append(line)
    parts.append("")

    parts.append(lbl['to'])
    if authority:
        parts.append(authority.strip().rstrip(','))
    if auth_loc:
        auth_loc_normalized = auth_loc.strip().rstrip(',')
        if '\n' in auth_loc_normalized:
            loc_lines = [l.strip().rstrip(',') for l in auth_loc_normalized.split('\n') if l.strip()]
        elif auth_loc_normalized.count(',') >= 2:
            loc_lines = [p.strip().rstrip(',') for p in auth_loc_normalized.split(',') if p.strip()]
        else:
            loc_lines = [auth_loc_normalized]
        for loc_line in loc_lines:
            if loc_line and loc_line != authority.strip():
                parts.append(loc_line)
    parts.append("")
    parts.append(f"{lbl['sub']} {subject}")
    parts.append("")
    parts.append(lbl['respected'])
    parts.append("")

    paragraphs = [p.strip() for p in re.split(r'\n{2,}', body_paragraphs) if p.strip()]
    parts.append("\n\n".join(paragraphs))
    parts.append("")

    if applicable_laws:
        parts.append(lbl['legal_provs'])
        for law in applicable_laws:
            parts.append(f"  \u2022 {law}")
        parts.append("")

    parts.append(lbl['attachments'])
    for line in documents_list.splitlines():
        stripped = re.sub(r'^\d+\.\s*', '', line.strip())
        if stripped:
            parts.append(f"  \u2022 {stripped}")
    parts.append("")
    parts.append(lbl['thank_you'])
    parts.append("")
    parts.append(lbl['faithfully'])
    parts.append("")
    parts.append("")
    parts.append("________________________")
    parts.append(lbl['signature'])
    parts.append("")
    if name:
        parts.append(f"{lbl['name']} {name}")
    if phone:
        parts.append(f"{lbl['contact']} {phone}")
    place = district_raw or state_raw or ""
    if place:
        parts.append(f"{lbl['place']} {place}")
    parts.append(f"{lbl['date']} {today_str}")
    if disclaimer:
        parts.append("")
        parts.append("DISCLAIMER")
        parts.append("")
        parts.append(disclaimer)

    return "\n".join(parts).strip()


# ---------------------------------------------------------------------------
# STEP 4B - Assemble demand letter to other party
# ---------------------------------------------------------------------------
def _assemble_demand_letter(scalars: dict, body_paragraphs: str, documents_list: str,
                            other_party: str, other_party_location: str,
                            today_str: str, doc_type: str, facts: dict,
                            disclaimer: str = "", reference_number: str = "") -> str:
    lbl = DOC_LABELS.get(scalars.get("user_language", "en"), DOC_LABELS["en"])
    if scalars.get("user_language") == "en": lbl = DOC_LABELS["en"] # fallback

    name     = scalars.get("full_name",    "")
    address  = scalars.get("full_address", "")
    phone    = scalars.get("phone",        "")
    subject  = scalars.get("subject",      "")
    district_raw = scalars.get("district_raw", "")
    state_raw    = scalars.get("state_raw",    "")

    # Format date with regional day name if Tamil
    today    = date.today()
    language = scalars.get("user_language", "en")
    day_name = TAMIL_DAYS[today.weekday()] if language == "ta" else today.strftime("%A")
    date_str = today.strftime("%d/%m/%Y") + f" ({day_name})"
    today_str = date_str # sync

    addr_clean = re.sub(r'[\s,\-\u2013\u2014]+$', '', address).strip() if address else ""
    salutation = f"{lbl['dear']} {other_party}," if other_party else lbl['respected']

    applicable_laws = get_applicable_laws(doc_type, facts)
    addr_lines      = _split_address_lines(addr_clean)

    parts = []
    parts.append(f"{lbl['date']} {date_str}")
    parts.append("")

    parts.append(lbl['from'])
    if name:
        parts.append(name.strip().rstrip(','))
    for line in addr_lines:
        parts.append(line)
    parts.append("")

    parts.append(lbl['to'])
    if other_party:
        parts.append(other_party.strip().rstrip(','))
    if other_party_location:
        for p in other_party_location.split(','):
            loc_part = p.strip().rstrip(',')
            if loc_part:
                parts.append(loc_part)
    parts.append("")
    parts.append(f"{lbl['sub']} {subject}")
    parts.append("")
    parts.append(salutation)
    parts.append("")

    paragraphs = [p.strip() for p in re.split(r'\n{2,}', body_paragraphs) if p.strip()]
    parts.append("\n\n".join(paragraphs))
    parts.append("")

    if applicable_laws:
        parts.append(lbl['legal_provs'])
        for law in applicable_laws:
            parts.append(f"  \u2022 {law}")
        parts.append("")

    has_real_docs = any(
        line.strip() and not line.strip().lower().startswith("relevant documents and evidence will be submitted")
        for line in documents_list.splitlines() if re.match(r'^\d+\.', line.strip())
    )
    if has_real_docs:
        parts.append(lbl['enclosures'])
        for line in documents_list.splitlines():
            stripped = re.sub(r'^\d+\.\s*', '', line.strip())
            if stripped:
                parts.append(f"  \u2022 {stripped}")
        parts.append("")

    parts.append(lbl['thank_you'])
    parts.append("")
    parts.append(lbl['faithfully'])
    parts.append("")
    parts.append("")
    parts.append("________________________")
    parts.append(lbl['signature'])
    parts.append("")
    if name:
        parts.append(f"{lbl['name']} {name}")
    if phone:
        parts.append(f"{lbl['contact']} {phone}")
    place = district_raw or state_raw or ""
    if place:
        parts.append(f"{lbl['place']} {place}")
    parts.append(f"{lbl['date']} {today_str}")
    if disclaimer:
        parts.append("")
        parts.append("DISCLAIMER")
        parts.append("")
        parts.append(disclaimer)

    return "\n".join(parts).strip()


# ---------------------------------------------------------------------------
# STEP 5 - Readiness score
# ---------------------------------------------------------------------------
def _calculate_readiness(intent: str, facts: dict) -> int:
    clean = _clean_facts(facts)
    prompt = (
        f"Score the evidence readiness of this Indian legal complaint from 0 to 100.\n\n"
        f"Legal issue: {intent}\nFacts:\n{_facts_text(clean)}\n\n"
        "Scoring:\n"
        "- 90-100: Strong documentary evidence\n"
        "- 60-89:  Some evidence but gaps\n"
        "- 30-59:  Limited evidence, mostly verbal\n"
        "- 0-29:   No evidence at all\n\n"
        "Return ONLY an integer. No text."
    )
    try:
        resp  = llm.invoke([HumanMessage(content=prompt)])
        score = int(re.search(r'\d+', resp.content).group())
        return max(0, min(100, score))
    except Exception:
        return min(100, len(clean) * 10)


# ---------------------------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------------------------
def generate_bilingual_document(intent: str, facts: dict,
                                user_language: str = "en") -> dict:
    today_str    = date.today().strftime("%d/%m/%Y")
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    classification     = _classify_intent(intent, facts)
    doc_type           = classification["doc_type"]
    authority          = classification["authority"]
    authority_location = classification.get("authority_location", "India")
    other_party        = classification["other_party"]
    other_party_loc    = classification["other_party_location"]
    ref_prefix         = classification["ref_prefix"]
    is_demand_letter   = classification["is_demand_letter"]
    ref_number         = f"SV/{ref_prefix}/{date.today().year}/{date.today().strftime('%m%d')}/001"

    readiness_score = _calculate_readiness(intent, facts)

    # ── Pre-translate header info/facts for bilingual consistency ───────────
    translated_classification = classification.copy()
    translated_facts          = facts.copy()

    if user_language != "en":
        # 1. Translate Classification fields to User Language
        fields_to_translate = ["authority", "authority_location", "other_party", "other_party_location"]
        text_to_translate   = " | ".join(str(classification.get(f, "")) for f in fields_to_translate)
        
        prompt = f"""You are a legal translator. Translate these Indian legal entity names and locations into formal {LANGUAGE_NAMES.get(user_language, 'Tamil')}.
Return as a pip-separated list in the same order. 

TEXT: {text_to_translate}

RULES:
- Formal vocabulary only.
- Respond ONLY with the piped translations. No commentary.
"""
        try:
            resp = llm.invoke([HumanMessage(content=prompt)])
            vals = [v.strip().strip('"').strip("'") for v in resp.content.split("|")]
            for i, f in enumerate(fields_to_translate):
                if i < len(vals) and vals[i]: 
                    translated_classification[f] = vals[i]
        except Exception: pass

        # 2. Translate Facts to English (for the English copy)
        # Identify non-English values in facts
        facts_to_translate = {}
        for k, v in facts.items():
            if v and any(c > '\u007f' for c in str(v)): # Detect non-ASCII/Indic characters
                facts_to_translate[k] = v
        
        if facts_to_translate:
            prompt = f"""You are a professional legal translator. Translate these user-provided details into natural, formal English.
Keep proper names accurate. Return as a JSON object with the same keys.

DETAILS: {json.dumps(facts_to_translate, ensure_ascii=False)}

Return valid JSON only. No markdown.
"""
            try:
                resp = llm.invoke([HumanMessage(content=prompt)])
                trans_facts = _parse_json(strip_markdown(resp.content))
                for k, v in trans_facts.items(): 
                    if v: translated_facts[k] = v
            except Exception as e:
                print(f"[generate_bilingual_document] Reverse translation failed: {e}")

    def _build(lang: str, disc: str, current_facts: dict, cur_class: dict) -> str:
        # Use lang-specific scalars and body
        # Pass the desired document language to LLM prompts
        scalars    = _extract_scalars(intent, current_facts, lang)
        scalars["user_language"] = lang # To help assembly function pick labels
        
        body, docs = _generate_body(
            intent, current_facts, lang,
            is_demand_letter=is_demand_letter,
            other_party=cur_class["other_party"],
        )
        if is_demand_letter:
            return _assemble_demand_letter(
                scalars, body, docs,
                cur_class["other_party"], cur_class["other_party_location"],
                today_str, doc_type, current_facts,
                disclaimer=disc,
                reference_number=ref_number,
            )
        else:
            return _assemble_petition(
                scalars, body, docs,
                cur_class["authority"], cur_class["authority_location"], today_str, doc_type, current_facts,
                disclaimer=disc,
                reference_number=ref_number,
            )

    # English copy uses translated facts (mostly English now) and original English classification
    english_content   = _build("en", "", translated_facts, classification)
    disc_user         = ""
    # User lang copy uses original user facts and translated classification
    user_lang_content = english_content if user_language == "en" else _build(user_language, "", facts, translated_classification)

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
