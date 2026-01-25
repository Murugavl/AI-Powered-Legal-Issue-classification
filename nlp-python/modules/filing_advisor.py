# modules/filing_advisor.py

def get_filing_guidance(intent, sub_category, domain):
    """
    Returns structured filing guidance based on the legal issue.
    """
    guidance = {
        "authority": "Unknown Authority",
        "jurisdiction_hint": "Jurisdiction typically depends on where the incident occurred or where the defendant resides.",
        "enclosures": [],
        "next_steps": []
    }

    intent_lower = intent.lower() if intent else ""
    sub_lower = sub_category.lower() if sub_category else ""

    # 1. Police Matters (Theft, Assault, Harassment)
    if "theft" in intent_lower or "assault" in intent_lower or "harassment" in intent_lower or "police" in domain.lower():
        guidance["authority"] = "Station House Officer (SHO)"
        guidance["jurisdiction_hint"] = "File at the Police Station covering the area where the incident happened."
        guidance["enclosures"] = [
            "Proof of Identity (Aadhar/PAN)",
            "Proof of Incident (Photos, Medical Report if assault)",
            "List of Stolen Items (if theft)",
            "Witness Details (if any)"
        ]
        guidance["next_steps"] = [
            "Submit the complaint in duplicate (2 copies).",
            "Get a 'CSR' (Community Service Register) receipt or FIR number immediately.",
            "If police refuse to file, send via Registered Post to the Superintendent of Police (SP)."
        ]

    # 2. Cyber Crime
    elif "cyber" in intent_lower or "online" in intent_lower:
        guidance["authority"] = "Cyber Crime Cell / National Cyber Crime Portal"
        guidance["jurisdiction_hint"] = "Can be filed online at cybercrime.gov.in or nearest Cyber Cell."
        guidance["enclosures"] = [
            "Screenshots of the fraudulent transaction/profile",
            "Bank Statement highlighting the transaction",
            "URL of the website/social media profile"
        ]
        guidance["next_steps"] = [
            "Register complaint on www.cybercrime.gov.in.",
            "Note down the Acknowledgement ID.",
            "Contact your bank to freeze numbers involved."
        ]

    # 3. Consumer Disputes
    elif "consumer" in domain.lower() or "defective" in intent_lower:
        guidance["authority"] = "District Consumer Disputes Redressal Commission"
        guidance["jurisdiction_hint"] = "District Commission where you reside or where the seller does business."
        guidance["enclosures"] = [
            "Bill / Invoice of purchase",
            "Proof of defect (photos/expert report)",
            "Copy of previous complaints/emails sent to seller"
        ]
        guidance["next_steps"] = [
            "Send a Legal Notice first (wait for 15-30 days).",
            "If no response, file consumer complaint online (EDAakhil) or physically.",
            "Pay the nominal court fee online."
        ]

    # 4. Property Disputes
    elif "property" in intent_lower or "land" in intent_lower:
        guidance["authority"] = "Civil Court / Revenue Divisional Officer (RDO)"
        guidance["jurisdiction_hint"] = "Court within whose local limits the property is situated."
        guidance["enclosures"] = [
            "Title Deed / Sale Deed",
            "Patta / Chitta / Adangal extracts",
            "Encumbrance Certificate (EC)",
            "Survey Map"
        ]
        guidance["next_steps"] = [
            "Consult a lawyer for drafting a Civil Suit.",
            "Apply for an Injunction if there is threat of dispossession.",
            "File a police complaint if there is criminal trespass."
        ]
    
    # 5. Generic Fallback
    else:
        guidance["authority"] = "Relevant Local Authority"
        guidance["enclosures"] = ["Identity Proof", "Any Relevant Documents"]
        guidance["next_steps"] = ["Consult a legal expert for specific advice."]

    return guidance
