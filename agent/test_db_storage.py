import os
import redis
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functions import manage_session_chat_history, _cleanup_old_conversations, _save_chat_to_db
import psycopg2

load_dotenv()

def test_chat_to_db_storage():
    """Test if chats get moved from Redis to DB"""
    
    redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    test_phone = "+12345678909"
    
    print("=== Testing Chat to DB Storage ===\n")
    
    # 1. Create a test chat session
    print("1. Creating test chat session...")
    manage_session_chat_history(test_phone, "Hello, I want to buy something", "Great! What would you like?")
    manage_session_chat_history(test_phone, "Nike shoes please", "Sure! Which size?")
    manage_session_chat_history(test_phone, "Size 42", "Perfect! Order placed.")
    
    # 2. Check if it's in Redis
    redis_key = f"chat_session:{test_phone}"
    chat_data = redis_client.get(redis_key)
    if chat_data:
        chat_history = json.loads(chat_data)
        print(f"✅ Chat in Redis: {len(chat_history['messages'])} messages")
    else:
        print("❌ No chat found in Redis")
        return
    
    # 3. FORCE the chat to be old (modify timestamp)
    print("\n2. Making chat appear old (30+ minutes)...")
    old_time = (datetime.now() - timedelta(minutes=35)).isoformat()
    chat_history["started_at"] = old_time
    chat_history["last_activity"] = old_time
    
    # Update all message timestamps to be old
    for msg in chat_history["messages"]:
        msg["timestamp"] = old_time
    
    # Save the modified chat back to Redis
    redis_client.setex(redis_key, 1800, json.dumps(chat_history))
    print("✅ Chat timestamps modified to appear 35 minutes old")
    
    # 4. Check DB before cleanup
    print("\n3. Checking DB before cleanup...")
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM conversations WHERE phone_no = %s", (test_phone,))
    before_count = cursor.fetchone()[0]
    print(f"Conversations in DB before cleanup: {before_count}")
    
    # 5. Force cleanup
    print("\n4. Running cleanup (should move chat to DB)...")

    # Debug: Check what cleanup function sees
    redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    chat_keys = redis_client.keys("chat_session:*")
    print(f"   Found {len(chat_keys)} chat sessions in Redis")

    for key in chat_keys:
        chat_data = redis_client.get(key)
        if chat_data:
            chat_history = json.loads(chat_data)
            last_activity = datetime.fromisoformat(chat_history.get("last_activity", chat_history["started_at"]))
            age_minutes = (datetime.now() - last_activity).total_seconds() / 60
            print(f"   Key: {key.decode()}, Age: {age_minutes:.1f} minutes")

    # Now run cleanup
    _cleanup_old_conversations()
    
    # 6. Check Redis after cleanup
    print("\n5. Checking Redis after cleanup...")
    chat_data_after = redis_client.get(redis_key)
    if chat_data_after:
        print("❌ Chat still in Redis (cleanup failed)")
    else:
        print("✅ Chat removed from Redis")
    
    # 7. Check DB after cleanup
    print("\n6. Checking DB after cleanup...")
    cursor.execute("SELECT COUNT(*) FROM conversations WHERE phone_no = %s", (test_phone,))
    after_count = cursor.fetchone()[0]
    print(f"Conversations in DB after cleanup: {after_count}")
    
    if after_count > before_count:
        print("✅ Chat successfully moved to DB!")
        
        # Show the conversation details
        cursor.execute("""
            SELECT conversation_id, started_at, ended_at 
            FROM conversations 
            WHERE phone_no = %s 
            ORDER BY started_at DESC 
            LIMIT 1
        """, (test_phone,))
        
        conv = cursor.fetchone()
        if conv:
            print(f"   Conversation ID: {conv[0]}")
            print(f"   Started: {conv[1]}")
            print(f"   Ended: {conv[2]}")
            
            # Check messages
            cursor.execute("""
                SELECT sender, message_text 
                FROM messages 
                WHERE conversation_id = %s 
                ORDER BY timestamp
            """, (conv[0],))
            
            messages = cursor.fetchall()
            print(f"   Messages stored: {len(messages)}")
            for i, (sender, text) in enumerate(messages, 1):
                print(f"     {i}. {sender}: {text[:50]}...")
    else:
        print("❌ Chat was not moved to DB")
    
    # 8. Cleanup
    # print("\n7. Cleaning up test data...")
    # cursor.execute("DELETE FROM conversations WHERE phone_no = %s", (test_phone,))
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    test_chat_to_db_storage()  # pyright: ignore[reportUndefinedVariable]
