import redis
import json
import os
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

# Check what's actually stored
key = "chat_session:+1234567890"
data = redis_client.get(key)

if data:
    chat_history = json.loads(data)
    print(f"Total messages: {len(chat_history['messages'])}")
    for i, msg in enumerate(chat_history['messages'], 1):
        print(f"{i}. {msg['sender']}: {msg['message'][:50]}...")
else:
    print("No data found!")
