from graph import process_message
import uuid
import time
import json

def test_repetitive_questioning():
    thread_id = str(uuid.uuid4())
    print(f"Starting test conversation thread: {thread_id}")

    # 1. Turn 1: Partial Issue
    print("\n[Turn 1] USER: My landlord Suresh owes me 50,000 rupees deposit.")
    res = process_message(thread_id, "My landlord Suresh owes me 50,000 rupees.")
    print(f"AI: {res['content']}")
    
    # 2. Turn 2: Provide Date (Simulate answering a question)
    print("\n[Turn 2] USER: It happened on Jan 1st 2024.")
    res = process_message(thread_id, "It happened on Jan 1st 2024.")
    print(f"AI: {res['content']}")
    
    # 3. Turn 3: Provide Location (Check if it re-asks date)
    print("\n[Turn 3] USER: The flat is in Chennai.")
    res = process_message(thread_id, "The flat is in Chennai.")
    print(f"AI: {res['content']}")
    
    # Verify internal state logic
    print("Entities captured:", res['entities'])
    
    if "date" in res['content'].lower() or "when" in res['content'].lower():
        print("FAIL: AI re-asked about date/time which was already provided.")
    else:
        print("PASS: AI did not re-ask about date.")

    # 4. Turn 4: Trigger confirmation & Reject
    print("\n[Turn 4] USER: I have the rental agreement.")
    # Assuming this triggers confirmation potentially or gets close.
    # Force rejection if confirmation asked, else just continue.
    res = process_message(thread_id, "I have the rental agreement.")
    print(f"AI: {res['content']}")
    
    if "continu" in res['content'].lower() or "proceed" in res['content'].lower():
        print("\n[Turn 5] USER: No, wait.")
        res = process_message(thread_id, "No, wait.")
        print(f"AI: {res['content']}")
        
        # Turn 6: Provide redundant info. Score should NOT increase.
        print("\n[Turn 6] USER: Yes, the agreement is with me.")
        res = process_message(thread_id, "Yes, the agreement is with me.")
        print(f"AI: {res['content']}")
        print(f"Score: {res['readiness_score']}")
        
        if "continu" in res['content'].lower():
             print("FAIL: Re-asked confirmation too soon.")
        else:
             print("PASS: Confirmation delayed.")

if __name__ == "__main__":
    test_repetitive_questioning()
