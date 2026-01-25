# modules/translator.py

# In a real production environment, this would call the Bhashini API or Google Translate API.
# For this prototype, we simulate translation to demonstrate the architectural flow.

def detect_lang(text):
    # Simple heuristic
    if any(char for char in text if ord(char) > 127):
        # Allow passing distinct language codes if detected libraries were available
        # For now, simplistic check for 'non-ascii' implying local lang
        return "local" 
    return "en"

def translate_to_english(text, source_lang):
    if source_lang == "en":
        return text
    
    # Mock translations for demo
    translations = {
        "vanakkam": "hello",
        "thiruttu": "theft",
        "panam": "money",
        "adi": "beat",
        "police": "police" # Shared words
    }
    
    # Very naive word-by-word replacement for demo
    words = text.lower().split()
    english_words = [translations.get(w, w) for w in words]
    return " ".join(english_words)

def translate_from_english(text, target_lang):
    if target_lang == "en":
        return text
        
    # Mock translations for demo responses
    translations = {
        "what is your full name?": "Ungal muzhu peyar enna?", # Tamil
        "where did this happen?": "Idhu enge nadandhadhu?",
        "please describe what happened.": "Dayavu seidhu enna nadandhadhu endru vivarikkavum.",
        "file fir": "Mudhal Thagaval Arikkai (FIR)",
        "criminal law": "Kuttraviyal Sattam"
    }
    
    return translations.get(text.lower(), text)
