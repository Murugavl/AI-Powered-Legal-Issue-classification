from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from langdetect import detect
import spacy
import re

app = FastAPI()

# Placeholder for spaCy model, will load in a real scenario
# nlp = spacy.load("en_core_web_sm") 

class DocumentRequest(BaseModel):
    text: str

class EntityExtraction(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    location: Optional[str] = None
    accused: Optional[str] = None

class AnalysisResponse(BaseModel):
    language: str
    entities: EntityExtraction

@app.get("/")
def read_root():
    return {"message": "NLP Service is running"}

@app.post("/analyze", response_model=AnalysisResponse)
def analyze_text(request: DocumentRequest):
    text = request.text
    
    # Language Detection
    try:
        lang = detect(text)
    except:
        lang = "unknown"
    
    # Regex-based extraction
    import re
    
    # Initialize variables to avoid UnboundLocalError
    name = None
    date = None
    location = None
    accused = None

    # Name: simple heuristic, looks for "Name: X" or "I am X"
    name_match = re.search(r"(?:Name|I am|My name is)\s*[:\-]?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", text, re.IGNORECASE)
    if name_match:
        name = name_match.group(1)
        
    # Date: dd/mm/yyyy or similar
    date_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", text)
    if date_match:
        date = date_match.group(1)
        
    # Location: "at X", "in X", "Location: X"
    location_match = re.search(r"(?:at|in|Location|place)\s*[:\-]?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", text, re.IGNORECASE)
    if location_match:
        location = location_match.group(1)
        
    # Accused: "against X", "accused X"
    accused_match = re.search(r"(?:against|accused|suspect)\s*[:\-]?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", text, re.IGNORECASE)
    if accused_match:
        accused = accused_match.group(1)
    
    return AnalysisResponse(
        language=lang,
        entities=EntityExtraction(
            name=name,
            date=date,
            location=location,
            accused=accused
        )
    )

class TranslationRequest(BaseModel):
    text: str
    target_language: str

@app.post("/translate")
def translate_text(request: TranslationRequest):
    # Mock Translation Logic for Prototype
    # In production, this would call Bhashini API
    translated_text = f"[Translated to {request.target_language}]: {request.text}"
    return {"translated_text": translated_text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
