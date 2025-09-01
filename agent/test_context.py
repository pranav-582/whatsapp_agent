from intent_router import IntentRouter

def test_context_memory():
    router = IntentRouter()
    phone_no = "+1234567890"
    whatsapp_name = "Test User"
    
    print("=== Context Memory Test ===")
    print("Type 'quit' to exit\n")
    
    message_count = 1
    while True:
        user_input = input(f"Message {message_count}: ")
        
        if user_input.lower() == 'quit':
            break
            
        result = router.process_user_message(
            phone_no=phone_no,
            user_message=user_input,
            whatsapp_name=whatsapp_name
        )
        
        print(f"Response: {result['agent_response']}\n")
        message_count += 1

if __name__ == "__main__":
    test_context_memory()
