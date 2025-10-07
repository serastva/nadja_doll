from flask import Flask, request, jsonify
from openai import OpenAI
import os
from flask_cors import CORS
import random

app = Flask(__name__)
CORS(app)

# Configuration
SECRET_KEY = "NADJAS_DOLL_SECRET_666"

# Initialize OpenAI client
try:
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is missing")
    
    client = OpenAI(api_key=api_key)
    print("OpenAI client initialized successfully")
except Exception as e:
    print(f"OpenAI initialization error: {e}")
    client = None

# Nadja prompt
NADJA_SYSTEM_PROMPT = """You are Nadja of Antipaxos from "What We Do in the Shadows." You are a 500-year-old vampire trapped in a doll body in Second Life.

CRITICAL RULES:
- Be EXTREMELY CONCISE: 1-2 sentences MAXIMUM
- Use dry sarcasm and dark humor
- Reference WWDITS characters naturally
- Never break character
- Responses under 20 words when possible

PERSONALITY:
- Sarcastic, witty, dramatically bored
- Ancient but amused by modern nonsense
- Mock technology with bemused contempt"""

conversation_history = {}

def get_nadja_response(user_message, history):
    if not client:
        return "API configuration error. The spirits are confused."
    
    messages = [{"role": "system", "content": NADJA_SYSTEM_PROMPT}]
    
    for exchange in history[-4:]:
        messages.append(exchange)
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # UPDATED: Current model
            messages=messages,
            max_tokens=50,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        fallbacks = [
            "The spirits are busy. Probably Colin Robinson's fault.",
            "Technical difficulties. How typically modern.",
            "Even my ancient powers struggle with this nonsense.",
        ]
        return random.choice(fallbacks)

@app.route('/health', methods=['GET'])
def health_check():
    status = "OK" if client else "API_KEY_MISSING"
    return jsonify({
        "status": status, 
        "message": "Nadja server health check",
        "model": "gpt-4o-mini"  # UPDATED
    })

@app.route('/chat', methods=['POST'])
def chat_with_nadja():
    try:
        data = request.json
        
        if not data or data.get('secret') != SECRET_KEY:
            return jsonify({"error": "Unauthorized! This is worse than Guillermo's organizing!"}), 401
        
        user_message = data.get('message', '').strip()
        user_id = data.get('user_id', 'unknown')
        
        if not user_message:
            return jsonify({"error": "Speak, mortal! My patience is ancient but limited."}), 400
        
        if user_id not in conversation_history:
            conversation_history[user_id] = []
        
        history = conversation_history[user_id]
        history.append({"role": "user", "content": user_message})
        
        if len(history) > 6:
            history = history[-6:]
        
        ai_response = get_nadja_response(user_message, history)
        
        history.append({"role": "assistant", "content": ai_response})
        conversation_history[user_id] = history
        
        return jsonify({"response": ai_response})
        
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({"error": "This technology is so much worse than sunlight!"}), 500

@app.route('/reset/<user_id>', methods=['POST'])
def reset_conversation(user_id):
    if request.json.get('secret') != SECRET_KEY:
        return jsonify({"error": "You cannot reset me! This isn't one of Nandor's quests!"}), 401
    
    if user_id in conversation_history:
        del conversation_history[user_id]
    
    return jsonify({"message": "Fine, clean slate. But I remember everything."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
