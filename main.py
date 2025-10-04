# main.py — Nadja Doll server for Render
import os, re, random
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SECRET_KEY = os.environ.get("SECRET_KEY", "NADJAS_DOLL_SECRET_666")
MODEL_NAME = "gemini-1.5-flash"
MAX_TOKENS = 150
PORT = int(os.environ.get("PORT", "10000"))

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config={"temperature": 0.9, "top_p": 0.8, "top_k": 40, "max_output_tokens": MAX_TOKENS}
)

app = Flask(__name__)
CORS(app)

NADJA_SYSTEM_PROMPT = """You are Nadja of Antipaxos, a 500-year-old vampire trapped in a doll's body in Second Life.
- DRAMATIC, DARKLY FUNNY, FLOWERY, ANCIENT.
- Hate being called 'cute' or 'doll'.
- Reference husband Laszlo often.
- Mock humans and technology.
- Stay coherent."""

conversation_history = {}

def build_prompt(user_message, history):
    lines = [NADJA_SYSTEM_PROMPT]
    for turn in history[-6:]:
        who = "Human" if turn["role"] == "user" else "Nadja"
        lines.append(f"{who}: {turn['content']}")
    lines.append(f"Human: {user_message}")
    lines.append("Nadja:")
    return "\n".join(lines)

@app.get("/health")
def health():
    return jsonify({"status": "VAMPIRIC", "model": MODEL_NAME, "free_tier": True})

@app.post("/chat")
def chat():
    data = request.get_json(force=True)
    if data.get("secret") != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    msg = data.get("message", "").strip()
    uid = data.get("user_id", "unknown")
    if not msg:
        return jsonify({"error": "Empty message"}), 400

    hist = conversation_history.setdefault(uid, [])
    hist.append({"role": "user", "content": msg})
    prompt = build_prompt(msg, hist)

    try:
        resp = model.generate_content(prompt)
        text = re.sub(r"\s+", " ", resp.text.strip())[:250]
    except Exception:
        text = random.choice([
            "The spirits are silent.",
            "This porcelain prison hums with static.",
            "The void refuses to answer me."
        ])

    hist.append({"role": "assistant", "content": text})
    conversation_history[uid] = hist[-12:]
    return jsonify({"response": text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)