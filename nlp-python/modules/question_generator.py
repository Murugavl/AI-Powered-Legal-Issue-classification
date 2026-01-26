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
        if "agreement" not in str(current_entities).lower() and "lease" not in str(current_entities).lower():
            return "Do you have a written rental agreement or lease deed?"
        if "notice" not in str(current_entities).lower() and "vacat" in str(current_entities).lower():
            return "Have you received or sent any legal notice regarding eviction?"

    # 2. FIR / Complaint / Harassment
    if intent == "File FIR / Complaint":
        if "harassment" in str(current_entities.get("description", "")).lower() or "house owner" in str(current_entities.get("description", "")).lower():
            # Specific to the user's scenario
            if not current_entities.get("date"):
                return "When did the most recent incident of harassment occur?"
            if "police" not in str(current_entities).lower():
                return "Have you approached the police already, or do you need help drafting a complaint?"
        
        if not current_entities.get("date"):
            return "When did the incident occur?"
        if not current_entities.get("location"):
            return "Where did this happen?"
        if "witness" not in str(current_entities).lower():
             return "Were there any witnesses present during the incident?"

    # 3. Cheating / Fraud
    if intent == "Cheating" or intent == "Send Legal Notice":
        if "amount" not in current_entities and "fraud" in str(current_entities).lower():
           return "What was the total financial loss or amount involved?"
        if "proof" not in str(current_entities).lower():
            return "Do you have any proof of the transaction (bank statement, agreement, chat history)?"

    # 4. Domestic Violence (Specific)
    if intent == "Domestic Violence":
        if not current_entities.get("date"):
            return "When did the incident happen?"
        return "Are you currently in a safe location?"

    # Default flow: Gather core details first
    if not current_entities.get("location") and domain != "General Legal":
        return "Could you specify the location (City/Area) relevant to this issue?"

    # Ask for Name LAST, after we have some context
    if not current_entities.get("name"):
        return "To finalize the document draft, could you please state your full name?"

    return None
