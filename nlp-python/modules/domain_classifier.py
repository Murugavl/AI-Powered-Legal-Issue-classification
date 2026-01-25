def classify_domain(text):
    text_lower = text.lower()
    
    if any(w in text_lower for w in ["theft", "murder", "assault", "beat", "kill", "threat"]):
        return "Criminal Law (IPC/CrPC)"
        
    if any(w in text_lower for w in ["land", "property", "rent", "tenant", "money", "debt"]):
        return "Civil Law"
        
    if any(w in text_lower for w in ["divorce", "wife", "husband", "custody", "dowry"]):
        return "Family Law"
        
    if any(w in text_lower for w in ["product", "service", "defective", "warranty", "refund"]):
        return "Consumer Protection"
        
    if any(w in text_lower for w in ["job", "salary", "wage", "terminate", "boss"]):
        return "Labour Law"
        
    return "General Legal"
