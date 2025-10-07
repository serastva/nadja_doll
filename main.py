# main.py — Nadja Doll (Render-safe)

import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# ---- Config ----
SECRET_KEY = os.getenv("SECRET_KEY", "NADJAS_DOLL_SECRET_666")  # set in Render
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

# ---- Prompt ----
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

# ---- In-memory conversation store ----
conversation_history = {}  # {user_id: [{"role": "...", "content": "..."}]}

# ---- OpenAI call using Responses API ----
def get_nadja_response(user_message, history):
    client = get_client()
    if not client:
        return "API configuration error. The spirits are confused."

    # Build messages array
    msgs = [{"role": "system", "content": NADJA_SYSTEM_PROMPT}]
    msgs.extend(history[-4:])  # last turns
    msgs.append({"role": "user", "content": user_message})

    try:
        # Prefer Responses API
        resp = client.responses.create(
            model=MODEL,
            input=msgs,
            temperature=0.8,
            max_output_tokens=50,
        )

        # Fast path (SDK >= 1.30 provides output_text)
        text = getattr(resp, "output_text", None)
        if text:
            return text.strip()

        # Fallback parse
        out = []
        for item in getattr(resp, "output", []) or []:
            if getattr(item, "type", None) == "message":
                for c in getattr(item, "content", []) or []:
                    if getattr(c, "type", None) == "text":
                        out.append(getattr(c, "text", ""))
        text = " ".join(out).strip()
        if text:
            return text

        return "The spirits are silent."
    except Exception as e:
        # Log rich HTTP error if available
        try:
            r = getattr(e, "response", None)
            if r is not None:
                try:
                    body = r.text
                except Exception:
                    body = "<no body>"
                print(f"OpenAI API error: status={getattr(r,'status_code', '?')} body={body}")
            else:
                print(f"OpenAI API error: {repr(e)}")
        except Exception as _:
            print("OpenAI logging failed")
        return random.choice([
            "The spirits are busy. Probably Colin Robinson's fault.",
            "Technical difficulties. How typically modern.",
            "Even my ancient powers struggle with this nonsense.",
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
        r = client.responses.create(
            model=MODEL,
            input=[{"role": "system", "content": "reply with exactly OK"}, {"role": "user", "content": "ping"}],
            temperature=0,
            max_output_tokens=3,
        )
        preview = getattr(r, "output_text", "").strip()
        return jsonify({"ok": True, "preview": preview}), 200
    except Exception as e:
        payload = {"ok": False, "error": str(e)}
        try:
            res = getattr(e, "response", None)
            if res is not None:
                payload.update({"status": getattr(res, "status_code", None), "body": getattr(res, "text", None)})
        except Exception:
            pass
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
        hist[:] = hist[-6:]

        ai_response = get_nadja_response(user_message, hist)
        hist.append({"role": "assistant", "content": ai_response})
        hist[:] = hist[-6:]

        return jsonify({"response": ai_response}), 200
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
