# modules/readiness_scorer.py
from typing import Dict, List

def calculate_readiness(entities: Dict, required_fields: List[str], text: str) -> Dict:
    """
    Calculates a Legal Readiness Score (0-100) and Status.
    Factors:
    - Field Completeness (High weight)
    - Evidence Keywords (Medium weight)
    - Description Length/Specificity (Low weight)
    """
    score = 0
    max_score = 100
    
    # 1. Completeness Check (60 points)
    filled_fields = 0
    for field in required_fields:
        if entities.get(field):
            filled_fields += 1
    
    if required_fields:
        completeness_ratio = filled_fields / len(required_fields)
        score += completeness_ratio * 60
    else:
        # If no strict requirements, assume 50% base if purely description exists
        if entities.get("description"):
            score += 40

    # 2. Evidence Strength (30 points)
    # Look for keywords indicating strong evidence
    evidence_keywords = ["written", "agreement", "contract", "deed", "bill", "invoice", 
                         "witness", "cctv", "recording", "photo", "police", "complaint", 
                         "receipt", "proof", "signed"]
    
    text_lower = text.lower()
    evidence_count = sum(1 for word in evidence_keywords if word in text_lower)
    
    # Cap evidence points at 30 (e.g., 3 keywords = max)
    evidence_points = min(evidence_count * 10, 30)
    score += evidence_points

    # 3. Description Specificity (10 points)
    # Very rough heuristic: length of description
    desc_len = len(text)
    if desc_len > 200:
        score += 10
    elif desc_len > 100:
        score += 5

    # Determine Status
    final_score = int(score)
    status = "NOT_ACTIONABLE"
    
    if final_score >= 80:
        status = "READY"
    elif final_score >= 50:
        status = "WEAK_CASE"
    else:
        status = "NOT_ACTIONABLE"

    # Feedback Message
    feedback = []
    if final_score < 50:
        feedback.append("Missing critical details. Please provide more specifics.")
    elif final_score < 80:
        if evidence_points < 10:
            feedback.append("Case implies legal issue but lacks mentioned evidence (witnesses, documents).")
        else:
            feedback.append("Good start, but more specific details (dates, names) would strengthen the case.")
    else:
        feedback.append("Strong case details detected. Ready for document generation.")

    return {
        "score": final_score,
        "status": status,
        "feedback": " ".join(feedback)
    }
