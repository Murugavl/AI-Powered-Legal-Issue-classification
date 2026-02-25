"""
Bilingual Document Generator
Generates legal documents in both user's language and English
"""

from llm_provider import llm
from langchain_core.messages import HumanMessage
import json


def generate_bilingual_document(intent: str, facts: dict, user_language: str) -> dict:
    """
    Generate document in both user language and English
    
    Returns:
        {
            "user_language_content": str,
            "english_content": str,
            "document_type": str,
            "readiness_score": int
        }
    """
    
    # Generate in user's language first
    user_lang_content = generate_document_in_language(intent, facts, user_language)
    
    # Generate in English
    english_content = generate_document_in_language(intent, facts, "en")
    
    # Calculate readiness score
    readiness_score = calculate_readiness_score(facts)
    
    # Determine document type
    document_type = determine_document_type(intent)
    
    return {
        "user_language_content": user_lang_content,
        "english_content": english_content,
        "document_type": document_type,
        "readiness_score": readiness_score,
        "user_language": user_language
    }


def generate_document_in_language(intent: str, facts: dict, language: str) -> str:
    """Generate document in specified language"""
    
    lang_name = get_language_name(language)
    
    prompt = f"""
    You are an AI Legal Assistant integrated into a legal document automation system.

    [INPUT CONTEXT]
    Intent: {intent}
    Retrieved Facts: {json.dumps(facts)}
    Target Language: {lang_name} ({language})

    --------------------------------
    TASK
    --------------------------------
    Generate a legally structured, authority-ready document in {lang_name}.
    
    --------------------------------
    GLOBAL CONSTRAINTS (STRICT)
    --------------------------------
    • Use ONLY {lang_name} language.
    • DO NOT translate or localize text automatically.
    • NEVER modify amounts, dates, or quantities.
    • If an amount is provided (e.g., ₹50,000), use it EXACTLY as given.
    • If information is missing, use placeholders like [MISSING: field_name].
    • Use neutral and factual language only.

    --------------------------------
    DOCUMENT TYPE SELECTION RULE
    --------------------------------
    Select document type using rules:
    • Rental deposit / landlord dispute → Legal Notice
    • Consumer purchase issue → Consumer Complaint Draft
    • Criminal allegation / theft / assault → FIR Draft (First Information Report)
    • Government information request → RTI Application
    • Other → Choose most appropriate formal legal draft.

    DO NOT default to court format unless appropriate.

    --------------------------------
    DOCUMENT STRUCTURE (MANDATORY)
    --------------------------------
    1. **Document Title** (e.g., "First Information Report", "Legal Notice")
    2. **To**: [Authority Name and Address]
    3. **From**: [User Name and Address]
    4. **Subject**: Brief description of the matter
    5. **Respected Sir/Madam**,
    6. **Introduction**: State who you are and purpose
    7. **Facts of the Case**: Chronological, factual narration
    8. **Details**: Specific information (dates, amounts, locations, parties)
    9. **Evidence**: List of documents/proof available
    10. **Prayer/Request**: What action you are requesting
    11. **Conclusion**: Respectful closing
    12. **Signature Block**: Name, Date, Place

    --------------------------------
    LANGUAGE-SPECIFIC FORMATTING
    --------------------------------
    • For Hindi/Tamil/Regional languages: Use appropriate formal salutations
    • Maintain respectful tone appropriate to the language
    • Use proper legal terminology in that language
    • Ensure dates are in DD-MM-YYYY format
    • Currency should be in ₹ (Rupees) format

    --------------------------------
    WHAT NOT TO INCLUDE
    --------------------------------
    • Do NOT include legal conclusions or predictions
    • Do NOT cite specific laws or sections (unless explicitly provided in facts)
    • Do NOT hallucinate names, dates, or amounts
    • DO NOT include irrelevant details or facts not explicitly stated in the input context.
    • If a fact is marked as 'EXPLICITLY_DENIED', omit it utterly and do not mention it.
    • Do NOT include lawyer signature or court stamps
    • Do NOT make promises about outcomes

    --------------------------------
    OUTPUT FORMAT (STRICT)
    --------------------------------
    Return ONLY the complete legal document text.
    Do NOT include:
    - Markdown formatting
    - Explanatory notes
    - Readiness scores
    - Disclaimers (will be added separately)
    
    Just return the clean, formatted legal document text.
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


def calculate_readiness_score(facts: dict) -> int:
    """
    Calculate document readiness based on available evidence
    
    Score calculation:
    - Written agreement / receipts → +25
    - Proof of payment → +25
    - Written communication (emails/messages) → +25
    - Proof of possession / return / delivery → +25
    """
    score = 0
    
    evidence = facts.get("evidence_available", "")
    if isinstance(evidence, str):
        evidence_lower = evidence.lower()
        
        if any(term in evidence_lower for term in ["agreement", "contract", "receipt", "bill", "invoice"]):
            score += 25
            
        if any(term in evidence_lower for term in ["payment", "transaction", "bank statement", "cheque"]):
            score += 25
            
        if any(term in evidence_lower for term in ["email", "message", "whatsapp", "sms", "letter", "communication"]):
            score += 25
            
        if any(term in evidence_lower for term in ["photo", "video", "witness", "proof", "document"]):
            score += 25
    
    # Ensure minimum score if basic facts are present
    if len(facts) >= 5 and score == 0:
        score = 40  # Basic facts present but no strong evidence
    
    return min(score, 100)


def determine_document_type(intent: str) -> str:
    """Determine document type from intent"""
    if not intent:
        return "general_petition"
    
    intent_lower = intent.lower()
    
    if any(term in intent_lower for term in ["theft", "stolen", "robbery", "assault", "harassment", "crime", "fir", "police"]):
        return "police_complaint"
    
    if any(term in intent_lower for term in ["consumer", "product", "service", "refund", "defective"]):
        return "consumer_complaint"
    
    if any(term in intent_lower for term in ["rti", "information", "government", "public"]):
        return "rti_application"
    
    if any(term in intent_lower for term in ["landlord", "tenant", "rent", "deposit", "eviction", "notice"]):
        return "legal_notice"
    
    if any(term in intent_lower for term in ["divorce", "maintenance", "custody", "family"]):
        return "family_petition"
    
    return "general_petition"


def get_language_name(code: str) -> str:
    """Get full language name from code"""
    languages = {
        "en": "English",
        "hi": "Hindi",
        "ta": "Tamil",
        "te": "Telugu",
        "kn": "Kannada",
        "ml": "Malayalam",
        "mr": "Marathi",
        "bn": "Bengali",
        "gu": "Gujarati"
    }
    return languages.get(code, "English")
