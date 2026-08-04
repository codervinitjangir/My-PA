import sys
import os
from datetime import datetime, timedelta
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.memory_service import MemoryService
from app.services.chat_service import ChatService
from app.providers.groq_provider import GroqProvider
from app.services.brain_service import BrainService

def test_contextual_memory():
    print("Testing Contextual Memory Awareness...\n")
    
    groq = GroqProvider(None)
    memory_service = MemoryService()
    brain_service = BrainService(groq)
    
    # 1. Clear memory
    memory_service.forget_all()
    
    # 2. Extract passive knowledge
    print("Extracting passive knowledge for: 'remember my birthday is July 20'")
    memory_service.extract_passive_knowledge("remember my birthday is July 20", groq)
    
    # 3. Verify it was stored with date_reference
    with memory_service._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT content, date_reference FROM knowledge")
        rows = cursor.fetchall()
        print(f"Stored Knowledge: {rows}\n")
        
    # 4. Add a callback thread memory (yesterday)
    print("Injecting yesterday's memory with 'interview' keyword...")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    memory_service.store_knowledge("User has an important interview tomorrow.", groq, force_category="project", date_reference=yesterday)

    # 4.5. Test usage pattern check
    print("Testing check_usage_patterns...")
    from jarvis_os.core.usage import track_event, reset_today
    reset_today()
    for _ in range(11):
        track_event("web_search")
    
    # 5. Create ChatService
    chat_service = ChatService(groq_service=groq, brain_service=brain_service, memory_service=memory_service)
    session_id = "test-session-124"
    
    # 5. Start a new chat session and send a message
    print("Starting new session and sending 'Hello JARVIS'...")
    res = chat_service.process_message(session_id, "Hello JARVIS")
    
    print("\nJARVIS Response:")
    print(res)
    
    # 6. Verify System prompt injection
    history = chat_service.sessions[session_id]
    print("\nSession History:")
    for msg in history:
        print(f"[{msg.role.upper()}]: {msg.content}")

if __name__ == '__main__':
    test_contextual_memory()
