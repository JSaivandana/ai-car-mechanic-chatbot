"""
Thin wrapper around the Gemini free API.

Per the task spec ("Use Gemini free API only where AI is actually
required... minimize AI/API usage"), this module is called from exactly
three places in bot_logic.py — free-text topic classification for
ambiguous messages, media (image/audio/video) analysis, and optional
natural-language phrasing of an already-computed diagnosis.

If GEMINI_API_KEY is not configured, or the request fails, every function
here degrades gracefully (returns None / a safe default) so the rest of
the app keeps working on rule-based logic alone.
"""

import base64
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15


def _gemini_available():
    return bool(settings.GEMINI_API_KEY)


def _call_gemini(parts):
    if not _gemini_available():
        return None
    try:
        response = requests.post(
            f"{settings.GEMINI_API_URL}?key={settings.GEMINI_API_KEY}",
            json={"contents": [{"parts": parts}]},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        logger.exception("Gemini API call failed")
        return None


def classify_freeform_text(text):
    """
    Used ONLY when the keyword-based rule engine cannot decide whether a
    message is car/mechanical-related. Returns True/False. If AI is
    unavailable, defaults to True (let the user proceed rather than
    wrongly rejecting them) so the bot still functions without a key.
    """
    if not _gemini_available():
        return True

    prompt = (
        "You are a strict binary classifier. Answer with only the single "
        "word YES or NO. Question: Is the following user message about a "
        "car, motorcycle, or other vehicle's mechanical/electrical "
        "problem, maintenance, or repair?\n\n"
        f"Message: \"{text}\""
    )
    result = _call_gemini([{"text": prompt}])
    if result is None:
        return True
    return result.strip().upper().startswith("Y")


def analyze_media(file_path, media_type, mime_type):
    """
    Used ONLY for uploaded images/audio/video, since traditional keyword
    logic cannot interpret binary media. Returns a short text description
    of anything relevant to a car issue, or None if AI is unavailable.
    """
    if not _gemini_available():
        return None

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
    except OSError:
        logger.exception("Could not read uploaded media file for analysis")
        return None

    encoded = base64.b64encode(file_bytes).decode("utf-8")

    prompt = (
        "You are a senior automobile technician. Briefly (2-3 sentences) "
        "describe anything relevant to a vehicle problem visible/audible "
        "in this media — e.g. visible damage, leaks, unusual sounds, dashboard "
        "warning lights, smoke color. If nothing car-related is present, say so."
    )
    parts = [
        {"text": prompt},
        {"inline_data": {"mime_type": mime_type, "data": encoded}},
    ]
    return _call_gemini(parts)


def generate_diagnosis_text(category, answers, causes, media_analysis=None):
    """
    Used ONLY to phrase the already rule-computed diagnosis (category,
    causes) in natural senior-technician language. Returns None if AI is
    unavailable, in which case bot_logic falls back to a template summary.
    """
    if not _gemini_available():
        return None

    answers_text = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in answers.items())
    prompt = (
        "You are a friendly, senior automobile technician talking to a customer. "
        "In 3-4 sentences, explain the likely diagnosis and recommend next steps. "
        "Be reassuring but clear about urgency. Do not invent facts beyond what's given.\n\n"
        f"Issue category: {category}\n"
        f"Customer answers: {answers_text}\n"
        f"Likely causes identified: {', '.join(causes)}\n"
        f"Media analysis notes: {media_analysis or 'none'}"
    )
    return _call_gemini([{"text": prompt}])
