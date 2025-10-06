# main.py — Fixed Model Name Nadja Doll Server
import os
import re
import random
import time
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY", "NADJAS_DOLL_SECRET_666")
PORT = int(os.environ.get("PORT", "10000"))

# Initialize Gemini with correct model names
model = None
gemini_available = False
api_error = "Unknown"

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        logger.info("🔧 Attempting to configure Gemini...")
        
        genai.configure(api_key=GEMINI_API_KEY)
        
        # List available models to see what's actually available
        try:
            models = genai.list_models()
            model_names = [m.name for m in models]
            logger.info(f"📋 Available models: {model_names}")
            
            # Find the correct model name
            supported_models = []
            for m in models:
                if 'generateContent' in m.supported_generation_methods:
                    supported_models.append(m.name)
                    logger.info(f"✅ Supported model: {m.name}")
            
            logger.info(f"🎯 Models supporting generateContent: {supported_models}")
            
        except Exception as e:
            logger.error(f"❌ Cannot list models: {e}")
            api_error = f"Cannot list models: {str(e)}"
            raise
        
        # Use the correct model name - try different options
        model_name = None
        
        # Try different possible model names
        possible_models = [
            "gemini-1.5-flash",  # Newer name
            "gemini-1.5-flash-001",  # Specific version
            "gemini-1.0-pro",    # Fallback option
            "gemini-pro",         # Alternative name
            "models/gemini-1.5-flash",  # Full path
            "models/gemini-pro"   # Full path fallback
        ]
        
        for test_model in possible_models:
            try:
                logger.info(f"🔧 Testing model: {test_model}")
                test_model_obj = genai.GenerativeModel(model_name=test_model)
                test_response = test_model_obj.generate_content("Say 'TEST' only.")
                if test_response and test_response.text:
                    model_name = test_model
                    logger.info(f"✅ Model works: {model_name}")
                    break
            except Exception as e:
                logger.info(f"❌ Model failed {test_model}: {str(e)[:100]}")
                continue
        
        if model_name:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config={
                    "temperature": 0.95,
                    "top_p": 0.85,
                    "top_k": 45,
                    "max_output_tokens": 200
                }
            )
            
            # Final test
            test_response = model.generate_content("Say 'NADJA READY' only.")
            if test_response and test_response.text:
                logger.info(f"🎉 Gemini configured successfully with model: {model_name}")
                gemini_available = True
                api_error = "None"
            else:
                raise Exception("Final test failed")
        else:
            raise Exception("No working model found")
            
    except Exception as e:
        logger.error(f"❌ Gemini configuration failed: {str(e)}")
        model = None
        gemini_available = False
        api_error = str(e)
else:
    logger.error("❌ GEMINI_API_KEY environment variable is not set!")
    api_error = "API key not set"

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
        "version": "2.4-model-fix",
        "gemini_available": gemini_available,
        "api_error": api_error,
        "gemini_api_key_set": GEMINI_API_KEY is not None
    })

@app.get("/health")
def health():
    return jsonify({
        "status": "VAMPIRIC", 
        "gemini_ready": gemini_available,
        "gemini_error": api_error,
        "active_users": len(conversation_history)
    })

@app.post("/chat")
def chat():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # Security check
        if data.get("secret") != SECRET_KEY:
            return jsonify({"error": "Unauthorized"}), 401

        msg = data.get("message", "").strip()
        uid = data.get("user_id", "unknown")
        
        if not msg:
            return jsonify({"error": "Empty message"}), 400

        # Manage conversation history
        hist = conversation_history.setdefault(uid, [])
        hist.append({"role": "user", "content": msg})
        
        response_text = ""
        gemini_used_successfully = False
        
        # Try to use Gemini if available
        if gemini_available and model:
            try:
                prompt = build_prompt(msg, hist)
                logger.info(f"🎭 Sending to Gemini: '{msg}'")
                
                response = model.generate_content(prompt)
                
                if response and response.text:
                    response_text = format_response(response.text)
                    gemini_used_successfully = True
                    logger.info(f"✅ Gemini success: {response_text}")
                else:
                    raise Exception("Empty response from Gemini")
                    
            except Exception as e:
                logger.error(f"💥 Gemini API call failed: {str(e)}")
                response_text = f"The spirits mock this technological failure! {str(e)[:30]}"
        
        # If Gemini failed or not available, use fallback
        if not response_text or not gemini_used_successfully:
            fallback_responses = [
                "This porcelain prison silences my dark essence!",
                "The digital void consumes my ancient words!",
                "Laszlo would laugh at this technological failure!",
                "Even as a doll, I deserve functioning magic!",
                "The mortal machinery fails to channel my eternal voice!"
            ]
            response_text = random.choice(fallback_responses)
            logger.warning(f"🔶 Using fallback: {response_text}")

        # Add to history
        hist.append({"role": "assistant", "content": response_text})
        conversation_history[uid] = hist[-6:]
        
        return jsonify({
            "response": response_text,
            "history_length": len(hist),
            "gemini_used": gemini_used_successfully,
            "gemini_available": gemini_available
        })
        
    except Exception as e:
        logger.error(f"💥 Critical error in chat: {str(e)}")
        return jsonify({
            "response": "The very fabric of this realm unravels!",
            "error": str(e)
        }), 500

@app.post("/reset/<user_id>")
def reset_conversation(user_id):
    try:
        data = request.get_json()
        if data.get("secret") != SECRET_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        
        if user_id in conversation_history:
            del conversation_history[user_id]
        
        return jsonify({"status": "reset"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("🚀 Starting Nadja Doll Server - Model Fix Version")
    logger.info(f"🔑 Gemini Available: {gemini_available}")
    logger.info(f"🔑 API Error: {api_error}")
    logger.info("=" * 50)
    app.run(host="0.0.0.0", port=PORT, debug=False)
