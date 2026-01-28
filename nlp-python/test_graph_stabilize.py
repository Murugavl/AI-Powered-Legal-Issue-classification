from graph import process_message
import uuid
import time
import json

def test_stabilization():
    thread_id = str(uuid.uuid4())
    print(f"Starting test conversation thread: {thread_id}")

    # 1. Turn 1: Detailed Request (Should be capped at 60%, Turn Count 1)
    print("\n[Turn 1] USER: My landlord Suresh owes me 50,000 rupees deposit. I vacated last month in Chennai.")
    res = process_message(thread_id, "My landlord Suresh owes me 50,000 rupees deposit. I vacated last month in Chennai.")
    print(f"AI: {res['content']}")
    print(f"Score: {res['readiness_score']} (Expected <= 60)")
    
    # Check language lock (implicit, assumed english)
    
    # 2. Turn 2: Short answer (Should be capped at 60-70% if < 3 categories, Turn Count 2)
    # 2 distinct categories provided in T1 (landlord issue, amount, location). 
    # Let's say we provide Date.
    print("\n[Turn 2] USER: It was on January 1st.")
    res = process_message(thread_id, "It was on January 1st.")
    print(f"AI: {res['content']}")
    print(f"Score: {res['readiness_score']} (Expected <= 75 due to Turn 2)")

    # 3. Turn 3: "No" to Confirmation (Simulate rejection behavior)
    # Force score high via simulation? No, let's just observe flow.
    # Provide critical missing info "Rental Agreement status"
    print("\n[Turn 3] USER: I have a valid rental agreement.")
    res = process_message(thread_id, "I have a valid rental agreement.")
    print(f"AI: {res['content']}")
    print(f"Score: {res['readiness_score']}")
    
    # If we hit confirmation, let's reject it to test retry logic
    if "continue" in res['content'].lower() or "proceed" in res['content'].lower():
        print("\n[Turn 4] USER: No, wait.")
        res = process_message(thread_id, "No, wait.")
        print(f"AI: {res['content']}")
        print(f"Next Action Should be Question. Content: {res['content']}")
        
        # Immediate next turn should NOT ask confirmation even if score is high
        print("\n[Turn 5] USER: I also forgot to mention he threatened me.")
        res = process_message(thread_id, "I also forgot to mention he threatened me.")
        print(f"AI: {res['content']}")
        
        if "continue" in res['content'].lower():
            print("FAIL: AI asked confirmation too soon after rejection.")
        else:
            print("PASS: AI respected cooldown.")

if __name__ == "__main__":
    test_stabilization()
