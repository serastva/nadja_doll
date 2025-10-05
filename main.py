# main.py — Crash-Proof Nadja Doll Server
import os
import re
import random
import time
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY", "NADJAS_DOLL_SECRET_666")
PORT = int(os.environ.get("PORT", "10000"))

# Initialize Gemini only if API key is available
model = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.95,
                "top_p": 0.85,
                "top_k": 45,
                "max_output_tokens": 200
            }
        )
        logger.info("✅ Gemini AI configured successfully")
    except Exception as e:
        logger.error(f"❌ Failed to configure Gemini: {e}")
        model = None
else:
    logger.error("❌ GEMINI_API_KEY environment variable is not set!")

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
        "version": "2.2-crashproof",
        "gemini_configured": model is not None,
        "gemini_api_key_set": GEMINI_API_KEY is not None
    })

@app.get("/health")
def health():
    return jsonify({
        "status": "VAMPIRIC", 
        "gemini_ready": model is not None,
        "active_users": len(conversation_history),
        "server_time": time.time()
    })

@app.post("/chat")
def chat():
    try:
        # Parse request data safely
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        logger.info(f"📨 Received chat request from user")
        
        # Security check
        if data.get("secret") != SECRET_KEY:
            logger.warning("❌ Unauthorized request - secret mismatch")
            return jsonify({"error": "Unauthorized"}), 401

        msg = data.get("message", "").strip()
        uid = data.get("user_id", "unknown")
        
        if not msg:
            return jsonify({"error": "Empty message"}), 400

        # Manage conversation history
        hist = conversation_history.setdefault(uid, [])
        hist.append({"role": "user", "content": msg})
        
        # Check if Gemini is available
        if not model:
            logger.error("Gemini model not available - using fallback response")
            fallback_responses = [
                "The ancient magic fails me! My connection to the darkness is severed!",
                "This technological curse silences my eternal voice!",
                "Laszlo would mock this mortal machinery failing to channel my essence!",
                "The digital void consumes my words before they can take form!",
                "Even as a doll, I deserve better than this broken technology!"
            ]
            text = random.choice(fallback_responses)
        else:
            # Build prompt and get response
            prompt = build_prompt(msg, hist)
            logger.info(f"🎭 Sending prompt to Gemini ({len(prompt)} chars)")
            
            try:
                response = model.generate_content(prompt)
                
                if response and response.text:
                    text = format_response(response.text)
                    logger.info(f"🗣️ Nadja responds: {text}")
                else:
                    raise Exception("Empty response from Gemini")
                    
            except Exception as e:
                logger.error(f"💥 Gemini API error: {str(e)}")
                text = random.choice([
                    "The spirits mock me from beyond this digital veil!",
                    "This porcelain prison hums with static instead of dark magic!",
                    "Even the void refuses to speak through this cursed technology!",
                    "Laszlo would find this failure most amusing, the bastard!",
                    "My eternal torment continues - silenced by mortal machinery!"
                ])

        # Add to history and maintain last 8 exchanges
        hist.append({"role": "assistant", "content": text})
        conversation_history[uid] = hist[-8:]
        
        return jsonify({
            "response": text,
            "history_length": len(hist),
            "gemini_used": model is not None
        })
        
    except Exception as e:
        logger.error(f"💥 Critical error in chat endpoint: {str(e)}")
        return jsonify({
            "response": "The very fabric of this digital realm unravels!",
            "error": "Server error",
            "history_length": 0
        }), 500

@app.post("/reset/<user_id>")
def reset_conversation(user_id):
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        if data.get("secret") != SECRET_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        
        if user_id in conversation_history:
            del conversation_history[user_id]
            logger.info(f"Reset conversation history for user: {user_id}")
        
        return jsonify({
            "status": "reset", 
            "message": f"Memory of {user_id} has been erased from my eternal consciousness"
        })
        
    except Exception as e:
        logger.error(f"Error in reset endpoint: {str(e)}")
        return jsonify({"error": "Reset failed"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found", "available_endpoints": ["/chat", "/health", "/reset/<user_id>"]}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info(f"🚀 Starting Crash-Proof Nadja Doll server on port {PORT}")
    logger.info(f"🔑 Gemini configured: {model is not None}")
    logger.info(f"🔑 API Key present: {GEMINI_API_KEY is not None}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
