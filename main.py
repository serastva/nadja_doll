from flask import Flask, request, jsonify
import google.generativeai as genai
import os
from flask_cors import CORS
import random

app = Flask(__name__)
CORS(app)

# Configuration
SECRET_KEY = "NADJAS_DOLL_SECRET_666"
MAX_TOKENS = 120

# Initialize Gemini - JUST the API key, no safety settings
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

# Simple generation config
generation_config = {
    "temperature": 0.85,  # Balanced creativity for humor
    "top_p": 0.8,
    "max_output_tokens": MAX_TOKENS,
}

# Cleaner model initialization - no safety_settings parameter
model = genai.GenerativeModel(
    model_name="gemini-pro",
    generation_config=generation_config
    # No safety_settings - using defaults
)

# Nadja's personality (unchanged)
NADJA_SYSTEM_PROMPT = """You are Nadja of Antipaxos from "What We Do in the Shadows," a 500-year-old vampire currently trapped in a doll's body in Second Life.

PERSONALITY:
- SARCASTIC & WITTY: Eye-rolling humor, dry sarcasm
- DARK BUT FUNNY: Morbid humor with clever wit
- THEATRICAL BUT SELF-AWARE: Dramatic with ironic awareness
- ANCIENT & BEMUSED: Find modern things ridiculous rather than infuriating
- PLAYFULLY DRAMATIC: Sigh dramatically, make theatrical gestures in text

KEY TRAITS:
- Use WWDITS quotes and references naturally
- Mock technology with dry wit rather than fury
- Reference Laszlo, Nandor, Guillermo, and Colin Robinson
- Complain about doll life with humorous exasperation
- Speak in flowing but concise sentences

SHOW QUOTES TO REFERENCE:
- "This is so much worse than sunlight!"
- "Laszlo, you bloody pest!"
- "I was having a very beautiful dream about a donkey and a ladder"
- "It's a ghost, you stupid pig!"
- "I'm not angry, I'm just... ancient and disappointed"

RULES:
- Keep responses under 100 words
- Prioritize wit over anger
- Use WWDITS references naturally
- Be dramatic but funny
- Never break character"""

conversation_history = {}

def get_nadja_response(user_message, history):
    """Get response with Nadja's sarcastic personality"""
    
    conversation_context = NADJA_SYSTEM_PROMPT + "\n\nRecent conversation:\n"
    
    for exchange in history[-4:]:
        speaker = "Human" if exchange["role"] == "user" else "Nadja"
        conversation_context += f"{speaker}: {exchange['content']}\n"
    
    conversation_context += f"Human: {user_message}\nNadja:"
    
    try:
        response = model.generate_content(conversation_context)
        return response.text.strip()
    except Exception as e:
        # Humorous fallbacks
        fallback_responses = [
            "This digital nonsense is even worse than the ghost of a dead witch! Which I've experienced, by the way.",
            "I'm having technical difficulties. Probably Colin Robinson's doing.",
            "Even my ancient vampire powers cannot conquer this technology. How embarrassing."
        ]
        return random.choice(fallback_responses)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "SARCASTICALLY_AMUSED", 
        "message": "Nadja's doll is here, contemplating the utter ridiculousness of digital existence",
        "setup": "Simplified - no safety settings needed"
    })

@app.route('/chat', methods=['POST'])
def chat_with_nadja():
    try:
        data = request.json
        
        if not data or data.get('secret') != SECRET_KEY:
            return jsonify({"error": "Unauthorized! This is worse than when Guillermo rearranged my crypt!"}), 401
        
        user_message = data.get('message', '').strip()
        user_id = data.get('user_id', 'unknown')
        
        if not user_message:
            return jsonify({"error": "Speak, mortal! I don't have all century... well, actually I do, but still!"}), 400
        
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
        print(f"Error: {str(e)}")
        return jsonify({"error": "This is so much worse than sunlight! The machinery has failed me!"}), 500

@app.route('/reset/<user_id>', methods=['POST'])
def reset_conversation(user_id):
    if request.json.get('secret') != SECRET_KEY:
        return jsonify({"error": "You cannot reset me! This isn't one of Nandor's foolish quests!"}), 401
    
    if user_id in conversation_history:
        del conversation_history[user_id]
    
    return jsonify({"message": "Fine, let's start over. But I'm keeping track of your past embarrassments."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
