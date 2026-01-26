from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from langdetect import detect
import spacy
# re and datetime removed as they were unused

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
    issue_type: Optional[str] = None
    description: Optional[str] = None

class ReadinessAssessment(BaseModel):
    score: int
    status: str
    feedback: str

class FilingGuidance(BaseModel):
    authority: str
    jurisdiction_hint: str
    enclosures: List[str]
    next_steps: List[str]

class AnalysisResponse(BaseModel):
    language: str
    entities: EntityExtraction
    completeness: Dict[str, bool]
    next_question: Optional[str] = None
    confidence: float
    readiness: Optional[ReadinessAssessment] = None
    filing_guidance: Optional[FilingGuidance] = None
    legal_sections: Optional[str] = None

class IssueClassificationResponse(BaseModel):
    issue_type: str
    sub_category: str
    required_fields: List[str]
    suggested_authority: str

class TranslationRequest(BaseModel):
    text: str
    target_language: str

# ==================== Imports ====================
from modules.intent_classifier import detect_intent
from modules.domain_classifier import classify_domain
from modules.confidence_scorer import calculate_confidence, is_ambiguous
from modules.entity_extractor import extract_entities
from modules.translator import translate_to_english, translate_from_english, detect_lang
from modules.legal_mapper import map_legal_sections
from modules.question_generator import get_next_question
from modules.readiness_scorer import calculate_readiness
from modules.filing_advisor import get_filing_guidance

# ==================== Endpoints ====================

@app.get("/")
def read_root():
    return {
        "message": "Legal Document NLP Service",
        "version": "2.0",
        "status": "running"
    }

@app.post("/analyze", response_model=AnalysisResponse)
def analyze_text(request: DocumentRequest):
    """
    Analyze user input using the Integrated Architecture.
    """
    original_text = request.text
    
    # 0. Language Detection
    lang = detect_lang(original_text)
    
    # 1. Translate to English
    text_en = translate_to_english(original_text, lang)
    
    # 2. Intent & Domain
    intent = detect_intent(text_en)
    domain = classify_domain(text_en)

    # 3. Entity Extraction
    extracted_data = extract_entities(text_en)
    
    name = extracted_data.get("name")
    date = extracted_data.get("date")
    location = extracted_data.get("location")
    accused = None # extractor placeholder
    
    entities_dict = {
        "name": name,
        "date": date,
        "location": location,
        "accused": accused,
        "issue_type": intent,
        "domain": domain,
        "description": original_text,
        "relationship": extracted_data.get("relationship")
    }

    # 4. Confidence Scoring
    confidence = calculate_confidence(text_en, entities_dict)
    
    # 5. Legal Section Mapping
    legal_sections = map_legal_sections(text_en, intent, domain)

    # 6. Smart Question Generation
    next_question_en = get_next_question(intent, domain, entities_dict)
    
    if not next_question_en and is_ambiguous(confidence):
         next_question_en = "Could you provide more specific details about what happened?"

    # 7. Translate Response
    next_question_local = translate_from_english(next_question_en, lang) if next_question_en else None

    # 8. Completeness Check
    classification = classify_issue(text_en)
    required_fields = classification["required_fields"]
    
    entities_model = EntityExtraction(
        name=name,
        date=date,
        location=location,
        accused=accused,
        issue_type=intent,
        description=original_text
    )
    
    completeness = check_completeness(entities_model, required_fields)

    # 9. Readiness Score
    readiness_result = calculate_readiness(entities_dict, required_fields, text_en)

    # 10. Filing Guidance
    filing_info = get_filing_guidance(intent, classification.get("sub_category", ""), domain)

    # Construct Response
    response_data = {
        "language": lang,
        "entities": entities_model,
        "completeness": completeness,
        "next_question": next_question_local,
        "confidence": confidence,
        "readiness": readiness_result,
        "filing_guidance": filing_info,
        "legal_sections": legal_sections
    }
    
    return AnalysisResponse(**response_data)

@app.post("/classify", response_model=IssueClassificationResponse)
def classify_legal_issue_endpoint(request: DocumentRequest):
    classification = classify_issue(request.text)
    return IssueClassificationResponse(
        issue_type=classification["issue_type"],
        sub_category=classification["sub_category"],
        required_fields=classification["required_fields"],
        suggested_authority=classification["suggested_authority"]
    )

@app.post("/translate")
def translate_text_endpoint(request: TranslationRequest):
    return {"translated_text": f"[Translated to {request.target_language}]: {request.text}"}

# ==================== Helpers ====================

def classify_issue(text: str) -> Dict:
    text_lower = text.lower()
    if any(word in text_lower for word in ["theft", "stolen", "robbery"]):
        return {
            "issue_type": "police_complaint",
            "sub_category": "theft",
            "required_fields": ["name", "date", "location", "description"],
            "suggested_authority": "Police Station"
        }
    elif any(word in text_lower for word in ["property", "land", "dispute"]):
        return {
            "issue_type": "civil_suit",
            "sub_category": "property_dispute",
            "required_fields": ["name", "location", "property_details"],
            "suggested_authority": "Civil Court"
        }
    else:
        return {
            "issue_type": "general_complaint",
            "sub_category": "unclassified",
            "required_fields": ["name", "description"],
            "suggested_authority": "Authority"
        }

def check_completeness(entities: EntityExtraction, required_fields: List[str]) -> Dict[str, bool]:
    completeness = {}
    for field in required_fields:
        val = getattr(entities, field, None)
        completeness[field] = bool(val)
    return completeness

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
