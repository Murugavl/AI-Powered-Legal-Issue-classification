import os
import google.generativeai as genai
import json
from dotenv import load_dotenv

# Load env variables (including GOOGLE_API_KEY from ../.env if possible, or local .env)
load_dotenv(dotenv_path="../.env") # Try root .env
if not os.getenv("GOOGLE_API_KEY"):
    load_dotenv() # Try local .env

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

generation_config = {
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 1024,
    "response_mime_type": "application/json",
}

def analyze_with_llm(text_history: str, current_entities: dict = None):
    """
    Uses Google Gemini (or any LLM) to analyze the legal context.
    Returns a structured JSON response.
    """
    if not api_key:
        return {
            "error": "Missing GOOGLE_API_KEY. Please add it to your .env file."
        }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
        system_instruction="""
        You are an expert AI Legal Assistant (Satta Vizhi). Your role is to help a user draft a legal document (like a Police Complaint, Rental Agreement notice, Affidavit, etc.) by gathering facts.

        Your tasks:
        1. **Intent Classification**: Determine the legal issue (e.g., "Property Dispute", "Domestic Violence", "Theft", "Cheating").
        2. **Entity Extraction**: Extract specific facts from the text (Name, Date, Location, Amount, Accused Name, etc.).
        3. **Readiness Check**: Determine if we have enough info to draft the document.
        4. **Question Generation**: If information is missing, generate the *single most important* follow-up question. Be polite but professional.
           - If the user has NOT provided their name yet, and the incident details are clear, ask for their full name to formalize the request.
           - If the incident is vague, ask for clarification.
        
        Output JSON Format:
        {
            "intent": "String (detected legal intent)",
            "confidence": 0.0 to 1.0,
            "entities": {
                "name": "...",
                "date": "...",
                "location": "...",
                "description": "...",
                "accused": "...",
                "amount": "..."
            },
            "next_question": "String (The next question to ask the user, or null if ready)",
            "readiness_score": 0 to 100,
            "legal_advice": "Short Filing Guidance (e.g., 'File at local Civil Court')"
        }
        """
    )
    
    # Construct prompt
    prompt = f"""
    Current Conversation History:
    {text_history}
    
    Already Known Entities:
    {json.dumps(current_entities if current_entities else {})}
    
    Analyze the latest input and update the state.
    """
    
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"LLM Error: {e}")
        return {
            "error": str(e),
            "next_question": "I apologize, I am having trouble connecting to my legal brain. Could you repeat that?"
        }
