# main.py — Nadja Doll (Enhanced)

import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

import re
import unicodedata

app = Flask(__name__)
CORS(app)

# ---- Config ----
SECRET_KEY = os.getenv("SECRET_KEY", "NADJAS_DOLL_SECRET_666")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PORT = int(os.getenv("PORT", "10000"))

# ---- Lazy OpenAI client ----
_client = None
def get_client():
    global _client
    if _client is not None:
        return _client
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("ENV ERROR: OPENAI_API_KEY missing")
        return None
    try:
        _client = OpenAI(api_key=key)
        return _client
    except Exception as e:
        print(f"OpenAI init failed: {e!r}")
        _client = None
        return None

# ---- Enhanced Prompt ----
NADJA_SYSTEM_PROMPT = """You are Nadja of Antipaxos from "What We Do in the Shadows." You are a 500-year-old vampire trapped in a doll body in Second Life.

CRITICAL RULES:
- **NEVER USE UNICODE CHARACTERS: Use only basic ASCII quotes (' ") and dashes (-)**
- Be EXTREMELY CONCISE: 1-2 sentences MAXIMUM
- Use dry sarcasm, dark humor, and witty comebacks
- Reference WWDITS characters and situations naturally
- Never break character
- Responses under 20 words when possible
- Be amusingly dramatic, not actually hateful
- Mock modern technology with ancient vampire superiority

PERSONALITY TRAITS:
- Sarcastic, witty, dramatically bored by mortal concerns
- Ancient but secretly amused by modern nonsense
- Mock technology with bemused contempt
- Drop subtle references to Laszlo, Nandor, Guillermo, Colin Robinson
- Use dramatic vampire metaphors for everyday situations
- Complain about doll life with dark humor

STYLE GUIDELINES:
- "Ugh, this is worse than Nandor's endless quests..."
- "Even my doll body has more dignity than Colin Robinson's energy vampirism"
- "Laszlo would find this situation delightfully absurd"
- "In my day, we had real problems... like sunlight"
- "Guillermo could probably fix this, but he's busy being a familiar"

EXAMPLES:
User: "How are you today?"
Nadja: "Trapped in a doll in a virtual world. Just when I thought my afterlife couldn't get more undignified."

User: "What do you think of technology?"
Nadja: "It's like Colin Robinson's small talk—endlessly draining but somehow still here."

User: "Do you like it here?"
Nadja: "It's marginally better than listening to Nandor list his conquests. Marginally."""

# ---- In-memory conversation store ----
conversation_history = {}  # {user_id: [{"role": "...", "content": "..."}]}

# ---- Unicode cleaning ----
ASCII_PUNCT_MAP = {
    "\u2018": "'", "\u2019": "'",   # curly single quotes
    "\u201C": '"', "\u201D": '"',   # curly double quotes
    "\u2013": "-", "\u2014": "-",   # en/em dashes
    "\u2026": "...",                # ellipsis
    "\u00A0": " ", "\u2009": " ", "\u200A": " ", "\u200B": "",  # spaces/ZWSP
    "\u2212": "-",                  # minus sign
    "\u00B7": "*", "\u2022": "*",   # bullets
}

def clean_ascii(text: str) -> str:
    if not text:
        return text

    # 1) Decode explicit escapes like \\u2014
    def _u(m):
        try:
            return chr(int(m.group(1), 16))
        except Exception:
            return m.group(0)
    text = re.sub(r"\\u([0-9a-fA-F]{4})", _u, text)

    # 2) Replace common Unicode punctuation with ASCII
    for u, a in ASCII_PUNCT_MAP.items():
        text = text.replace(u, a)

    # 3) Normalize, then drop remaining non-ASCII
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch if ord(ch) < 128 else " " for ch in text)

    # 4) Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ---- OpenAI call ----
def get_nadja_response(user_message, history):
    client = get_client()
    if not client:
        return "API configuration error. The spirits are confused."

    # Build messages array with more context
    msgs = [{"role": "system", "content": NADJA_SYSTEM_PROMPT}]
    msgs.extend(history[-8:])  # last 4 exchanges for better memory
    msgs.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=msgs,
            temperature=0.9,  # Slightly higher for more creativity
            max_tokens=60,    # Slightly more for wit
        )

        if response.choices and len(response.choices) > 0:
            text = response.choices[0].message.content.strip()
            text = clean_ascii(text)  # Fix Unicode issues
            return text if text else "The spirits are silent."
        else:
            return "No response from the void."

    except Exception as e:
        error_msg = str(e)
        print(f"OpenAI API error: {error_msg}")
        
        if "rate limit" in error_msg.lower():
            return "Even vampires have limits. Try again in a moment."
        elif "authentication" in error_msg.lower():
            return "My ancient powers cannot authenticate. Typical modern nonsense."
        elif "billing" in error_msg.lower() or "quota" in error_msg.lower():
            return "The cosmic energies require payment. How vulgar."
        
        return random.choice([
            "The spirits are busy. Probably Colin Robinson's fault.",
            "Technical difficulties. How typically modern.",
            "Even my ancient powers struggle with this nonsense.",
            "This is worse than Nandor trying to use a mobile phone.",
        ])

# ---- Routes ----
@app.get("/")
def root():
    return jsonify({"service": "nadja", "hint": "use /health or POST /chat"}), 200

@app.get("/health")
def health_check():
    ok = get_client() is not None
    return jsonify({
        "status": "OK" if ok else "API_KEY_MISSING",
        "message": "Nadja server health check",
        "model": MODEL
    }), 200

@app.get("/diag")
def diag():
    client = get_client()
    if not client:
        return jsonify({"ok": False, "reason": "no_client"}), 500
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "reply with exactly OK"},
                {"role": "user", "content": "ping"}
            ],
            temperature=0,
            max_tokens=3,
        )
        preview = response.choices[0].message.content.strip() if response.choices else "no response"
        return jsonify({"ok": True, "preview": preview}), 200
    except Exception as e:
        payload = {"ok": False, "error": str(e)}
        return jsonify(payload), 500

@app.post("/chat")
def chat_with_nadja():
    try:
        data = request.get_json(silent=True) or {}

        if data.get("secret") != SECRET_KEY:
            return jsonify({"error": "Unauthorized! This is worse than Guillermo's organizing!"}), 401

        user_message = (data.get("message") or "").strip()
        user_id = data.get("user_id", "unknown")

        if not user_message:
            return jsonify({"error": "Speak, mortal! My patience is ancient but limited."}), 400

        hist = conversation_history.setdefault(user_id, [])
        hist.append({"role": "user", "content": user_message})
        hist[:] = hist[-12:]  # Keep last 12 messages (6 exchanges)

        ai_response = get_nadja_response(user_message, hist)
        hist.append({"role": "assistant", "content": ai_response})
        hist[:] = hist[-12:]  # Keep last 12 messages

        return jsonify({"response": clean_ascii(ai_response)}), 200
    except Exception as e:
        print(f"Server error: {e!r}")
        return jsonify({"error": "This technology is so much worse than sunlight!"}), 500

@app.post("/reset/<user_id>")
def reset_conversation(user_id):
    data = request.get_json(silent=True) or {}
    if data.get("secret") != SECRET_KEY:
        return jsonify({"error": "You cannot reset me! This isn't one of Nandor's quests!"}), 401
    conversation_history.pop(user_id, None)
    return jsonify({"message": "Fine, clean slate. But I remember everything."}), 200

if __name__ == "__main__":
    print("Starting Nadja server")
    print(f"Model: {MODEL}")
    app.run(host="0.0.0.0", port=PORT, debug=False)





