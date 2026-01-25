from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from langdetect import detect
import spacy
import re
from datetime import datetime

app = FastAPI(title="Legal Document NLP Service", version="2.0")

# CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    print("Warning: SpaCy model not found. Run 'python -m spacy download en_core_web_sm'")
    nlp = None 

# ==================== Request/Response Models ====================

class DocumentRequest(BaseModel):
    text: str

class EntityExtraction(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    location: Optional[str] = None
    accused: Optional[str] = None
    issue_type: Optional[str] = None  # e.g., "theft", "assault", "property_dispute"
    description: Optional[str] = None

class AnalysisResponse(BaseModel):
    language: str
    entities: EntityExtraction
    completeness: Dict[str, bool]  # Which fields are complete
    next_question: Optional[str] = None  # Next question to ask user
    confidence: float  # 0.0 to 1.0

class IssueClassificationResponse(BaseModel):
    issue_type: str  # "police_complaint", "civil_suit", "government_application"
    sub_category: str  # "theft", "assault", "property_dispute", "RTI", etc.
    required_fields: List[str]  # Which fields are mandatory
    suggested_authority: str  # "Police Station", "Civil Court", "Tehsildar Office"

@app.get("/")
def read_root():
    return {
        "message": "Legal Document NLP Service",
        "version": "2.0",
        "endpoints": ["/analyze", "/translate", "/classify"],
        "status": "running"
    }

@app.post("/analyze", response_model=AnalysisResponse)
def analyze_text(request: DocumentRequest):
    """
    Analyze user input text to extract entities and determine next steps.
    """
    text = request.text
    
    # Language Detection
    try:
        lang = detect(text)
    except:
        lang = "unknown"
    
    # Initialize variables
    name = None
    date = None
    location = None
    accused = None
    description = text  # Store full text as description

    # Load SpaCy model
    # Note: Global variable 'nlp' should ideally be loaded at startup
    global nlp
    if 'nlp' not in globals():
        try:
           nlp = spacy.load("en_core_web_sm")
        except:
           # Fallback if not loaded
           nlp = None

    # Process text with SpaCy
    doc = nlp(text) if nlp else None

    # Extract Entities using SpaCy
    if doc:
        # PERSON
        if not name:
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    name = ent.text
                    break
        
        # DATE
        if not date:
            for ent in doc.ents:
                if ent.label_ == "DATE":
                    date = ent.text
                    break
        
        # GPE (Geopolitical Entity) or LOC for Location
        if not location:
             for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC"]:
                    location = ent.text
                    break
                    
    # Regex Fallback (existing logic)
    
    # Name Fallback
    if not name:
        name_match = re.search(
            r"(?:Name|I am|My name is|This is)\s*[:\-]?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)",
            text,
            re.IGNORECASE
        )
        if name_match:
            name = name_match.group(1)

    # Date Fallback
    if not date:
        date_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", text)
        if date_match:
            date = date_match.group(1)
        else:
            # Try natural language: "yesterday", "today", "last week"
            if re.search(r"\byesterday\b", text, re.IGNORECASE):
                from datetime import datetime, timedelta
                yesterday = datetime.now() - timedelta(days=1)
                date = yesterday.strftime("%d/%m/%Y")
            elif re.search(r"\btoday\b", text, re.IGNORECASE):
                date = datetime.now().strftime("%d/%m/%Y")

    # Location Fallback
    if not location:
        location_match = re.search(
            r"(?:at|in|Location|place|near)\s*[:\-]?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)",
            text,
            re.IGNORECASE
        )
        if location_match:
            location = location_match.group(1)

    # Accused: "against X", "accused X", "by X"
    if not accused:
        accused_match = re.search(
            r"(?:against|accused|suspect|by|person named)\s*[:\-]?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)",
            text,
            re.IGNORECASE
        )
        if accused_match:
            accused = accused_match.group(1)
    
    # Classify the issue
    classification = classify_issue(text)
    issue_type = classification["sub_category"]
    required_fields = classification["required_fields"]

    # Create entity object
    entities = EntityExtraction(
        name=name,
        date=date,
        location=location,
        accused=accused,
        issue_type=issue_type,
        description=description
    )

    # Check completeness
    completeness = check_completeness(entities, required_fields)

    # Get next question
    next_question = get_next_question(entities, required_fields, lang)

    # Calculate confidence (simple heuristic: % of required fields filled)
    filled_count = sum(1 for v in completeness.values() if v)
    confidence = filled_count / len(required_fields) if required_fields else 1.0

    return AnalysisResponse(
        language=lang,
        entities=entities,
        completeness=completeness,
        next_question=next_question,
        confidence=confidence
    )

@app.post("/classify", response_model=IssueClassificationResponse)
def classify_legal_issue(request: DocumentRequest):
    """
    Classify the legal issue and return required fields and suggested authority.
    """
    classification = classify_issue(request.text)

    return IssueClassificationResponse(
        issue_type=classification["issue_type"],
        sub_category=classification["sub_category"],
        required_fields=classification["required_fields"],
        suggested_authority=classification["suggested_authority"]
    )

class TranslationRequest(BaseModel):
    text: str
    target_language: str

class InteractiveQARequest(BaseModel):
    session_id: str
    user_response: str
    context: Dict  # Stores previous answers


# ==================== Helper Functions ====================

def classify_issue(text: str) -> Dict:
    """
    Classify the legal issue based on keywords.
    In production, replace with ML model (e.g., fine-tuned transformer).
    """
    text_lower = text.lower()

    # Police Complaints
    if any(word in text_lower for word in ["theft", "stolen", "robbery", "burglary"]):
        return {
            "issue_type": "police_complaint",
            "sub_category": "theft",
            "required_fields": ["name", "date", "location", "description", "stolen_items"],
            "suggested_authority": "Police Station"
        }
    elif any(word in text_lower for word in ["assault", "attack", "beat", "hit", "violence"]):
        return {
            "issue_type": "police_complaint",
            "sub_category": "assault",
            "required_fields": ["name", "date", "location", "accused", "description", "injuries"],
            "suggested_authority": "Police Station"
        }
    elif any(word in text_lower for word in ["harassment", "threaten", "intimidation"]):
        return {
            "issue_type": "police_complaint",
            "sub_category": "harassment",
            "required_fields": ["name", "date", "location", "accused", "description"],
            "suggested_authority": "Police Station"
        }

    # Civil Matters
    elif any(word in text_lower for word in ["property", "land", "boundary", "dispute", "ownership"]):
        return {
            "issue_type": "civil_suit",
            "sub_category": "property_dispute",
            "required_fields": ["name", "location", "accused", "description", "property_details"],
            "suggested_authority": "Civil Court"
        }
    elif any(word in text_lower for word in ["contract", "agreement", "breach"]):
        return {
            "issue_type": "civil_suit",
            "sub_category": "contract_dispute",
            "required_fields": ["name", "date", "accused", "description", "contract_details"],
            "suggested_authority": "Civil Court"
        }

    # Government Applications
    elif any(word in text_lower for word in ["rti", "right to information", "public information"]):
        return {
            "issue_type": "government_application",
            "sub_category": "rti",
            "required_fields": ["name", "address", "description", "department"],
            "suggested_authority": "Public Information Officer"
        }
    elif any(word in text_lower for word in ["pension", "ration card", "certificate", "government benefit"]):
        return {
            "issue_type": "government_application",
            "sub_category": "welfare_benefit",
            "required_fields": ["name", "address", "description", "benefit_type"],
            "suggested_authority": "Tehsildar / Block Office"
        }

    # Default
    else:
        return {
            "issue_type": "general_complaint",
            "sub_category": "unclassified",
            "required_fields": ["name", "date", "location", "description"],
            "suggested_authority": "Appropriate Authority"
        }

def get_next_question(entities: EntityExtraction, required_fields: List[str], language: str = "en") -> Optional[str]:
    """
    Determine the next question to ask based on missing required fields.
    Returns one question at a time.
    """
    # Check each required field in order
    field_questions = {
        "name": "What is your full name?",
        "date": "When did this incident occur? (Please provide date in DD/MM/YYYY format)",
        "location": "Where did this happen? (Please provide the location/address)",
        "accused": "Do you know who is responsible? (If yes, please provide their name and details)",
        "description": "Please describe what happened in detail.",
        "stolen_items": "What items were stolen? Please list them.",
        "injuries": "Did you sustain any injuries? Please describe them.",
        "property_details": "Please provide details about the property (survey number, location, etc.)",
        "contract_details": "Please provide details about the contract or agreement.",
        "department": "Which government department does this relate to?",
        "benefit_type": "What type of benefit or service are you applying for?",
        "address": "What is your complete address?"
    }

    # Find first missing required field
    for field in required_fields:
        entity_value = getattr(entities, field, None) if hasattr(entities, field) else None
        if not entity_value:
            return field_questions.get(field, f"Please provide: {field}")

    return None  # All required fields are complete

def check_completeness(entities: EntityExtraction, required_fields: List[str]) -> Dict[str, bool]:
    """
    Check which required fields are complete.
    """
    completeness = {}
    for field in required_fields:
        entity_value = getattr(entities, field, None) if hasattr(entities, field) else None
        completeness[field] = bool(entity_value)
    return completeness

@app.post("/translate")
def translate_text(request: TranslationRequest):
    # Mock Translation Logic for Prototype
    # In production, this would call Bhashini API
    translated_text = f"[Translated to {request.target_language}]: {request.text}"
    return {"translated_text": translated_text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
