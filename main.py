# main.py — Nadja Doll (Render-safe)

import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# Config
SECRET_KEY = os.getenv("SECRET_KEY", "NADJAS_DOLL_SECRET_666")  # set in Render
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PORT = int(os.getenv("PORT", "10000"))

# Lazy OpenAI client
_client = None
def get_client():
    global _client
    if _client is not None:
        return _client
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        _client = OpenAI(api_key=key)  # no proxies/api_base/engine
        return _client
    except Exception as e:
        # keep it None if init fails; don't crash routes
        print(f"OpenAI init failed: {e}")
        _client = None
        return None

# Prompt
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
    client = get_client()
    if not client:
        return "API configuration error. The spirits are confused."

    messages = [{"role": "system", "content": NADJA_SYSTEM_PROMPT}]
    messages.extend(history[-4:])
    messages.append({"role": "user", "content": user_message})

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=50,
            temperature=0.8,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return random.choice([
            "The spirits are busy. Probably Colin Robinson's fault.",
            "Technical difficulties. How typically modern.",
            "Even my ancient powers struggle with this nonsense.",
        ])

@app.get("/health")
def health_check():
    ok = get_client() is not None
    return jsonify({
        "status": "OK" if ok else "API_KEY_MISSING",
        "message": "Nadja server health check",
        "model": MODEL
    }), 200

@app.post('/chat')
def chat_with_nadja():
    try:
        data = request.get_json(silent=True) or {}

        if data.get('secret') != SECRET_KEY:
            return jsonify({"error": "Unauthorized! This is worse than Guillermo's organizing!"}), 401

        user_message = (data.get('message') or "").strip()
        user_id = data.get('user_id', 'unknown')

        if not user_message:
            return jsonify({"error": "Speak, mortal! My patience is ancient but limited."}), 400

        hist = conversation_history.setdefault(user_id, [])
        hist.append({"role": "user", "content": user_message})
        hist[:] = hist[-6:]

        ai_response = get_nadja_response(user_message, hist)
        hist.append({"role": "assistant", "content": ai_response})
        hist[:] = hist[-6:]

        return jsonify({"response": ai_response})
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({"error": "This technology is so much worse than sunlight!"}), 500

@app.post('/reset/<user_id>')
def reset_conversation(user_id):
    data = request.get_json(silent=True) or {}
    if data.get('secret') != SECRET_KEY:
        return jsonify({"error": "You cannot reset me! This isn't one of Nandor's quests!"}), 401

    conversation_history.pop(user_id, None)
    return jsonify({"message": "Fine, clean slate. But I remember everything."})

if __name__ == '__main__':
    print("Starting Nadja server")
    print(f"Model: {MODEL}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
