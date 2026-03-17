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
    [Authority Name],          ← government/institutional authority
    [District, State]

    Sub: ...
    Respected Sir/Madam,
    [3 body paragraphs — first person]
    Relevant documents attached:
    1. ...
    Thank You,
    Signature: ___
    [Name]
    [Phone]
    DISCLAIMER

MODE B — "demand_letter_to_party" (sent directly to other party)
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
    [Other Party Name],        ← landlord / employer / debtor etc.
    [Other Party Address/City]

    Sub: ...
    Dear Mr./Ms. [Other Party Name],
    [3 body paragraphs — first person, assertive demand tone]
    Yours faithfully,
    Signature: ___
    [Name]
    [Phone]
    DISCLAIMER

Rules for all modes:
  - Ref No and Date always at the very TOP before From
  - First person throughout ("I", "my", "me") — never third person
  - No section headings (COMPLAINANT DETAILS, INCIDENT DETAILS etc.)
  - No filler phrases ("I hope", "I trust", "I am confident")
  - Evidence list uses actual items, not placeholder text
  - Single disclaimer at the bottom only
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

# ── Doc types that go DIRECTLY to the other party (not an authority) ──────────
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


def _norm(s: str) -> str:
    """Normalise for overlap detection: lowercase, strip spaces/dashes/commas."""
    s = s.lower()
    s = re.sub(r'[\s,\-\u2013\u2014]+', '', s)
    return s


def _already_in(text: str, value: str) -> bool:
    if not value or not text:
        return True
    return _norm(value) in _norm(text)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Classify intent
# ─────────────────────────────────────────────────────────────────────────────
def _classify_intent(intent: str, facts: dict) -> dict:
    """
    Returns doc_type, authority (or other_party for demand letters),
    other_party_location, ref_prefix, and is_demand_letter flag.
    """
    clean = _clean_facts(facts)
    prompt = f"""You are an Indian legal document classifier with deep knowledge of Indian law.
Carefully read the legal issue and facts, then make the CORRECT classification.

LEGAL ISSUE: {intent}

FACTS:
{_facts_text(clean)}

═══ CLASSIFICATION RULES ═══

STEP 1 — Determine the nature of the dispute:
  A) Criminal matter (theft, robbery, assault, serious criminal cheating/fraud by strangers, harassment) → police or court
  B) Civil/contractual dispute between two private parties (landlord-tenant, employer-employee salary,
     service provider, loan between individuals) → demand letter / legal notice to the OTHER PARTY
     **CRITICAL GENERAL RULE:** Disputes over rental security deposits, rent, unpaid loans between known persons, breach of contract, or employment dues are ALWAYS CIVIL (legal_notice). DO NOT classify them as `police_complaint_fir` even if the user claims the other party "cheated" or "stole" their money.
  C) Consumer grievance (defective product, e-commerce, insurance, telecom) → consumer commission
  D) Government/public grievance (RTI, government scheme) → government authority

STEP 2 — Pick the most logical doc_type based on the facts provided:
  Valid values:
  - police_complaint_fir
  - cyber_fraud_complaint
  - consumer_complaint
  - legal_notice
  - workplace_complaint
  - family_petition
  - banking_complaint
  - rti_application
  - property_dispute
  - insurance_complaint
  - civil_petition
  - general_petition

STEP 3 — Determine the correct recipient.
  If it's an AUTHORITY (police, bank manager, consumer court), fill "authority" with their official title (e.g. "The Station House Officer", "The Branch Manager").
  If it's a PRIVATE INDIVIDUAL/COMPANY (landlord, employer, debtor, spouse), fill "other_party" with their EXACT name and "other_party_location" with their address/city.

IMPORTANT: NEVER use `police_complaint_fir` for matters that are fundamentally civil (even if bad words like "fraud" or "cheating" are used casually by the user to describe a broken promise). Only use `police_complaint_fir` if criminal intent is obvious (like a stranger stealing a phone or physically attacking someone).

Return valid JSON only — no markdown:
{{
  "doc_type": "legal_notice",
  "authority": "",
  "other_party": "R. Kumar",
  "other_party_location": "Salem, Tamil Nadu",
  "ref_prefix": "LN",
  "reasoning": "Landlord refusing to return security deposit is a civil contractual dispute"
}}

Note: Fill "authority" for government/authority recipients, "other_party" for private party recipients.
"""
    try:
        resp = llm.invoke([
            SystemMessage(content="Indian legal classifier. Think carefully. Return JSON only, no markdown."),
            HumanMessage(content=prompt)
        ])
        data = _parse_json(resp.content)
        doc_type = str(data.get("doc_type", "general_petition")).strip()

        print(f"[_classify_intent] doc_type={doc_type}, reasoning={data.get('reasoning','')}")

        # Extract authority location from collected facts
        authority_location = ""
        authority_name = str(data.get("authority", "The Concerned Authority")).strip()

        # Get location-specific details from facts
        police_station = str(facts.get("police_station_name", "")).strip()
        forum_district = str(facts.get("consumer_forum_district", "")).strip()
        bank_branch = str(facts.get("bank_branch_details", "")).strip()
        insurance_office = str(facts.get("insurance_office_location", "")).strip()
        employer_address = str(facts.get("employer_name_address", "")).strip()
        rti_department = str(facts.get("rti_department_name", "")).strip()

        # Determine authority location based on what was collected.
        # IMPORTANT: When a specific branch address is given, use it ONLY as authority_location.
        # The LLM already puts the authority name (e.g. "The Branch Manager, SBI") in authority_name.
        # We must NOT repeat the full branch address in authority_name AND authority_location.

        if police_station and is_real_value(police_station):
            authority_location = police_station
            if "police station" not in police_station.lower():
                authority_location = f"{police_station} Police Station"
            # Override LLM authority name to avoid duplication
            authority_name = "The Station House Officer"

        elif bank_branch and is_real_value(bank_branch):
            # bank_branch already contains the full branch address
            # Put it entirely in authority_location; authority_name should be generic title only
            authority_location = bank_branch
            authority_name = "The Branch Manager"

        elif forum_district and is_real_value(forum_district):
            authority_location = f"District Consumer Forum, {forum_district}"

        elif insurance_office and is_real_value(insurance_office):
            authority_location = insurance_office
            authority_name = "The Branch Manager"

        elif rti_department and is_real_value(rti_department):
            authority_location = rti_department

        elif employer_address and is_real_value(employer_address):
            authority_location = employer_address

        # Fallback to district/state from personal info if nothing specific
        if not authority_location:
            district = str(facts.get("user_district", "")).strip()
            state = str(facts.get("user_state", "")).strip()
            authority_location = ", ".join(p for p in [district, state] if p and is_real_value(p))

        # Final fallback
        if not authority_location:
            authority_location = "India"

        # Prefer the explicitly collected other_party_name from facts over LLM inference
        llm_other_party    = str(data.get("other_party",          "")).strip()
        llm_other_party_loc= str(data.get("other_party_location", "")).strip()

        # Use fact-collected name if available (more reliable than LLM inference)
        known_other_party = str(facts.get("other_party_name",      "")).strip() or \
                            str(facts.get("landlord_name_contact",  "")).strip() or \
                            str(facts.get("landlord_name",          "")).strip()
        other_party_final = known_other_party if is_real_value(known_other_party) else llm_other_party

        # Other party location: prefer property address from facts
        known_other_party_loc = str(facts.get("property_exact_location",   "")).strip() or \
                                str(facts.get("rental_property_address",   "")).strip() or \
                                llm_other_party_loc

        return {
            "doc_type":             doc_type,
            "authority":            authority_name,
            "authority_location":   authority_location,
            "other_party":          other_party_final,
            "other_party_location": known_other_party_loc,
            "ref_prefix":           str(data.get("ref_prefix",           "SV")).upper().strip(),
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


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Extract scalar header values
# ─────────────────────────────────────────────────────────────────────────────
def _extract_scalars(intent: str, facts: dict, language: str) -> dict:
    clean     = _clean_facts(facts)
    lang_name = LANGUAGE_NAMES.get(language, "English")

    # Generate subject line
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


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Generate body + evidence list
# ─────────────────────────────────────────────────────────────────────────────
def _generate_body(intent: str, facts: dict, language: str,
                   is_demand_letter: bool = False,
                   other_party: str = "") -> tuple[str, str]:
    """
    Returns (body_paragraphs, documents_list).
    """
    lang_name = LANGUAGE_NAMES.get(language, "English")
    clean     = _clean_facts(facts)

    # Detect evidence: filter out values that are just repeating the complaint narrative
    # (user pasted complaint text instead of listing actual evidence items)
    evidence_keys = ["evidence_available", "evidence_details",
                     "documents_available", "proof_available"]
    evidence_raw_parts = []
    for k in evidence_keys:
        v = str(clean.get(k, "")).strip()
        if v:
            # If the evidence field just repeats factual narrative (>40 chars and no
            # mention of specific document types), treat as "no specific evidence"
            doc_keywords = ["receipt", "bill", "sms", "screenshot", "photo", "video",
                            "cctv", "statement", "certificate", "agreement", "contract",
                            "report", "invoice", "bank", "email", "whatsapp", "message",
                            "proof", "record", "document", "evidence", "உரிமம்", "ரசீது"]
            has_doc_keyword = any(kw in v.lower() for kw in doc_keywords)
            if has_doc_keyword or len(v) < 50:
                evidence_raw_parts.append(v)
            # else: narrative repeated — skip
    evidence_raw = " | ".join(evidence_raw_parts).strip()

    if is_demand_letter:
        tone_instruction = (
            "This is a formal DEMAND LETTER / LEGAL NOTICE sent directly to the other party.\n"
            "Tone: firm, assertive, and formal — like a legal notice before court action.\n"
            f"The letter is addressed to: {other_party if other_party else 'the other party'}.\n"
            "Paragraph 3: one clear demand with a deadline, and state consequences if not complied.\n"
        )
    else:
        tone_instruction = (
            "This is a formal COMPLAINT / PETITION to a government authority.\n"
            "Tone: respectful and factual.\n"
            "Paragraph 3: clearly request the authority to take specific action.\n"
        )

    prompt = f"""You are writing a concise formal legal letter for an Indian citizen.
Write ENTIRELY in {lang_name}.

Legal issue: "{intent}"

CONFIRMED FACTS — use ONLY these, do not add anything not listed here:
{_facts_text(clean)}

{tone_instruction}

═══ PART 1: BODY (exactly 3 SHORT paragraphs) ═══
Write IN FIRST PERSON ("I", "my", "me").
Each paragraph: 2 to 3 sentences MAXIMUM. Keep it concise and professional.

Paragraph 1 — Facts: State what happened. Include dates, amounts, agreed terms.
Paragraph 2 — Harm: State the specific loss or harm caused and why the other party is at fault.
Paragraph 3 — Demand/Request: State the specific action demanded or requested, with deadline if applicable.

CRITICAL RULES:
- 2-3 sentences per paragraph ONLY — no padding, no filler
- First person ONLY: "I", "my", "me" — NEVER "the complainant", "the victim", "he/she/they"
- Include specific amounts (₹), dates (DD/MM/YYYY), and names from the facts
- NO filler phrases: "I hope", "I trust", "I am confident", "I believe", "I am writing this"
- Do NOT repeat facts across paragraphs
- No markdown, no bold, no bullets
- Do NOT include sender's name, phone, or address in the body text
- Do NOT cite law section numbers
- Do NOT invent facts not in the confirmed list above

Write this EXACT marker on its own line after the 3 paragraphs:
---DOCUMENTS---

═══ PART 2: EVIDENCE LIST ═══
Evidence from facts: "{evidence_raw}"

Rules:
- If specific document types are mentioned (rental agreement, bank SMS, receipt, photograph,
  CCTV, medical report, purchase bill, WhatsApp messages, email, contract etc.)
  → list EACH as a numbered item.
- If the evidence field only contains a narrative of what happened (not actual document names)
  OR is empty → write: 1. Relevant documents and evidence will be submitted upon request.
- NEVER list the complaint narrative as evidence.
- NEVER invent evidence items.
"""
    try:
        resp = llm.invoke([
            SystemMessage(content="Legal letter writer. Plain text only. No markdown."),
            HumanMessage(content=prompt)
        ])
        raw = _strip_md(resp.content)
    except Exception as e:
        print(f"[_generate_body] error: {e}")
        raw = (f"I respectfully submit the following.\n\n"
               f"I have suffered loss due to the matter described.\n\n"
               f"I request immediate resolution of this matter.\n\n"
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

    return body_paragraphs, documents_list


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4A — Assemble petition to authority
# ─────────────────────────────────────────────────────────────────────────────
def get_applicable_laws(doc_type: str, facts: dict) -> list:
    """
    Returns list of relevant Indian law sections based on document type and facts.
    Uses simple keyword matching - no database or RAG needed.
    
    Args:
        doc_type: Type of legal document (police_complaint_fir, consumer_complaint, etc.)
        facts: Dictionary of collected facts from user
    
    Returns:
        List of applicable law sections as strings
    """
    
    applicable_laws = []
    
    # Convert facts to lowercase text for keyword matching
    facts_text = " ".join(str(v).lower() for v in facts.values() if v)
    
    # ═══ CRIMINAL COMPLAINTS ═══
    if doc_type == "police_complaint_fir":
        # Always add FIR registration section
        applicable_laws.append("Code of Criminal Procedure 1973, Section 154 - Registration of FIR")
        
        # Theft-related
        if any(keyword in facts_text for keyword in ["theft", "stolen", "robbery", "burglary", "missing items", "stole"]):
            applicable_laws.append("Indian Penal Code 1860, Section 379 - Punishment for theft")
            if "house" in facts_text or "home" in facts_text:
                applicable_laws.append("Indian Penal Code 1860, Section 380 - Theft in dwelling house")
        
        # Assault/Violence
        if any(keyword in facts_text for keyword in ["assault", "attack", "beat", "hit", "violence", "hurt", "injury"]):
            applicable_laws.append("Indian Penal Code 1860, Section 323 - Punishment for voluntarily causing hurt")
            if "grievous" in facts_text or "serious" in facts_text:
                applicable_laws.append("Indian Penal Code 1860, Section 325 - Grievous hurt")
        
        # Cheating/Fraud
        if any(keyword in facts_text for keyword in ["cheat", "fraud", "dishonest", "deceive", "false promise"]):
            applicable_laws.append("Indian Penal Code 1860, Section 420 - Cheating and dishonestly inducing delivery of property")
        
        # Harassment (women)
        if any(keyword in facts_text for keyword in ["harass", "modesty", "woman", "female", "girl", "inappropriate"]):
            applicable_laws.append("Indian Penal Code 1860, Section 354 - Assault or criminal force with intent to outrage modesty")
            applicable_laws.append("Indian Penal Code 1860, Section 509 - Word, gesture or act intended to insult the modesty of a woman")
        
        # Threats/Intimidation
        if any(keyword in facts_text for keyword in ["threat", "intimidate", "criminal intimidation", "blackmail"]):
            applicable_laws.append("Indian Penal Code 1860, Section 506 - Punishment for criminal intimidation")
    
    # ═══ CYBER CRIMES ═══
    elif doc_type == "cyber_fraud_complaint":
        applicable_laws.append("Information Technology Act 2000, Section 66C - Identity theft")
        applicable_laws.append("Information Technology Act 2000, Section 66D - Cheating by personation using computer resource")
        
        if any(keyword in facts_text for keyword in ["hack", "unauthorized access", "password"]):
            applicable_laws.append("Information Technology Act 2000, Section 66 - Computer related offences")
        
        if any(keyword in facts_text for keyword in ["obscene", "pornography", "indecent"]):
            applicable_laws.append("Information Technology Act 2000, Section 67 - Publishing obscene material")
        
        # Also add IPC cheating section for cyber fraud
        applicable_laws.append("Indian Penal Code 1860, Section 420 - Cheating and dishonestly inducing delivery of property")
    
    # ═══ CONSUMER COMPLAINTS ═══
    elif doc_type == "consumer_complaint":
        applicable_laws.append("Consumer Protection Act 2019, Section 35 - Consumer disputes redressal")
        applicable_laws.append("Consumer Protection Act 2019, Section 2(7) - Definition of consumer")
        
        if any(keyword in facts_text for keyword in ["defective", "defect", "faulty", "not working"]):
            applicable_laws.append("Consumer Protection Act 2019, Section 2(10) - Definition of defect")
        
        if any(keyword in facts_text for keyword in ["unfair", "misleading", "false advertisement"]):
            applicable_laws.append("Consumer Protection Act 2019, Section 2(47) - Unfair trade practice")
        
        if any(keyword in facts_text for keyword in ["service", "contractor", "repair", "plumber", "electrician"]):
            applicable_laws.append("Consumer Protection Act 2019, Section 2(42) - Definition of service")
    
    # ═══ CIVIL DISPUTES (Legal Notices) ═══
    elif doc_type == "legal_notice":
        # Property/Landlord-Tenant
        if any(keyword in facts_text for keyword in ["property", "land", "house", "rent", "landlord", "tenant", "lease"]):
            applicable_laws.append("Transfer of Property Act 1882")
            applicable_laws.append("Specific Relief Act 1963, Section 9 - Suits for specific performance of contracts")
            
            if "rent" in facts_text or "tenant" in facts_text:
                applicable_laws.append("Rent Control Act (State-specific)")
        
        # Contract breach
        if any(keyword in facts_text for keyword in ["contract", "agreement", "breach", "violation"]):
            applicable_laws.append("Indian Contract Act 1872, Section 73 - Compensation for loss or damage caused by breach of contract")
        
        # Money recovery
        if any(keyword in facts_text for keyword in ["loan", "debt", "owe", "borrow", "repay", "recovery"]):
            applicable_laws.append("Civil Procedure Code 1908, Order 37 - Summary Procedure")
        
        # Defamation
        if any(keyword in facts_text for keyword in ["defamation", "reputation", "false statement", "slander", "libel"]):
            applicable_laws.append("Indian Penal Code 1860, Sections 499-502 - Defamation")
    
    # ═══ WORKPLACE/EMPLOYMENT ═══
    elif doc_type == "workplace_complaint":
        applicable_laws.append("Industrial Disputes Act 1947, Section 2(s) - Definition of workman")
        
        if any(keyword in facts_text for keyword in ["salary", "wage", "payment", "unpaid", "dues"]):
            applicable_laws.append("Payment of Wages Act 1936, Section 5 - Fixation of wage-periods and time of payment")
        
        if any(keyword in facts_text for keyword in ["terminate", "dismiss", "fire", "retrench"]):
            applicable_laws.append("Industrial Disputes Act 1947, Section 25F - Conditions precedent to retrenchment")
        
        if any(keyword in facts_text for keyword in ["harassment", "sexual", "misconduct"]):
            applicable_laws.append("Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act 2013")
        
        if any(keyword in facts_text for keyword in ["provident fund", "pf", "epf"]):
            applicable_laws.append("Employees' Provident Funds Act 1952")
    
    # ═══ BANKING COMPLAINTS ═══
    elif doc_type == "banking_complaint":
        applicable_laws.append("Banking Regulation Act 1949")
        applicable_laws.append("Reserve Bank of India Act 1934")
        
        if any(keyword in facts_text for keyword in ["unauthorized", "debit", "transaction", "fraud"]):
            applicable_laws.append("Payment and Settlement Systems Act 2007")
        
        if any(keyword in facts_text for keyword in ["loan", "credit", "emi"]):
            applicable_laws.append("Banking Ombudsman Scheme 2006")
    
    # ═══ INSURANCE COMPLAINTS ═══
    elif doc_type == "insurance_complaint":
        applicable_laws.append("Insurance Act 1938")
        applicable_laws.append("Insurance Regulatory and Development Authority Act 1999")
        
        if any(keyword in facts_text for keyword in ["claim", "reject", "denial"]):
            applicable_laws.append("IRDAI (Protection of Policyholders' Interests) Regulations 2017")
    
    # ═══ RTI APPLICATIONS ═══
    elif doc_type == "rti_application":
        applicable_laws.append("Right to Information Act 2005, Section 6 - Request for obtaining information")
        applicable_laws.append("Right to Information Act 2005, Section 7 - Disposal of request")
    
    # ═══ PROPERTY DISPUTES ═══
    elif doc_type == "property_dispute":
        applicable_laws.append("Transfer of Property Act 1882")
        applicable_laws.append("Indian Easements Act 1882")
        
        if any(keyword in facts_text for keyword in ["encroachment", "boundary", "trespass"]):
            applicable_laws.append("Specific Relief Act 1963, Section 38 - Perpetual injunction")
    
    # ═══ FAMILY MATTERS ═══
    elif doc_type == "family_petition":
        if any(keyword in facts_text for keyword in ["maintenance", "alimony", "spouse", "wife", "husband"]):
            applicable_laws.append("Code of Criminal Procedure 1973, Section 125 - Order for maintenance of wives, children and parents")
            applicable_laws.append("Hindu Marriage Act 1955, Section 24 - Maintenance pendente lite and expenses of proceedings")
        
        if any(keyword in facts_text for keyword in ["divorce", "separation"]):
            applicable_laws.append("Hindu Marriage Act 1955, Section 13 - Divorce")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_laws = []
    for law in applicable_laws:
        if law not in seen:
            seen.add(law)
            unique_laws.append(law)
    
    return unique_laws


def _assemble_petition(scalars: dict, body_paragraphs: str, documents_list: str,
                       authority: str, authority_location: str, today_str: str, doc_type: str, facts: dict,
                       disclaimer: str = "", reference_number: str = "") -> str:
    name      = scalars.get("full_name",    "")
    address   = scalars.get("full_address", "")
    district  = scalars.get("district",     "")
    state     = scalars.get("state",        "")
    pincode   = scalars.get("pincode",      "")
    phone     = scalars.get("phone",        "")
    subject   = scalars.get("subject",      "")

    district_raw = scalars.get("district_raw", district)
    state_raw    = scalars.get("state_raw",    state)

    # Use the authority_location passed from classification
    auth_loc = authority_location if authority_location else "India"

    addr_clean = re.sub(r'[\s,\-\u2013\u2014]+$', '', address).strip() if address else ""

    city_state_pin = []
    if district: city_state_pin.append(district)
    if state: city_state_pin.append(state)
    
    city_state_str = ", ".join(city_state_pin)
    if pincode and city_state_str:
        last_line = f"{city_state_str} - {pincode}"
    elif city_state_str:
        last_line = city_state_str
    elif pincode:
        last_line = pincode
    else:
        last_line = ""

    # Compute applicable laws for this doc type
    applicable_laws = get_applicable_laws(doc_type, facts)

    # Split full_address into individual lines at commas, just like the To block
    def _split_address_lines(raw_addr: str) -> list:
        """Split a comma-separated address string into clean individual lines."""
        if not raw_addr:
            return []
        parts_out = [p.strip().rstrip(',').strip() for p in raw_addr.split(',')]
        return [p for p in parts_out if p]

    addr_lines = _split_address_lines(addr_clean)

    parts = []
    # NO Ref No — removed per user request
    parts.append(f"Date: {datetime.now().strftime('%d/%m/%Y (%A)')}")
    parts.append("")

    parts.append("From:")
    if name:
        parts.append(name.strip().rstrip(','))
    for line in addr_lines:
        parts.append(line)
    parts.append("")
    
    parts.append("To:")
    if authority:
        parts.append(authority.strip().rstrip(','))
    if auth_loc:
        loc_parts = auth_loc.replace('\n', ',').split(',')
        for loc_part in loc_parts:
            cleaned = loc_part.strip().rstrip(',')
            if cleaned and cleaned != authority.strip():
                parts.append(cleaned)
    parts.append("")
    parts.append(f"Sub: {subject}")
    parts.append("")
    parts.append("Respected Sir/Madam,")
    parts.append("")

    paragraphs = [p.strip() for p in re.split(r'\n{2,}', body_paragraphs) if p.strip()]
    parts.append("\n\n".join(paragraphs))
    parts.append("")

    if applicable_laws:
        parts.append("Applicable Legal Provisions:")
        parts.append("")
        for i, law in enumerate(applicable_laws, 1):
            parts.append(f"{i}. {law}")
        parts.append("")

    parts.append("Relevant documents attached:")
    for line in documents_list.splitlines():
        if line.strip(): parts.append(f"   {line.strip()}")
    parts.append("")
    parts.append("Thank you.")
    parts.append("")
    parts.append("Yours faithfully,")
    parts.append("")
    parts.append("")
    parts.append("________________________")
    parts.append("(Signature)")
    parts.append("")
    if name:  parts.append(f"Name: {name}")
    if phone: parts.append(f"Contact: {phone}")
    place = district_raw or state_raw or ""
    if place:
        parts.append(f"Place: {place}")
    parts.append(f"Date: {today_str}")
    if disclaimer:
        parts.append("")
        parts.append("DISCLAIMER")
        parts.append("")
        parts.append(disclaimer)

    return "\n".join(parts).strip()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4B — Assemble demand letter to other party (landlord, employer, etc.)
# ─────────────────────────────────────────────────────────────────────────────
def _assemble_demand_letter(scalars: dict, body_paragraphs: str, documents_list: str,
                            other_party: str, other_party_location: str,
                            today_str: str, doc_type: str, facts: dict,
                            disclaimer: str = "", reference_number: str = "") -> str:
    name      = scalars.get("full_name",    "")
    address   = scalars.get("full_address", "")
    district  = scalars.get("district",     "")
    state     = scalars.get("state",        "")
    pincode   = scalars.get("pincode",      "")
    phone     = scalars.get("phone",        "")
    subject   = scalars.get("subject",      "")

    district_raw = scalars.get("district_raw", district)
    state_raw    = scalars.get("state_raw",    state)

    addr_clean = re.sub(r'[\s,\-\u2013\u2014]+$', '', address).strip() if address else ""

    city_state_pin = []
    if district: city_state_pin.append(district)
    if state: city_state_pin.append(state)
    
    city_state_str = ", ".join(city_state_pin)
    if pincode and city_state_str:
        last_line = f"{city_state_str} - {pincode}"
    elif city_state_str:
        last_line = city_state_str
    elif pincode:
        last_line = pincode
    else:
        last_line = ""

    # Salutation: "Dear Mr./Ms. [Name]" — extract first name for salutation
    # Use the full other_party name, prefixed with "Mr./Ms." generically
    salutation = f"Dear {other_party}," if other_party else "Dear Sir/Madam,"

    # Compute applicable laws for this doc type
    applicable_laws = get_applicable_laws(doc_type, facts)

    # Split full_address into individual lines at commas, just like the To block
    def _split_address_lines(raw_addr: str) -> list:
        if not raw_addr:
            return []
        parts_out = [p.strip().rstrip(',').strip() for p in raw_addr.split(',')]
        return [p for p in parts_out if p]

    addr_lines = _split_address_lines(addr_clean)

    parts = []
    # NO Ref No — removed per user request
    parts.append(f"Date: {datetime.now().strftime('%d/%m/%Y (%A)')}")
    parts.append("")

    parts.append("From:")
    if name:
        parts.append(name.strip().rstrip(','))
    for line in addr_lines:
        parts.append(line)
    parts.append("")
    
    parts.append("To:")
    if other_party:
        parts.append(other_party.strip().rstrip(','))
    if other_party_location:
        for p in other_party_location.split(','):
            loc_part = p.strip().rstrip(',')
            if loc_part:
                parts.append(loc_part)
    parts.append("")
    parts.append(f"Sub: {subject}")
    parts.append("")
    parts.append(salutation)
    parts.append("")

    paragraphs = [p.strip() for p in re.split(r'\n{2,}', body_paragraphs) if p.strip()]
    parts.append("\n\n".join(paragraphs))
    parts.append("")

    if applicable_laws:
        parts.append("Applicable Legal Provisions:")
        parts.append("")
        for i, law in enumerate(applicable_laws, 1):
            parts.append(f"{i}. {law}")
        parts.append("")

    # Demand letters list enclosures only if there are actual items
    has_real_docs = any(
        line.strip() and not line.strip().lower().startswith("relevant documents and evidence will be submitted")
        for line in documents_list.splitlines() if re.match(r'^\d+\.', line.strip())
    )
    if has_real_docs:
        parts.append("Enclosures:")
        for line in documents_list.splitlines():
            if line.strip(): parts.append(f"   {line.strip()}")
        parts.append("")

    parts.append("Thank you.")
    parts.append("")
    parts.append("Yours faithfully,")
    parts.append("")
    parts.append("")
    parts.append("________________________")
    parts.append("(Signature)")
    parts.append("")
    if name:  parts.append(f"Name: {name}")
    if phone: parts.append(f"Contact: {phone}")
    place = district_raw or state_raw or ""
    if place:
        parts.append(f"Place: {place}")
    parts.append(f"Date: {today_str}")
    if disclaimer:
        parts.append("")
        parts.append("DISCLAIMER")
        parts.append("")
        parts.append(disclaimer)

    return "\n".join(parts).strip()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Readiness score
# ─────────────────────────────────────────────────────────────────────────────
def _calculate_readiness(intent: str, facts: dict) -> int:
    clean = _clean_facts(facts)
    prompt = (
        f"Score the evidence readiness of this Indian legal complaint from 0 to 100.\n\n"
        f"Legal issue: {intent}\nFacts:\n{_facts_text(clean)}\n\n"
        "Scoring:\n"
        "- 90-100: Strong documentary evidence (receipts, bank statements, SMS, screenshots, witnesses)\n"
        "- 60-89:  Some evidence but gaps\n"
        "- 30-59:  Limited evidence, mostly verbal account\n"
        "- 0-29:   No evidence at all\n\n"
        "Return ONLY an integer. No text."
    )
    try:
        resp  = llm.invoke([HumanMessage(content=prompt)])
        score = int(re.search(r'\d+', resp.content).group())
        return max(0, min(100, score))
    except Exception:
        return min(100, len(clean) * 10)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def generate_bilingual_document(intent: str, facts: dict,
                                user_language: str = "en") -> dict:
    today_str    = date.today().strftime("%d/%m/%Y")
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    classification    = _classify_intent(intent, facts)
    doc_type          = classification["doc_type"]
    authority         = classification["authority"]
    authority_location = classification.get("authority_location", "India")
    other_party       = classification["other_party"]
    other_party_loc   = classification["other_party_location"]
    ref_prefix        = classification["ref_prefix"]
    is_demand_letter  = classification["is_demand_letter"]
    ref_number        = f"SV/{ref_prefix}/{date.today().year}/{date.today().strftime('%m%d')}/001"

    readiness_score = _calculate_readiness(intent, facts)

    def _build(lang: str, disc: str) -> str:
        scalars   = _extract_scalars(intent, facts, lang)
        body, docs = _generate_body(
            intent, facts, lang,
            is_demand_letter=is_demand_letter,
            other_party=other_party,
        )
        if is_demand_letter:
            return _assemble_demand_letter(
                scalars, body, docs,
                other_party, other_party_loc,
                today_str, doc_type, facts,
                disclaimer=disc,
                reference_number=ref_number,
            )
        else:
            return _assemble_petition(
                scalars, body, docs,
                authority, authority_location, today_str, doc_type, facts,
                disclaimer=disc,
                reference_number=ref_number,
            )

    english_content   = _build("en",          DISCLAIMER_EN)
    disc_user         = get_disclaimer(user_language)
    user_lang_content = english_content if user_language == "en" else _build(user_language, disc_user)

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
