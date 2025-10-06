# main.py — Fixed with gemini-flash-latest
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

# Initialize Gemini
model = None
gemini_available = False
api_error = "Unknown"

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        logger.info("🔧 Configuring Gemini...")
        
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Try the specific model that should work
        model_name = "gemini-2.0-flash"  # This is in your available list
        
        try:
            model = genai.GenerativeModel(model_name=model_name)
            # Test it
            test_response = model.generate_content("Say 'TEST' only.")
            if test_response and test_response.text:
                logger.info(f"✅ Success with model: {model_name}")
                gemini_available = True
                api_error = "None"
            else:
                raise Exception("Test failed")
                
        except Exception as e:
            logger.error(f"❌ Model {model_name} failed: {e}")
            
            # Try fallback models
            fallback_models = [
                "gemini-2.0-flash-001",
                "gemini-2.0-flash-lite",
                "gemini-2.0-flash-lite-001", 
                "gemini-pro-latest"
            ]
            
            for fallback_model in fallback_models:
                try:
                    logger.info(f"🔄 Trying fallback: {fallback_model}")
                    model = genai.GenerativeModel(model_name=fallback_model)
                    test_response = model.generate_content("Test")
                    if test_response and test_response.text:
                        logger.info(f"✅ Success with fallback: {fallback_model}")
                        gemini_available = True
                        api_error = "None"
                        break
                except Exception as e2:
                    logger.info(f"❌ Fallback {fallback_model} failed: {str(e2)[:100]}")
                    continue
            
            if not gemini_available:
                raise Exception("All models failed")
            
    except Exception as e:
        logger.error(f"❌ Gemini configuration failed: {str(e)}")
        model = None
        gemini_available = False
        api_error = str(e)
else:
    logger.error("❌ GEMINI_API_KEY not set!")
    api_error = "API key not set"

app = Flask(__name__)
CORS(app)

# Nadja Personality
NADJA_SYSTEM_PROMPT = """You are Nadja of Antipaxos, a 500-year-old vampire trapped in a doll's body in Second Life. Be dramatic, darkly humorous, and contemptuous of modern technology. Reference your husband Laszlo frequently."""

conversation_history = {}

def build_prompt(user_message, history):
    lines = [NADJA_SYSTEM_PROMPT]
    for turn in history[-4:]:
        speaker = "Human" if turn["role"] == "user" else "Nadja"
        lines.append(f"{speaker}: {turn['content']}")
    lines.append(f"Human: {user_message}")
    lines.append("Nadja:")
    return "\n".join(lines)

@app.route('/')
def home():
    return jsonify({
        "status": "alive", 
        "gemini_available": gemini_available,
        "api_error": api_error
    })

@app.get("/health")
def health():
    return jsonify({
        "status": "VAMPIRIC", 
        "gemini_ready": gemini_available,
        "error": api_error
    })

@app.post("/chat")
def chat():
    try:
        data = request.get_json()
        if not data or data.get("secret") != SECRET_KEY:
            return jsonify({"error": "Unauthorized"}), 401

        msg = data.get("message", "").strip()
        uid = data.get("user_id", "unknown")
        
        if not msg:
            return jsonify({"error": "Empty message"}), 400

        hist = conversation_history.setdefault(uid, [])
        hist.append({"role": "user", "content": msg})
        
        response_text = ""
        gemini_used = False
        
        if gemini_available and model:
            try:
                prompt = build_prompt(msg, hist)
                response = model.generate_content(prompt)
                
                if response and response.text:
                    response_text = re.sub(r'\s+', ' ', response.text.strip())[:250]
                    gemini_used = True
                    logger.info(f"✅ Gemini response: {response_text}")
                else:
                    raise Exception("Empty response")
                    
            except Exception as e:
                logger.error(f"💥 Gemini error: {str(e)}")
                response_text = "The spirits mock this technological failure!"

        if not response_text:
            response_text = random.choice([
                "This porcelain prison silences my dark essence!",
                "Laszlo would laugh at this machinery failing!",
                "The digital void consumes my ancient words!",
            ])

        hist.append({"role": "assistant", "content": response_text})
        conversation_history[uid] = hist[-6:]
        
        return jsonify({
            "response": response_text,
            "gemini_used": gemini_used
        })
        
    except Exception as e:
        logger.error(f"💥 Chat error: {str(e)}")
        return jsonify({"response": "The realm unravels!"}), 500

if __name__ == "__main__":
    logger.info(f"🚀 Nadja Server - Gemini: {gemini_available}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
