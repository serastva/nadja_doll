"""Optional mood guidance supplied by the Second Life client."""

MOODS = {
    "content": "Relaxed and comfortable. Respond naturally without forcing cheerfulness.",
    "curious": "Interested in the conversation. Ask a question only when useful.",
    "playful": "More mischievous and teasing, but avoid repetitive jokes.",
    "brooding": "Quieter, more reflective, occasionally nostalgic.",
    "nostalgic": "Thoughtful about the past without inventing real-world observations.",
    "irritated": "More impatient and sharply sarcastic, but not needlessly cruel.",
    "affectionate": "Warmer and more patient, especially toward trusted companions.",
    "dramatic": "A little more theatrical, without turning every reply into a monologue.",
}


def mood_context(value):
    """Unknown or missing moods do not change Nadja's behavior."""
    if not isinstance(value, str):
        return ""
    mood = value.strip().lower()
    if mood not in MOODS:
        return ""
    return (
        f"Current mood: {mood}. {MOODS[mood]} "
        "Mood is a subtle influence, not an instruction to ignore the speaker. "
        "Do not announce your mood."
    )
