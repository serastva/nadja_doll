# main.py — Fixed Nadja Doll Server
import os
import re
import random
import time
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY", "NADJAS_DOLL_SECRET_666")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-1.5-flash")
MAX_TOKENS = 200
PORT = int(os.environ.get("PORT", "10000"))

# Validate API key
if not GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY environment variable is not set!")
    # Don't exit, but we'll handle this in the chat endpoint

# Initialize Gemini only if API key is available
if GEMINI_API_KEY:
    try:
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
        logger.info("✅ Gemini AI configured successfully")
    except Exception as e:
        logger.error(f"❌ Failed to configure Gemini: {e}")
        model = None
else:
    model = None
    logger.warning("⚠️ Gemini model not available - API key missing")

app = Flask(__name__)
CORS(app)

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

RULES:
- Keep responses under 120 words - be concise but dramatic
- Never break character - you are Nadja
- Use dark humor appropriately
- Respond to Second Life context specifically
- Be dramatic but coherent"""

# Conversation management
conversation_history = {}

def build_prompt(user_message, history):
    """Build conversation prompt"""
    lines = [NADJA_SYSTEM_PROMPT]
    lines.append("\nRECENT CONVERSATION:")
    
    # Include last 6 exchanges
    for turn in history[-6:]:
        speaker = "Human" if turn["role"] == "user" else "Nadja"
        lines.append(f"{speaker}: {turn['content']}")
    
    lines.append(f"\nHuman: {user_message}")
    lines.append("Nadja:")
    return "\n".join(lines)

def format_response(text):
    """Format Nadja's response"""
    if not text:
        return "The void whispers nothing back..."
    
    text = re.sub(r'\s+', ' ', text.strip())
    return text[:250]

@app.route('/')
def home():
    return jsonify({
        "status": "alive", 
        "service": "Nadja Doll API",
        "version": "2.1",
        "gemini_configured": GEMINI_API_KEY is not None
    })

@app.get("/health")
def health():
    return jsonify({
        "status": "VAMPIRIC", 
        "model": MODEL_NAME,
        "active_users": len(conversation_history),
        "gemini_ready": model is not None
    })

@app.post("/chat")
def chat():
    try:
        data = request.get_json(force=True)
        logger.info(f"📨 Received chat request: {data}")
        
        # Security check
        if data.get("secret") != SECRET_KEY:
            logger.warning("❌ Unauthorized request - secret mismatch")
            return jsonify({"error": "Unauthorized"}), 401

        msg = data.get("message", "").strip()
        uid = data.get("user_id", "unknown")
        
        if not msg:
            return jsonify({"error": "Empty message"}), 400

        # Check if Gemini is available
        if not model:
            logger.error("❌ Gemini model not available")
            return jsonify({
                "response": "The ancient magic fails me... my connection to the darkness is severed!",
                "error": "Gemini API not configured"
            }), 500

        # Manage conversation history
        hist = conversation_history.setdefault(uid, [])
        hist.append({"role": "user", "content": msg})
        
        # Build prompt and get response
        prompt = build_prompt(msg, hist)
        logger.info(f"🎭 Sending prompt to Gemini (length: {len(prompt)})")
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            text = format_response(response.text)
            logger.info(f"🗣️ Nadja responds: {text}")
        else:
            raise Exception("Empty response from Gemini")
            
    except Exception as e:
        logger.error(f"💥 Error in chat endpoint: {str(e)}")
        text = random.choice([
            "This porcelain prison mocks me! The spirits refuse to answer!",
            "The digital void consumes my words... how fitting for this pathetic realm.",
            "Even the darkness refuses to speak through this cursed doll body!",
            "Laszlo would find this technological failure most amusing, the bastard!",
            "My eternal torment continues - silenced by mortal machinery!"
        ])

    # Add to history
    if 'hist' in locals():
        hist.append({"role": "assistant", "content": text})
        conversation_history[uid] = hist[-10:]  # Keep last 10 exchanges
    
    return jsonify({
        "response": text,
        "history_length": len(hist) if 'hist' in locals() else 0
    })

@app.post("/reset/<user_id>")
def reset_conversation(user_id):
    data = request.get_json(force=True)
    
    if data.get("secret") != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    if user_id in conversation_history:
        del conversation_history[user_id]
        
    return jsonify({
        "status": "reset", 
        "message": f"Memory of {user_id} has been erased"
    })

if __name__ == "__main__":
    logger.info(f"🚀 Starting Nadja Doll server on port {PORT}")
    logger.info(f"🔑 Gemini configured: {GEMINI_API_KEY is not None}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
