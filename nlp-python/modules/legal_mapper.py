# modules/legal_mapper.py

def map_legal_sections(text, intent, domain):
    """
    Maps the detected intent and keywords to specific legal sections.
    Returns a string summary of the section.
    """
    text_lower = text.lower()
    sections = []

    # Criminal Law (IPC)
    if "theft" in text_lower or "stole" in text_lower or intent == "Theft":
        sections.append("IPC Section 378 (Theft)")
        sections.append("IPC Section 379 (Punishment for Theft)")
    
    if "cheat" in text_lower or "fraud" in text_lower or intent == "Cheating":
        sections.append("IPC Section 420 (Cheating and dishonestly inducing delivery of property)")
    
    if "assault" in text_lower or "beat" in text_lower or "hit" in text_lower:
        sections.append("IPC Section 323 (Punishment for voluntarily causing hurt)")
        sections.append("IPC Section 351 (Assault)")

    if "murder" in text_lower or "kill" in text_lower:
        sections.append("IPC Section 302 (Punishment for murder) - ALERT: HIGH SEVERITY")

    if "dowry" in text_lower:
        sections.append("Dowry Prohibition Act, 1961")
        sections.append("IPC Section 498A (Cruelty by husband or relatives)")
    
    if "cyber" in text_lower or "online" in text_lower and "fraud" in text_lower:
        sections.append("IT Act Section 66D (Punishment for cheating by personation by using computer resource)")

    # Civil / Consumer
    if domain == "Consumer":
        sections.append("Consumer Protection Act, 2019 - Section 35 (Filing a complaint)")
    
    if "check bounce" in text_lower or "cheque" in text_lower:
        sections.append("Negotiable Instruments Act - Section 138")

    if not sections:
        return None

    # Format output
    return " | ".join(sections)
