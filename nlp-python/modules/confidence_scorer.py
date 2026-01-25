def calculate_confidence(text, entities):
    score = 0.0
    
    # 1. Text Length (Too short = low confidence)
    if len(text.split()) > 10:
        score += 0.2
    
    # 2. Key Entities Present
    if entities.get("name"): score += 0.2
    if entities.get("date"): score += 0.2
    if entities.get("location"): score += 0.2
    
    # 3. Specificity (Detecting numbers/dates usually implies detail)
    import re
    if re.search(r"\d", text):
        score += 0.1
        
    # Cap at 1.0
    return min(score, 1.0)
    
def is_ambiguous(confidence_score):
    return confidence_score < 0.5
