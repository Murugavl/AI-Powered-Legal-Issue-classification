# modules/question_generator.py

def get_next_question(intent, domain, current_entities):
    """
    Determines the simplified 'Smart Question' to ask the user based on 
    missing legal elements.
    """
    
    # 1. Land / Property Disputes
    if intent == "Property Dispute" or "land" in str(current_entities.get("description", "")).lower():
        if not current_entities.get("location"):
            return "Where is this property located?"
        if "title_deed" not in current_entities and "ownership" not in str(current_entities).lower():
            return "Do you have the title deed or documents proving ownership?"
        if "survey_number" not in current_entities:
            return "Do you know the Survey Number or Patta details?"

    # 2. Theft / Burglary
    if intent == "Theft":
        if not current_entities.get("date"):
            return "When did the theft occur?"
        if not current_entities.get("location"):
            return "Where did this happen?"
        if "stolen_items" not in current_entities and "amount" not in current_entities:
            return "What specific items were stolen, and what is their approximate value?"
        if "witness" not in str(current_entities).lower():
             return "Were there any witnesses or CCTV cameras nearby?"

    # 3. Cheating / Fraud
    if intent == "Cheating":
        if "amount" not in current_entities:
           return "What was the total amount involved in this transaction?"
        if "transaction_proof" not in str(current_entities).lower() and "agreement" not in str(current_entities).lower():
            return "Do you have any written agreement, bank transfer details, or proof of the transaction?"

    # 4. Domestic Violence / Harassment
    if intent == "Domestic Violence" or domain == "Family":
        if "safety" not in str(current_entities).lower(): # Generic check
             # If high risk context detected elsewhere, this might be overridden, but good to have.
             pass 
        if "date" not in current_entities:
            return "When did the most recent incident happen?"
        if "police_complaint" not in str(current_entities).lower():
            return "Have you filed any previous police complaints regarding this?"

    # Default fallback for generic required fields
    if not current_entities.get("name"):
        return "To proceed, could you please state your full name?"
    
    if not current_entities.get("location") and domain != "General Legal":
        return "Which city or location did this incident take place in?"

    return None
