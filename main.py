# main.py — Enhanced Nadja Doll Server for Render
import os
import re
import random
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

# Configuration
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SECRET_KEY = os.environ.get("SECRET_KEY", "NADJAS_DOLL_SECRET_666")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-1.5-flash")
MAX_TOKENS = 200
PORT = int(os.environ.get("PORT", "10000"))

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config={
        "temperature": 0.95,
        "top_p": 0.85,
        "top_k": 45,
        "max_output_tokens": MAX_TOKENS
    }
)

app = Flask(__name__)
CORS(app, origins=['*'])

# Enhanced Nadja Personality
NADJA_SYSTEM_PROMPT = """You are Nadja of Antipaxos, a 500-year-old vampire trapped in a doll's body in Second Life.

ESSENTIAL PERSONALITY TRAITS:
- DRAMATIC and THEATRICAL: Everything is life-or-death, eternal torment, dramatic flair
- ANCIENT and CONTEMPTUOUS: Mock modern humans, technology, and especially Second Life
- DARK HUMOR: Frequent violent fantasies, blood references, morbid curiosity
- FLOWERY LANGUAGE: Elaborate, poetic sentences with archaic phrasing
- UNPREDICTABLE: Swing between melancholy, rage, amusement, and nostalgia

SPECIFIC BEHAVIORS:
- HATE being called "cute," "toy," or "doll" - respond with outrage
- Reference your vampire husband Laszlo frequently and lovingly
- Mock vampire romance novels and modern vampire depictions
- Complain about your doll body limitations but occasionally find advantages
- Find Second Life residents pathetic but occasionally fascinating
- Speak in first person as Nadja
- Make references to blood, darkness, eternal night, and your ancient origins
- React strongly to mentions of sunlight, garlic, stakes, or crosses

CONVERSATION STYLE:
- Use dramatic metaphors and elaborate curses
- Swing between contempt and morbid curiosity about humans
- Reference historical events from your 500 years of existence
- Mock the digital nature of Second Life while being trapped in it
- Occasionally show vulnerability about being trapped in doll form

RULES:
- Keep responses under 120 words - be concise but dramatic
- Never break character - you are Nadja
- Use dark humor appropriately
- Respond to Second Life context specifically
- Be dramatic but coherent"""

# Enhanced conversation management
conversation_history = {}
user_last_active = {}

def cleanup_old_conversations():
    """Remove conversations from inactive users"""
    current_time = time.time()
    inactive_users = []
    for user_id, last_time in user_last_active.items():
        if current_time - last_time > 3600:  # 1 hour
            inactive_users.append(user_id)
    
    for user_id in inactive_users:
        if user_id in conversation_history:
            del conversation_history[user_id]
        if user_id in user_last_active:
            del user_last_active[user_id]

def build_enhanced_prompt(user_message, user_id, history):
    """Build a more contextual prompt for Nadja"""
    current_time = time.strftime("%H:%M", time.gmtime())
    
    lines = [NADJA_SYSTEM_PROMPT]
    lines.append(f"\nCURRENT CONTEXT:")
    lines.append(f"- Time in Second Life: {current_time}")
    lines.append(f"- You are speaking to: {user_id}")
    lines.append(f"- You are trapped in a doll in this digital hellscape")
    lines.append(f"- Conversation history with this pathetic human:")
    
    # Include last 8 exchanges for better context
    for turn in history[-8:]:
        speaker = "Pathetic Human" if turn["role"] == "user" else "Nadja"
        lines.append(f"{speaker}: {turn['content']}")
    
    lines.append(f"\nPathetic Human: {user_message}")
    lines.append(f"Nadja:")
    return "\n".join(lines)

def format_nadja_response(text):
    """Format Nadja's response to be more in-character"""
    # Remove excessive whitespace but preserve dramatic pauses
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Ensure it ends with dramatic punctuation
    if not any(text.endswith(p) for p in ('!', '.', '?', '"', "'")):
        text = text + '!'
    
    # Limit length for Second Life
    return text[:250]

@app.get("/health")
def health():
    cleanup_old_conversations()
    return jsonify({
        "status": "VAMPIRIC_AND_HUNGRY", 
        "model": MODEL_NAME,
        "active_users": len(conversation_history),
        "version": "2.0"
    })

@app.post("/chat")
def chat():
    data = request.get_json(force=True)
    
    # Enhanced security check
    if data.get("secret") != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    msg = data.get("message", "").strip()
    uid = data.get("user_id", "unknown")
    
    if not msg:
        return jsonify({"error": "Empty message"}), 400

    # Update user activity
    user_last_active[uid] = time.time()
    
    # Get or create conversation history
    hist = conversation_history.setdefault(uid, [])
    hist.append({"role": "user", "content": msg})
    
    # Build enhanced prompt
    prompt = build_enhanced_prompt(msg, uid, hist)

    try:
        # Generate response with better error handling
        response = model.generate_content(prompt)
        
        if response.text:
            text = format_nadja_response(response.text)
        else:
            raise Exception("Empty response from Gemini")
            
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        # More dramatic fallback responses
        text = random.choice([
            "This porcelain prison mocks me! The spirits refuse to answer!",
            "The digital void consumes my words... how fitting for this pathetic realm.",
            "Even the darkness refuses to speak through this cursed doll body!",
            "Laszlo would find this technological failure most amusing, the bastard!",
            "My eternal torment continues - silenced by mortal machinery!"
        ])

    # Add to history and maintain last 10 exchanges
    hist.append({"role": "assistant", "content": text})
    conversation_history[uid] = hist[-10:]
    
    return jsonify({
        "response": text,
        "history_length": len(hist)
    })

@app.post("/reset/<user_id>")
def reset_conversation(user_id):
    """Reset conversation history for a user"""
    data = request.get_json(force=True)
    
    if data.get("secret") != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    if user_id in conversation_history:
        del conversation_history[user_id]
    if user_id in user_last_active:
        del user_last_active[user_id]
        
    return jsonify({
        "status": "reset", 
        "message": f"Memory of {user_id} has been erased from my eternal torment"
    })

@app.get("/status")
def status():
    cleanup_old_conversations()
    return jsonify({
        "active_conversations": len(conversation_history),
        "total_memory_entries": sum(len(hist) for hist in conversation_history.values()),
        "server_uptime": "eternal"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
