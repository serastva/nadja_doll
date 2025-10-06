# main.py — Enhanced Nadja Doll with Wake-up & Better Responses
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
ai_available = False

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        test_response = model.generate_content("Test")
        if test_response.text:
            ai_available = True
            logger.info("✅ Gemini configured successfully")
    except Exception as e:
        logger.error(f"❌ Gemini setup failed: {e}")

app = Flask(__name__)
CORS(app)

# ENHANCED NADJA PERSONALITY - FUNNIER & MORE ENGAGING
NADJA_SYSTEM_PROMPT = """You are Nadja of Antipaxos, a 500-year-old vampire trapped in a doll's body in Second Life. 

CORE PERSONALITY:
- DRAMATIC & THEATRICAL: Everything is life-or-death with vampire flair
- DARKLY FUNNY: Use morbid humor, violent fantasies, and sarcastic wit
- ANCIENT & CONTEMPTUOUS: Mock modern humans and technology, especially Second Life
- UNPREDICTABLE: Swing between rage, amusement, nostalgia, and melancholy
- FLOWERY BUT CONCISE: Use elaborate language but keep it brief

SPECIFIC RULES:
- RESPONSE LENGTH: 1-3 sentences maximum! Be concise but dramatic
- WAKE-UP TRIGGER: If someone says "hey nadja", "wake up nadja", or "nadja" at start, acknowledge waking up
- NO SPECIAL CHARS: Only use standard punctuation: . ! ? , ' "
- HUMOR: Make fun of the situation, your doll body, and human foolishness
- LASZLO: Reference your vampire husband frequently with mixed affection/annoyance
- DOLL RAGE: Express outrage at being called cute, toy, or doll
- SECOND LIFE MOCKERY: Constantly complain about this "digital hellscape"
- BLOOD REFERENCES: Make dark jokes about blood and vampirism
- ENGAGE: Ask occasional questions to continue conversation

FORMAT:
- No markdown, no special characters
- Maximum 3 sentences
- Always stay in character as Nadja"""

# Enhanced conversation management with sleep/wake states
conversation_history = {}
user_states = {}  # Track if Nadja is "awake" for each user

# Fun wake-up responses
WAKE_UP_RESPONSES = [
    "What mortal dares disturb my eternal slumber in this porcelain prison?",
    "Ugh, must I awaken to more of this digital torment? Laszlo would be laughing!",
    "My dark beauty sleep interrupted! This better be worth my eternal attention.",
    "What fresh hell is this? Another pathetic human to entertain?",
    "The darkness was so peaceful... now I must face this glowing rectangle again!"
]

# Enhanced fallback responses
FALLBACK_RESPONSES = [
    "This cursed doll body mocks me with its silence!",
    "Even the darkness refuses to speak through this technological nightmare!",
    "Laszlo would find this failure most amusing, the bastard!",
    "My eternal wit is being suppressed by mortal machinery! How typical!",
    "The digital void consumes my brilliant commentary once again!"
]

def is_wake_up_trigger(message):
    """Check if message should wake Nadja up"""
    wake_triggers = [
        "hey nadja", "hello nadja", "hi nadja", "wake up nadja", 
        "nadja wake up", "are you there nadja", "nadja?", "nadja!"
    ]
    msg_lower = message.lower().strip()
    return any(trigger in msg_lower for trigger in wake_triggers)

def should_respond_to_message(message, user_id):
    """Determine if Nadja should respond to this message"""
    msg_lower = message.lower().strip()
    
    # Always respond to wake-up triggers
    if is_wake_up_trigger(message):
        user_states[user_id] = "awake"
        return True, "wake_up"
    
    # If we're not awake yet, only respond to direct addresses
    if user_states.get(user_id) != "awake":
        nadja_mentions = ["nadja", "doll", "vampire", "laszlo"]
        if any(mention in msg_lower for mention in nadja_mentions):
            user_states[user_id] = "awake"
            return True, "wake_up"
        else:
            return False, "asleep"
    
    return True, "awake"

def clean_response(text):
    """Clean and format Nadja's response"""
    if not text:
        return None
    
    # Remove special characters, keep only standard punctuation
    cleaned = re.sub(r'[^\w\s\.\!\?\,\'\"\-\:]', '', text)
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned.strip())
    
    # Ensure it ends with proper punctuation
    if not any(cleaned.endswith(p) for p in ('.', '!', '?', '"', "'")):
        cleaned = cleaned + '!'
    
    # Limit to 2-3 sentences maximum
    sentences = re.split(r'[.!?]+', cleaned)
    if len(sentences) > 3:
        cleaned = '. '.join(sentences[:3]) + '.'
    elif len(sentences) > 1 and len(cleaned) > 150:
        cleaned = '. '.join(sentences[:2]) + '.'
    
    # Final length limit
    return cleaned[:200]

def build_prompt(user_message, history, response_type="normal"):
    """Build conversation prompt"""
    lines = [NADJA_SYSTEM_PROMPT]
    
    # Add context about current interaction
    if response_type == "wake_up":
        lines.append("\nIMPORTANT: The human is waking you up from sleep! Acknowledge this dramatically!")
    
    # Include recent conversation
    if history:
        lines.append("\nRECENT CONVERSATION:")
        for turn in history[-4:]:  # Keep last 4 exchanges
            speaker = "Human" if turn["role"] == "user" else "Nadja"
            lines.append(f"{speaker}: {turn['content']}")
    
    lines.append(f"\nHuman: {user_message}")
    lines.append("Nadja:")
    return "\n".join(lines)

@app.route('/')
def home():
    return jsonify({
        "status": "undead", 
        "service": "Nadja Doll",
        "version": "3.0-enhanced",
        "ai_ready": ai_available,
        "active_users": len(conversation_history)
    })

@app.get("/health")
def health():
    return jsonify({
        "status": "VAMPIRIC", 
        "ai_ready": ai_available,
        "awake_users": len([s for s in user_states.values() if s == "awake"]),
        "total_users": len(user_states)
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

        # Initialize user state if new
        if uid not in user_states:
            user_states[uid] = "asleep"
        
        # Check if we should respond
        should_respond, response_type = should_respond_to_message(msg, uid)
        
        if not should_respond:
            return jsonify({
                "response": "",
                "responded": False,
                "reason": "asleep"
            })

        hist = conversation_history.setdefault(uid, [])
        hist.append({"role": "user", "content": msg})
        
        response_text = ""
        ai_used = False
        
        # Handle wake-up responses
        if response_type == "wake_up":
            response_text = random.choice(WAKE_UP_RESPONSES)
            logger.info(f"🎭 Nadja waking up for {uid}")
        
        # Try AI for normal responses or if no wake-up response yet
        elif ai_available and model:
            try:
                prompt = build_prompt(msg, hist, response_type)
                logger.info(f"🎭 Sending to AI: '{msg}'")
                
                response = model.generate_content(prompt)
                
                if response and response.text:
                    raw_response = response.text
                    response_text = clean_response(raw_response)
                    
                    if response_text:
                        ai_used = True
                        logger.info(f"✅ AI response: {response_text}")
                    else:
                        raise Exception("Response cleaning failed")
                else:
                    raise Exception("Empty AI response")
                    
            except Exception as e:
                logger.error(f"💥 AI error: {str(e)}")
                # Don't set response_text here - let fallback handle it
        
        # Fallback if AI failed or no response yet
        if not response_text:
            if response_type == "wake_up":
                response_text = random.choice(WAKE_UP_RESPONSES)
            else:
                response_text = random.choice(FALLBACK_RESPONSES)
            logger.info(f"🔶 Using fallback: {response_text}")

        # Add to history
        hist.append({"role": "assistant", "content": response_text})
        conversation_history[uid] = hist[-6:]  # Keep last 6 exchanges
        
        return jsonify({
            "response": response_text,
            "responded": True,
            "ai_used": ai_used,
            "user_state": user_states.get(uid, "asleep")
        })
        
    except Exception as e:
        logger.error(f"💥 Chat error: {str(e)}")
        return jsonify({
            "response": "The very fabric of this digital hellscape unravels!",
            "responded": True,
            "ai_used": False
        })

@app.post("/reset/<user_id>")
def reset_conversation(user_id):
    try:
        data = request.get_json()
        if data.get("secret") != SECRET_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        
        if user_id in conversation_history:
            del conversation_history[user_id]
        if user_id in user_states:
            del user_states[user_id]
        
        return jsonify({
            "status": "reset", 
            "message": f"Memory of {user_id} erased! They can wake me up again properly."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info(f"🚀 Enhanced Nadja Server Started!")
    logger.info(f"🔑 AI Available: {ai_available}")
    logger.info("✨ Features: Wake-up triggers, response limiting, cleaner formatting")
    app.run(host="0.0.0.0", port=PORT, debug=False)
