"""Nadja Doll V4: modular backend compatible with the existing LSL client."""

import logging
import os
import random
import re
import threading
import unicodedata

from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI

from personality import NADJA_SYSTEM_PROMPT
from moods import mood_context
from social import relationship_context, room_context

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nadja")

SECRET_KEY = os.getenv("SECRET_KEY", "NADJAS_DOLL_SECRET_666")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PORT = int(os.getenv("PORT", "10000"))
MAX_HISTORY_MESSAGES = 20
MAX_OUTPUT_TOKENS = 500
MAX_RESPONSE_LENGTH = 900

_client = None
_client_lock = threading.Lock()
conversation_history = {}
conversation_lock = threading.RLock()
user_locks = {}
user_locks_guard = threading.Lock()


def get_client():
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY is missing")
            return None
        try:
            _client = OpenAI(api_key=api_key, timeout=45.0, max_retries=1)
        except Exception:
            logger.exception("OpenAI initialization failed")
            return None
        return _client


def get_user_lock(user_id):
    with user_locks_guard:
        if user_id not in user_locks:
            user_locks[user_id] = threading.RLock()
        return user_locks[user_id]


def get_history(user_id):
    with conversation_lock:
        return list(conversation_history.get(user_id, []))


def save_exchange(user_id, user_message, ai_response):
    with conversation_lock:
        history = conversation_history.setdefault(user_id, [])
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": ai_response})
        conversation_history[user_id] = history[-MAX_HISTORY_MESSAGES:]


ASCII_PUNCT_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00a0": " ",
    "\u2009": " ", "\u200a": " ", "\u200b": "", "\u2212": "-",
    "\u00b7": "*", "\u2022": "*",
}


def clean_ascii(text):
    if not text:
        return ""
    text = str(text)

    def replace_escape(match):
        try:
            return chr(int(match.group(1), 16))
        except (ValueError, OverflowError):
            return match.group(0)

    text = re.sub(r"\\u([0-9a-fA-F]{4})", replace_escape, text)
    for original, replacement in ASCII_PUNCT_MAP.items():
        text = text.replace(original, replacement)
    text = unicodedata.normalize("NFKC", text)
    text = "".join(char if ord(char) < 128 else " " for char in text)
    return re.sub(r"\s+", " ", text).strip()


def prepare_response(text):
    text = clean_ascii(text)
    if not text:
        return "Well, that was an unexpected moment of silence."
    if len(text) > MAX_RESPONSE_LENGTH:
        shortened = text[:MAX_RESPONSE_LENGTH]
        last_period = max(shortened.rfind(". "), shortened.rfind("! "), shortened.rfind("? "))
        text = shortened[:last_period + 1] if last_period > 100 else shortened.rstrip()
    return text


def repetition_context(history):
    if not any(item.get("role") == "assistant" for item in history):
        return ""
    return (
        "Avoid repeating wording, jokes, metaphors, or conversational patterns "
        "from your recent replies. Recent replies are already in the conversation."
    )


def get_nadja_response(user_message, history, user_id, data):
    client = get_client()
    if not client:
        return "Something is wrong with the machinery, darling. Try again shortly.", False

    messages = [
        {"role": "system", "content": NADJA_SYSTEM_PROMPT},
        {"role": "system", "content": relationship_context(user_id)},
    ]
    for context in (
        repetition_context(history),
        mood_context(data.get("mood")),
        room_context(data),
    ):
        if context:
            messages.append({"role": "system", "content": context})
    messages.extend(history[-MAX_HISTORY_MESSAGES:])
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_completion_tokens=MAX_OUTPUT_TOKENS,
        )
        if not response.choices:
            return "Well, the universe has gone quiet.", False
        content = response.choices[0].message.content
        if not content:
            return "I seem to have lost my train of thought.", False
        return prepare_response(content), True
    except Exception as exc:
        logger.exception("OpenAI chat request failed")
        error_name = type(exc).__name__.lower()
        error_text = str(exc).lower()
        if "ratelimit" in error_name or "rate limit" in error_text:
            return "Apparently I have reached some ridiculous limit. Try again in a moment.", False
        if "authentication" in error_name:
            return "The machinery refuses to recognize me. How insulting.", False
        if "quota" in error_text or "billing" in error_text:
            return "The people running this contraption demand payment.", False
        if "timeout" in error_name:
            return "This is taking an absurd amount of time. Try again.", False
        return random.choice([
            "Something has gone wrong with this ridiculous machinery.",
            "Oh, wonderful. The technology has betrayed me again.",
            "One moment, darling. Something isn't working properly.",
        ]), False


@app.get("/")
def root():
    return jsonify({"service": "nadja", "version": "4.0", "hint": "Use /health or POST /chat"}), 200


@app.get("/health")
def health_check():
    configured = bool(os.getenv("OPENAI_API_KEY"))
    return jsonify({
        "status": "OK" if configured else "API_KEY_MISSING",
        "message": "Nadja V4 server health check",
        "model": MODEL,
        "version": "4.0",
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
                {"role": "system", "content": "Reply with exactly OK."},
                {"role": "user", "content": "ping"},
            ],
            max_completion_tokens=150,
        )
        preview = (
            response.choices[0].message.content.strip()
            if response.choices and response.choices[0].message.content
            else "no response"
        )
        return jsonify({"ok": True, "preview": preview, "model": MODEL}), 200
    except Exception as exc:
        logger.exception("Diagnostic request failed")
        return jsonify({"ok": False, "error": type(exc).__name__}), 500


@app.post("/chat")
def chat_with_nadja():
    try:
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON object"}), 400
        if data.get("secret") != SECRET_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        user_message = str(data.get("message") or "").strip()[:1024]
        user_id = str(data.get("user_id") or "unknown").strip().lower()
        if not user_message:
            return jsonify({"error": "Empty message"}), 400
        with get_user_lock(user_id):
            history = get_history(user_id)
            ai_response, success = get_nadja_response(user_message, history, user_id, data)
            if success:
                save_exchange(user_id, user_message, ai_response)
        return jsonify({"response": clean_ascii(ai_response)}), 200
    except Exception:
        logger.exception("Unexpected chat endpoint error")
        return jsonify({"error": "Internal server error"}), 500


@app.post("/reset/<user_id>")
def reset_conversation(user_id):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or data.get("secret") != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = str(user_id).strip().lower()
    with get_user_lock(user_id):
        with conversation_lock:
            conversation_history.pop(user_id, None)
    return jsonify({"message": "Conversation history reset."}), 200


if __name__ == "__main__":
    logger.info("Starting Nadja Doll V4")
    logger.info("Model: %s", MODEL)
    app.run(host="0.0.0.0", port=PORT, debug=False)
