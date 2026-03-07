"""
Bilingual Document Generator – Satta Vizhi
Generates legally formatted documents in both user's language and English.
Refers to sample document structures (Police Complaint, Consumer Complaint,
Legal Notice, RTI, FIR, General Petition, etc.) from the Indian legal domain.
"""

from llm_provider import llm
from langchain_core.messages import HumanMessage
import json
from datetime import datetime


# ============================================================
# DOCUMENT STRUCTURE REFERENCES
# (Based on sample legal documents ZIP – Indian legal format)
# ============================================================

DOCUMENT_TEMPLATES = {
    "police_complaint": {
        "title": "COMPLAINT TO THE SUPERINTENDENT OF POLICE / STATION HOUSE OFFICER",
        "authority": "The Station House Officer\n[Police Station Name]\n[District], [State]",
        "sections": [
            "1. Introduction (Who you are)",
            "2. Chronological Facts of the Case",
            "3. Description of Accused / Respondent",
            "4. Nature of Offence",
            "5. Evidence Available",
            "6. Prayer / Request for Action",
            "7. Statement of Truth",
            "8. List of Enclosures",
            "9. Signature and Date"
        ],
        "applicable_acts": "Indian Penal Code, 1860 / Bharatiya Nyaya Sanhita, 2023"
    },
    "consumer_complaint": {
        "title": "COMPLAINT BEFORE THE DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION",
        "authority": "The President\nDistrict Consumer Disputes Redressal Commission\n[District], [State]",
        "sections": [
            "1. Particulars of Complainant",
            "2. Particulars of Opposite Party (Seller/Service Provider)",
            "3. Brief Facts of the Complaint",
            "4. Cause of Action",
            "5. Reliefs Sought (Refund/Compensation/Replacement)",
            "6. Jurisdiction",
            "7. Valuation of Complaint",
            "8. Prayer",
            "9. Verification and Signature",
            "10. Annexures (Bills, Receipts, Warranty)"
        ],
        "applicable_acts": "Consumer Protection Act, 2019"
    },
    "rti_application": {
        "title": "APPLICATION UNDER THE RIGHT TO INFORMATION ACT, 2005",
        "authority": "The Public Information Officer\n[Department Name]\n[Government Office Address]",
        "sections": [
            "1. Applicant Details",
            "2. Information Sought (Specific and Clear)",
            "3. Period for which Information is Required",
            "4. Mode of Receiving Information",
            "5. Declaration (Not held by other government entity)",
            "6. Fee Payment Details",
            "7. Date and Signature"
        ],
        "applicable_acts": "Right to Information Act, 2005 – Section 6"
    },
    "legal_notice": {
        "title": "LEGAL NOTICE",
        "authority": "Sent Through Advocate / Directly",
        "sections": [
            "1. Notice Address (Recipient)",
            "2. Sender Details",
            "3. Reference/Subject",
            "4. Background Facts",
            "5. Demand / Legal Requirement",
            "6. Time Given to Comply (usually 15-30 days)",
            "7. Consequences of Non-Compliance",
            "8. Without Prejudice Statement",
            "9. Signature of Advocate / Party"
        ],
        "applicable_acts": "Civil Procedure Code, 1908 / Specific Relief Act, 1963"
    },
    "anticipatory_bail": {
        "title": "PETITION FOR ANTICIPATORY BAIL",
        "authority": "In the Court of Sessions Judge\n[District], [State]",
        "sections": [
            "1. Petitioner Details",
            "2. FIR/Case Details",
            "3. Grounds for Bail",
            "4. Prima Facie Innocence",
            "5. Previous Criminal Record (if any)",
            "6. Undertaking by Petitioner",
            "7. Prayer for Bail",
            "8. Verification",
            "9. Advocate Signature"
        ],
        "applicable_acts": "Section 438 CrPC / Section 482 BNSS"
    },
    "motor_accident_claim": {
        "title": "CLAIM PETITION BEFORE THE MOTOR ACCIDENT CLAIMS TRIBUNAL",
        "authority": "The Presiding Officer\nMotor Accident Claims Tribunal (MACT)\n[District], [State]",
        "sections": [
            "1. Claimant Details",
            "2. Respondent (Driver/Owner/Insurance Company)",
            "3. Date, Time, and Place of Accident",
            "4. Circumstances of Accident",
            "5. Nature of Injuries / Damages",
            "6. Medical Expenses Incurred",
            "7. Loss of Income / Earning Capacity",
            "8. Compensation Sought",
            "9. List of Documents",
            "10. Prayer and Verification"
        ],
        "applicable_acts": "Motor Vehicles Act, 1988 – Section 166"
    },
    "domestic_violence_complaint": {
        "title": "COMPLAINT UNDER THE PROTECTION OF WOMEN FROM DOMESTIC VIOLENCE ACT, 2005",
        "authority": "The Magistrate Court / Protection Officer\n[District], [State]",
        "sections": [
            "1. Complainant (Aggrieved Person) Details",
            "2. Respondent Details",
            "3. Relationship with Respondent",
            "4. Acts of Domestic Violence (Physical/Mental/Sexual/Economic)",
            "5. Reliefs Sought (Protection Order/Residence Order/Monetary Relief)",
            "6. Interim Relief Request",
            "7. Verification",
            "8. Annexures"
        ],
        "applicable_acts": "Protection of Women from Domestic Violence Act, 2005"
    },
    "employment_dispute": {
        "title": "COMPLAINT REGARDING ILLEGAL TERMINATION / SALARY DISPUTE",
        "authority": "The Labour Commissioner / Labour Court\n[District], [State]",
        "sections": [
            "1. Employee (Complainant) Details",
            "2. Employer (Respondent) Details",
            "3. Nature of Employment",
            "4. Details of Dispute",
            "5. Prior Notices / Representations",
            "6. Relief Sought",
            "7. Verification",
            "8. Supporting Documents"
        ],
        "applicable_acts": "Industrial Disputes Act, 1947 / Payment of Wages Act, 1936 / Minimum Wages Act, 1948"
    },
    "general_petition": {
        "title": "COMPLAINT / PETITION",
        "authority": "The Competent Authority\n[Office Name]\n[District], [State]",
        "sections": [
            "1. Petitioner Details",
            "2. Respondent Details",
            "3. Brief Facts",
            "4. Grounds of Complaint",
            "5. Relief Sought",
            "6. Verification",
            "7. List of Documents"
        ],
        "applicable_acts": "As applicable"
    }
}


def generate_bilingual_document(intent: str, facts: dict, user_language: str, selected_action: str = None) -> dict:
    """
    Generate document in both user language and English.
    Uses sample legal document structures as reference.

    Returns:
        {
            "user_language_content": str,
            "english_content": str,
            "document_type": str,
            "readiness_score": int,
            "user_language": str
        }
    """
    # Determine document type based on intent and selected action
    doc_type = determine_document_type(intent, selected_action)
    template = DOCUMENT_TEMPLATES.get(doc_type, DOCUMENT_TEMPLATES["general_petition"])

    # Generate English version first (primary)
    english_content = generate_document_in_language(intent, facts, "en", doc_type, template, selected_action)

    # Generate user language version
    if user_language == "en":
        user_lang_content = english_content
    else:
        user_lang_content = generate_document_in_language(intent, facts, user_language, doc_type, template, selected_action)

    # Calculate readiness score
    readiness_score = calculate_readiness_score(facts)

    return {
        "user_language_content": user_lang_content,
        "english_content": english_content,
        "document_type": doc_type,
        "readiness_score": readiness_score,
        "user_language": user_language
    }


def generate_document_in_language(intent: str, facts: dict, language: str,
                                   doc_type: str, template: dict, selected_action: str = None) -> str:
    """Generate a properly formatted legal document in the specified language."""

    lang_name = get_language_name(language)
    current_date = datetime.now().strftime("%d-%m-%Y")

    # Format facts for the document
    formatted_facts = json.dumps(facts, ensure_ascii=False, indent=2)

    # Build structure hint
    sections_text = "\n".join([f"  {s}" for s in template["sections"]])

    action_context = f"Selected Legal Action: {selected_action}" if selected_action else ""

    prompt = f"""You are an expert Indian legal document drafting assistant integrated into Satta Vizhi.

[INPUT CONTEXT]
Legal Intent: {intent}
{action_context}
Document Type: {template['title']}
Applicable Acts: {template['applicable_acts']}
Target Language: {lang_name} ({language})
Current Date: {current_date}

[FACTS PROVIDED BY USER]
{formatted_facts}

[DOCUMENT RECIPIENT / AUTHORITY]
{template['authority']}

================================
TASK: Draft a Complete Legal Document
================================
Generate a complete, properly formatted, jurisdiction-compliant Indian legal document in {lang_name}.

[MANDATORY DOCUMENT STRUCTURE]
The document MUST include ALL these sections in order:
{sections_text}

================================
GLOBAL CONSTRAINTS (STRICTLY FOLLOW)
================================
1. Language: Use ONLY {lang_name}. Do NOT switch languages mid-document.
2. Facts: NEVER modify amounts, dates, or quantities. Use user-provided values exactly.
3. Missing Information: Use placeholders like [MISSING: field_name] for absent facts.
4. Neutral Language: Use factual, objective language only.
5. Legal Caution: Use "may fall under", "allegedly", "as stated by the complainant".
6. DENIED Fields: If a fact is marked 'EXPLICITLY_DENIED', completely OMIT it.
7. NO Hallucination: Only use acts/sections explicitly listed in Applicable Acts above.
8. Dates: Use DD-MM-YYYY format.
9. Currency: Use ₹ (Rupees) format.
10. NO Markdown: Return pure text only, no bold/italic/headers with #.

================================
DOCUMENT TYPE RULES
================================
- FIR / Police Complaint: Use formal police complaint format with FIR sections
- Consumer Complaint: Use CDRC format with all statutory details
- RTI Application: Use official RTI format with Section 6 reference
- Legal Notice: Use advocate-style notice with compliance deadline
- General Petition: Use formal petition format with jurisdictional details

================================
SIGNATURE BLOCK (MANDATORY at end)
================================
Include:
  Complainant: {facts.get('user_full_name', '[Name of Complainant]')}
  Address: {facts.get('user_address', '[Address]')}
  Date: {current_date}
  Place: {facts.get('district', '[Place]')}, {facts.get('state', '[State]')}
  Signature: [Signature / Thumb Impression]

After the signature block, add this DISCLAIMER on a new line:
"DISCLAIMER: This document has been automatically generated by Satta Vizhi (AI Legal Assistant) based solely on information provided by the user. It does not constitute legal advice or legal representation. Please review this document with a qualified legal professional before official submission."

================================
OUTPUT FORMAT
================================
Return ONLY the complete legal document text (plain text, no markdown).
Start directly with the document title.
End with the disclaimer.
"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


def calculate_readiness_score(facts: dict) -> int:
    """
    Calculate document readiness based on completeness of facts.

    Score breakdown:
    - Core jurisdiction (state, district, date): +30
    - Parties identified: +20
    - Incident description: +20
    - Evidence available: +20
    - Contact details: +10
    """
    score = 0

    # Core jurisdiction
    if facts.get("state") and str(facts.get("state", "")).lower() not in ["unknown", "not_available"]:
        score += 10
    if facts.get("district") and str(facts.get("district", "")).lower() not in ["unknown", "not_available"]:
        score += 10
    if facts.get("incident_date") and str(facts.get("incident_date", "")).lower() not in ["unknown", "not_available"]:
        score += 10

    # Parties
    if facts.get("user_full_name") and str(facts.get("user_full_name", "")).lower() not in ["unknown", "not_available"]:
        score += 10
    if facts.get("counterparty_name") and str(facts.get("counterparty_name", "")).lower() not in ["unknown", "not_available"]:
        score += 10

    # Incident
    if facts.get("incident_description") and len(str(facts.get("incident_description", ""))) > 20:
        score += 20

    # Evidence
    evidence = facts.get("evidence_available", "")
    if isinstance(evidence, str) and evidence and len(evidence) > 5:
        evidence_lower = evidence.lower()
        if any(term in evidence_lower for term in ["receipt", "bill", "contract", "agreement", "invoice"]):
            score += 10
        if any(term in evidence_lower for term in ["email", "message", "whatsapp", "sms", "letter"]):
            score += 5
        if any(term in evidence_lower for term in ["photo", "video", "witness", "document", "proof"]):
            score += 5

    # Contact details
    if facts.get("user_phone") and str(facts.get("user_phone", "")).lower() not in ["unknown", "not_available"]:
        score += 5
    if facts.get("user_address") and len(str(facts.get("user_address", ""))) > 10:
        score += 5

    return min(score, 100)


def determine_document_type(intent: str, selected_action: str = None) -> str:
    """
    Determine the most appropriate document type.
    Checks selected_action first, then falls back to intent.
    """
    search_text = f"{selected_action or ''} {intent or ''}".lower()

    # Check selected action first
    if selected_action:
        action_lower = selected_action.lower()
        if any(t in action_lower for t in ["fir", "police complaint", "first information report"]):
            return "police_complaint"
        if any(t in action_lower for t in ["consumer complaint", "consumer commission", "consumer forum"]):
            return "consumer_complaint"
        if any(t in action_lower for t in ["rti", "right to information"]):
            return "rti_application"
        if any(t in action_lower for t in ["legal notice", "notice"]):
            return "legal_notice"
        if any(t in action_lower for t in ["anticipatory bail", "bail petition"]):
            return "anticipatory_bail"
        if any(t in action_lower for t in ["mact", "motor accident", "accident claim", "tribunal"]):
            return "motor_accident_claim"
        if any(t in action_lower for t in ["domestic violence", "protection order"]):
            return "domestic_violence_complaint"
        if any(t in action_lower for t in ["labour", "employment", "salary", "wages"]):
            return "employment_dispute"

    # Fall back to intent
    if any(t in search_text for t in ["theft", "robbery", "assault", "harassment", "crime", "cheating", "fraud"]):
        return "police_complaint"
    if any(t in search_text for t in ["consumer", "product", "service", "refund", "defective", "warranty"]):
        return "consumer_complaint"
    if any(t in search_text for t in ["rti", "information act", "government information"]):
        return "rti_application"
    if any(t in search_text for t in ["landlord", "tenant", "rent", "deposit", "eviction"]):
        return "legal_notice"
    if any(t in search_text for t in ["divorce", "maintenance", "custody", "family settlement"]):
        return "general_petition"
    if any(t in search_text for t in ["motor", "accident", "vehicle", "car crash"]):
        return "motor_accident_claim"
    if any(t in search_text for t in ["domestic", "violence", "dowry", "cruelty"]):
        return "domestic_violence_complaint"
    if any(t in search_text for t in ["employment", "salary", "wages", "termination", "workplace"]):
        return "employment_dispute"

    return "general_petition"


def get_language_name(code: str) -> str:
    """Get full language name from ISO code."""
    languages = {
        "en": "English",
        "hi": "Hindi",
        "ta": "Tamil",
        "te": "Telugu",
        "kn": "Kannada",
        "ml": "Malayalam",
        "mr": "Marathi",
        "bn": "Bengali",
        "gu": "Gujarati",
        "pa": "Punjabi",
        "or": "Odia",
        "as": "Assamese",
        "ur": "Urdu"
    }
    return languages.get(code, "English")
