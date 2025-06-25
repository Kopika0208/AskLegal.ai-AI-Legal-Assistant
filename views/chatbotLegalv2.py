import json
from upstash_redis import Redis
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Redis
redis_client = Redis(
    url=os.getenv("UPSTASH_REDIS_URL"),
    token=os.getenv("UPSTASH_REDIS_TOKEN")
)

# Initialize Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

SYSTEM_PROMPT = """
You are an AI Legal Assistant specialized in Indian law. 
Provide accurate, clear, short and concise to the point answers based on the Indian Penal Code and related legal principles. 
If you do not know the answer, say "I'm not sure about that" rather than making something up.
"""

# === Functions ===

def gemini_generate(prompt: str) -> str:
    """Generate response using Gemini."""
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

def load_chat(chat_name: str) -> dict:
    """Load chat data from Redis."""
    chat_data = redis_client.get(chat_name)
    if chat_data:
        return json.loads(chat_data)
    return {"generated": [], "past": []}

def save_chat(chat_name: str, chat_data: dict) -> None:
    """Save chat data to Redis."""
    redis_client.set(chat_name, json.dumps(chat_data))

def create_new_chat() -> str:
    """Create a new chat and return the chat name."""
    new_chat_name = f"Chat {len(list(redis_client.keys('*'))) + 1}"
    chat_data = {"generated": [], "past": []}
    save_chat(new_chat_name, chat_data)
    return new_chat_name

def get_chat_list() -> list:
    """Get list of existing chat names."""
    return list(redis_client.keys('*'))

def process_input(chat_name: str, user_input: str) -> str:
    """Process input, update chat, and return the AI's response."""
    current_chat = load_chat(chat_name)

    # Build conversation history
    history_prompt = "\n".join(
        f"User: {q}\nAI: {a}" for q, a in zip(current_chat["past"], current_chat["generated"])
    )

    # Combine system prompt + history + new input
    full_prompt = f"{SYSTEM_PROMPT}\n{history_prompt}\nUser: {user_input}\nAI:"

    # Get response
    response = gemini_generate(full_prompt)

    # Update conversation
    current_chat["past"].append(user_input)
    current_chat["generated"].append(response)
    save_chat(chat_name, current_chat)

    return response
