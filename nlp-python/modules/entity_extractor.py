import spacy
import re

# Load model once at module level if possible, or lazy load
nlp_model = None

def get_spacy_model():
    global nlp_model
    if nlp_model is None:
        try:
            nlp_model = spacy.load("en_core_web_sm")
        except:
            return None
    return nlp_model

def extract_entities(text):
    nlp = get_spacy_model()
    doc = nlp(text) if nlp else None
    
    entities = {
        "name": None,
        "date": None,
        "location": None,
        "amount": None,
        "relationship": None
    }
    
    if doc:
        for ent in doc.ents:
            if ent.label_ == "PERSON" and not entities["name"]: 
                entities["name"] = ent.text
            elif ent.label_ == "DATE" and not entities["date"]: 
                entities["date"] = ent.text
            elif ent.label_ in ["GPE", "LOC"] and not entities["location"]: 
                entities["location"] = ent.text
            elif ent.label_ == "MONEY" and not entities["amount"]:
                entities["amount"] = ent.text
    
    # --- Regex Fallbacks / Enhancements ---
    
    # Name pattern (My name is X)
    if not entities["name"]:
        m = re.search(r"(?:Name|I am|My name is)\s*[:\-]?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", text, re.IGNORECASE)
        if m: entities["name"] = m.group(1)
        
    # Amount pattern (Rs. 5000, 50k)
    if not entities["amount"]:
         m = re.search(r"(?:Rs\.?|INR|₹)\s*([\d,]+)", text, re.IGNORECASE)
         if m: entities["amount"] = m.group(1)
         
    # Relationship pattern (My landlord, my wife, my boss)
    rel_keywords = ["landlord", "tenant", "wife", "husband", "neighbor", "boss", "employer", "employee"]
    for word in rel_keywords:
        if re.search(r"\b(my|the)\s+" + word + r"\b", text, re.IGNORECASE):
            entities["relationship"] = word
            break
            
    return entities
