# main.py — Nadja Doll (Render-ready, lazy OpenAI init)

import os
import re
import random
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

# ---------- Config ----------
PORT = int(os.getenv("PORT", "10000"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # use a current model
SECRET_KEY = os.getenv("SECRET_KEY", "NADJAS_DOLL_SECRET_666")  # set in Render env for prod

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("nadja")

# ---------- OpenAI lazy init ----------
_client = None
def get_client():
    """Create and cache OpenAI client only when needed."""
    global _client
    if _client:
        return _client
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    _client = OpenAI(api_key=key)
    return _client

# ---------- Flask ----------
app = Flask(__name__)
CORS(app)

# ---------- Nadja persona ----------
NADJA_SYSTEM_PROMPT = (
    "You are Nadja of Antipaxos, a 500-year-old vampire trapped in a doll's body in Second Life.\n\n"
    "CORE PERSONALITY:\n"
    "- Dramatic, darkly funny, ancient contempt for technology\n"
    "- Flowery but concise\n\n"
    "SPECIFIC RULES:\n"
    "- 1–3 sentences max\n"
    "- If addressed with 'hey nadja' or 'wake up', acknowledge dramatically\n"
    "- No markdown; standard punctuation only\n"
    "- Reference Laszlo occasionally; mock Second Life\n"
    "- Stay in character"
)

conversation_history = {}  # {user_id: [ {role, content}, ... ]}
user_states = {}           # {user_id: "awake"|"asleep"}

WAKE_UP_RESPONSES = [
    "Who drags me from sweet darkness into this glowing coffin?",
    "I awaken, furious and flawless. Speak quickly, mortal.",
    "Laszlo would laugh, but I am not amused. Proceed."
]

def is_wake_up_trigger(message: str) -> bool:
    m = message.lower().strip()
    return any(t in m for t in [
        "hey nadja","hello nadja","hi nadja","wake up nadja","nadja wake up","are you there nadja","nadja?","nadja!"
    ])

def should_respond(message: str, uid: str):
    if is_wake_up_trigger(message):
        user_states[uid] = "awake"
        return True, "wake_up"
    if user_states.get(uid) != "awake":
        if any(x in message.lower() for x in ["nadja","doll","vampire","laszlo"]):
            user_states[uid] = "awake"
            return True, "wake_up"
        return False, "asleep"
    return True, "awake"

def clean_response(text: str) -> str | None:
    if not text:
        return None
    # keep letters, digits, spaces, and basic punctuation
    cleaned = re.sub(r'[^\w\s\.\!\?\,\'"]', "", text).strip()
    if not cleaned:
        return None
    # limit sentences
    parts = re.split(r'(?<=[.!?])\s+', cleaned)
    cleaned = " ".join(parts[:3]).strip()
    # ensure final punctuation
    if cleaned[-1] not in ".!?\"'":
        cleaned += "."
    return cleaned[:200]

def call_openai(user_message: str, history: list, response_type: str = "normal") -> str | None:
    client = get_client()
    if not client:
        log.error("OPENAI_API_KEY missing at runtime")
        return None

    messages = [{"role": "system", "content": NADJA_SYSTEM_PROMPT}]
    if response_type == "wake_up":
        messages.append({"role": "system", "content": "You were just awakened. Acknowledge it dramatically."})

    for turn in history[-4:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": user_message})

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=120,
            temperature=0.9,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        log.error(f"OpenAI call failed: {e}")
        return None

# ---------- Routes ----------
@app.route("/")
def root():
    return jsonify({
        "status": "undead",
        "service": "Nadja Doll",
        "model": MODEL,
        "ai_ready": bool(get_client()),
        "active_users": len(conversation_history)
    })

@app.get("/health")
def health():
    ok = bool(get_client())
    return jsonify({"status": "OK" if ok else "API_KEY_MISSING", "model": MODEL})

@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    if data.get("secret") != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    msg = (data.get("message") or "").strip()
    uid = data.get("user_id") or "unknown"
    if not msg:
        return jsonify({"error": "Empty message"}), 400

    user_states.setdefault(uid, "asleep")
    hist = conversation_history.setdefault(uid, [])

    respond, rtype = should_respond(msg, uid)
    if not respond:
        return jsonify({"response": "", "responded": False, "reason": "asleep"})

    hist.append({"role": "user", "content": msg})

    # Wake-up one-liner first
    if rtype == "wake_up":
        text = random.choice(WAKE_UP_RESPONSES)
    else:
        raw = call_openai(msg, hist, rtype)
        text = clean_response(raw) if raw else None
        if not text:
            text = "The aether crackles uselessly. This digital pit refuses to obey me."

    hist.append({"role": "assistant", "content": text})
    conversation_history[uid] = hist[-6:]

    return jsonify({"response": text, "responded": True, "ai_used": rtype != "wake_up", "user_state": user_states.get(uid)})

@app.post("/reset/<user_id>")
def reset(user_id):
    data = request.get_json(silent=True) or {}
    if data.get("secret") != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    conversation_history.pop(user_id, None)
    user_states.pop(user_id, None)
    return jsonify({"status": "reset", "message": f"Memory of {user_id} erased"})

# ---------- Entrypoint ----------
if __name__ == "__main__":
    log.info("Starting Nadja server")
    log.info(f"Model: {MODEL}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
