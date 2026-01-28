from graph import process_message
import uuid

def test_flow():
    thread_id = str(uuid.uuid4())
    print(f"Starting test conversation thread: {thread_id}")

    # 1. User reports an issue
    print("\nUSER: My landlord is not returning my deposit.")
    res = process_message(thread_id, "My landlord is not returning my deposit.")
    print(f"AI: {res['content']}")
    print(f"Entities: {res['entities']}")
    print(f"Score: {res['readiness_score']}")

    # 2. Provide some details
    print("\nUSER: It is 50,000 rupees and he is from Chennai.")
    res = process_message(thread_id, "It is 50,000 rupees and he is from Chennai.")
    print(f"AI: {res['content']}")
    print(f"Entities: {res['entities']}")
    print(f"Score: {res['readiness_score']}")
    
    # 3. Try providing something already known to see if it repeats
    print("\nUSER: The amount is fifty thousand.")
    res = process_message(thread_id, "The amount is fifty thousand.")
    print(f"AI: {res['content']}")
    
    # 4. Provide all details (Simulate completion)
    print("\nUSER: The incident happened last month. I have a rental agreement. The landlord's name is Suresh.")
    res = process_message(thread_id, "The incident happened last month. I have a rental agreement. The landlord's name is Suresh.")
    print(f"AI: {res['content']}")
    print(f"Score: {res['readiness_score']}")
    
    # If score is high, it should ask for confirmation
    if res['readiness_score'] >= 80:
        print("\n(Triggering Confirmation Logic)")
        # 5. Confirm
        print("\nUSER: Yes, go ahead.")
        res = process_message(thread_id, "Yes, please proceed.")
        print(f"AI: {res['content']}")
        print(f"Is Document: {res['is_document']}")

if __name__ == "__main__":
    test_flow()
