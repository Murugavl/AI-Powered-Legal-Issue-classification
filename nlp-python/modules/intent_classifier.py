import re

def detect_intent(text):
    text_lower = text.lower()
    
    # Keyword-based heuristics (Placeholder for ML model)
    if any(w in text_lower for w in ["police", "fir", "arrest", "theft", "stolen", "attack", "harassment", "abuse", "beat", "hit"]):
        return "File FIR / Complaint"
    
    if any(w in text_lower for w in ["legal notice", "sue", "defamation", "breach", "cheat", "fraud"]):
        return "Send Legal Notice"
        
    if any(w in text_lower for w in ["affidavit", "declare", "oath", "name change"]):
        return "Create Affidavit"
        
    if any(w in text_lower for w in ["rti", "information", "public master"]):
        return "File RTI Application"

    if any(w in text_lower for w in ["landlord", "tenant", "rent", "eviction", "property", "house owner", "lease", "advance", "deposit"]):
        return "Property Dispute"
        
    return "General Consultation"
