"""
Rule-based conversation engine for the virtual mechanic.

Design goal (per the task spec): use traditional backend logic wherever
possible and call the Gemini API only where it is genuinely required.

AI (Gemini) is used in exactly three places, and nowhere else:
  1. `ai_client.classify_freeform_text`  — only when a user message does not
     match any keyword category AND does not match the reject list, i.e.
     the rule engine is genuinely unsure whether the query is car-related.
  2. `ai_client.analyze_media`           — only for uploaded images / audio /
     video, because pixels/audio can't be understood by keyword matching.
  3. `ai_client.generate_diagnosis_text` — only to turn the already-computed
     structured diagnosis (category, causes, repair, urgency — all decided
     by rule-based scoring below) into a natural, senior-technician-style
     paragraph. If Gemini is unavailable, a template-based summary is used
     instead so the feature still works without AI.

Everything else — topic filtering, follow-up question selection, slot
filling, diagnosis scoring, urgency calculation, booking flow — is plain
Python/Django logic with no external API calls.
"""

from . import ai_client

# ---------------------------------------------------------------------------
# Keyword knowledge base (traditional logic — no AI)
# ---------------------------------------------------------------------------

CAR_KEYWORDS = [
    "car", "vehicle", "engine", "brake", "brakes", "tire", "tyre", "battery",
    "oil", "transmission", "clutch", "gear", "gearbox", "exhaust", "radiator",
    "coolant", "alternator", "starter", "suspension", "steering", "axle",
    "headlight", "wiper", "dashboard", "warning light", "check engine",
    "spark plug", "fuel", "petrol", "diesel", "mileage", "ac ", "a/c",
    "air conditioning", "horn", "indicator", "wheel", "clutch plate",
    "noise", "smoke", "leak", "overheating", "stall", "stalling", "vibration",
    "squeak", "squeal", "grind", "grinding", "rattle", "knock", "knocking",
    "jerk", "jerking", "won't start", "not starting", "wont start",
    "sedan", "suv", "hatchback", "bike", "motorcycle", "scooter", "truck",
]

REJECT_HINT_KEYWORDS = [
    "weather", "recipe", "movie", "song", "homework", "math problem",
    "stock price", "cryptocurrency", "joke", "poem", "politics", "sports score",
    "girlfriend", "boyfriend", "relationship advice", "medicine", "doctor",
    "programming", "code review", "write an essay",
]

GREETING_WORDS = ["hi", "hello", "hey", "namaste", "good morning", "good evening"]

# category -> ordered list of follow-up questions (slot names -> prompt)
FOLLOW_UP_QUESTIONS = {
    "engine": [
        ("when_happens", "When does it happen — while starting, idling, or while driving?"),
        ("warning_light", "Is the check-engine or any warning light on the dashboard?"),
        ("sound_smell", "Do you notice any unusual sound, smoke, or smell when this happens?"),
    ],
    "brakes": [
        ("when_happens", "Does it happen when you press the brake pedal, or all the time?"),
        ("sound_smell", "Do you hear a squeal, grind, or feel a vibration in the pedal/steering?"),
        ("duration", "How long has this been happening — days, weeks, or just started today?"),
    ],
    "battery_electrical": [
        ("when_happens", "Does the car fail to start completely, or crank slowly?"),
        ("warning_light", "Are the dashboard lights, horn, and headlights working normally?"),
        ("duration", "Is this the first time, or has it happened before recently?"),
    ],
    "noise_vibration": [
        ("when_happens", "Does the noise/vibration happen at low speed, high speed, or while turning?"),
        ("sound_smell", "Can you describe the sound — knocking, rattling, squeaking, or grinding?"),
        ("duration", "How long has this been going on?"),
    ],
    "overheating_leak": [
        ("when_happens", "Does it overheat while idling, driving, or both?"),
        ("sound_smell", "Do you see any fluid leaking under the car, and what color is it?"),
        ("duration", "How long has this been happening?"),
    ],
    "general": [
        ("when_happens", "When did you first notice the issue?"),
        ("sound_smell", "Is there any unusual sound, smoke, smell, or warning light with it?"),
        ("duration", "How often does it happen — every time, or occasionally?"),
    ],
}

CATEGORY_KEYWORD_MAP = {
    "engine": ["engine", "stall", "stalling", "won't start", "wont start", "not starting", "smoke", "power loss", "jerk", "jerking"],
    "brakes": ["brake", "brakes", "brake pedal"],
    "battery_electrical": ["battery", "starter", "alternator", "headlight", "dashboard", "electrical", "horn", "wiper"],
    "noise_vibration": ["noise", "vibration", "squeak", "squeal", "grind", "grinding", "rattle", "knock", "knocking"],
    "overheating_leak": ["overheating", "overheat", "coolant", "radiator", "leak", "leaking"],
}

REPAIR_SUGGESTIONS = {
    "engine": {
        "causes": ["Fuel delivery issue", "Ignition system fault (spark plugs/coil)", "Sensor malfunction (e.g., MAF/O2 sensor)"],
        "repair": "Engine diagnostic scan and inspection of fuel/ignition system at a service center.",
        "urgency": "high",
    },
    "brakes": {
        "causes": ["Worn brake pads", "Low brake fluid", "Warped brake rotor"],
        "repair": "Brake inspection and pad/rotor replacement if worn — recommended urgently for safety.",
        "urgency": "urgent",
    },
    "battery_electrical": {
        "causes": ["Weak or dead battery", "Faulty alternator", "Loose/corroded battery terminals"],
        "repair": "Battery load test and alternator check; replace battery or terminals if needed.",
        "urgency": "medium",
    },
    "noise_vibration": {
        "causes": ["Worn suspension component", "Unbalanced wheel/tire", "Loose underbody part"],
        "repair": "Suspension and wheel alignment/balancing inspection.",
        "urgency": "medium",
    },
    "overheating_leak": {
        "causes": ["Coolant leak", "Faulty radiator or water pump", "Low coolant level"],
        "repair": "Cooling system pressure test and coolant top-up/leak repair — avoid driving until checked.",
        "urgency": "high",
    },
    "general": {
        "causes": ["Requires physical inspection to pinpoint the exact cause"],
        "repair": "General vehicle inspection at a service center.",
        "urgency": "medium",
    },
}

REJECTION_REPLY = (
    "I'm your virtual car mechanic, so I can only help with vehicle-related issues "
    "(engine, brakes, battery, noise, leaks, warning lights, etc.). "
    "Could you tell me more about a problem you're having with your car?"
)

GREETING_REPLY = (
    "Hi, I'm your virtual mechanic. Tell me what's going on with your vehicle — "
    "for example, a strange noise, a warning light, or trouble starting — and I'll help "
    "figure out what's wrong."
)


def _contains_any(text, keywords):
    text = text.lower()
    return any(kw in text for kw in keywords)


def _detect_category(text):
    text = text.lower()
    best_category, best_hits = None, 0
    for category, keywords in CATEGORY_KEYWORD_MAP.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits > best_hits:
            best_category, best_hits = category, hits
    return best_category, best_hits


def handle_user_message(conversation, text, media_analysis=None):
    """
    Core rule engine. Returns (bot_reply: str, ready_for_diagnosis: bool).
    `conversation.context` is mutated and must be saved by the caller.
    """
    ctx = conversation.context or {}
    stage = conversation.stage
    text_stripped = (text or "").strip()

    # --- Stage: fresh conversation -----------------------------------
    if stage == "greeting":
        if _contains_any(text_stripped, GREETING_WORDS) and not _contains_any(text_stripped, CAR_KEYWORDS):
            conversation.stage = "classifying"
            conversation.context = ctx
            return GREETING_REPLY, False
        stage = "classifying"  # fall through to classification below

    # --- Stage: classify the query ------------------------------------
    if stage == "classifying":
        category, hits = _detect_category(text_stripped)

        if hits == 0 and _contains_any(text_stripped, CAR_KEYWORDS):
            category = "general"
            hits = 1

        if hits == 0:
            if _contains_any(text_stripped, REJECT_HINT_KEYWORDS):
                conversation.stage = "rejected"
                conversation.context = ctx
                return REJECTION_REPLY, False

            # Genuinely ambiguous free text — this is one of the few
            # places we call the AI model, purely for topic classification.
            is_car_related = ai_client.classify_freeform_text(text_stripped)
            if not is_car_related:
                conversation.stage = "rejected"
                conversation.context = ctx
                return REJECTION_REPLY, False
            category = "general"

        ctx["category"] = category
        ctx["answers"] = {}
        ctx["initial_complaint"] = text_stripped
        if media_analysis:
            ctx["media_analysis"] = media_analysis
        conversation.stage = "follow_up"
        conversation.context = ctx
        return _next_follow_up_question(conversation)

    # --- Stage: collecting follow-up answers ---------------------------
    if stage == "follow_up":
        questions = FOLLOW_UP_QUESTIONS.get(ctx.get("category", "general"), FOLLOW_UP_QUESTIONS["general"])
        answers = ctx.get("answers", {})
        pending = [slot for slot, _ in questions if slot not in answers]

        if pending:
            # store the answer to the question we most recently asked
            current_slot = ctx.get("awaiting_slot")
            if current_slot:
                answers[current_slot] = text_stripped
            ctx["answers"] = answers
            conversation.context = ctx

        pending = [slot for slot, _ in questions if slot not in answers]
        if pending:
            return _next_follow_up_question(conversation)

        conversation.stage = "ready_for_diagnosis"
        conversation.context = ctx
        return (
            "Thanks, that's helpful. I have enough information now — "
            "type 'diagnose' or tap 'Get Diagnosis' to see what I think is wrong.",
            True,
        )

    # --- Stage: already diagnosed / booking / rejected -----------------
    if stage in ("ready_for_diagnosis", "diagnosed"):
        return (
            "I already have enough details for a diagnosis — tap 'Get Diagnosis' "
            "to see the result, or describe a new issue to start over.",
            True,
        )

    if stage == "rejected":
        category, hits = _detect_category(text_stripped)
        if hits > 0:
            conversation.stage = "classifying"
            conversation.context = ctx
            return handle_user_message(conversation, text_stripped, media_analysis)
        return REJECTION_REPLY, False

    return GREETING_REPLY, False


def _next_follow_up_question(conversation):
    ctx = conversation.context
    category = ctx.get("category", "general")
    questions = FOLLOW_UP_QUESTIONS.get(category, FOLLOW_UP_QUESTIONS["general"])
    answers = ctx.get("answers", {})
    for slot, prompt in questions:
        if slot not in answers:
            ctx["awaiting_slot"] = slot
            conversation.context = ctx
            return prompt, False
    conversation.stage = "ready_for_diagnosis"
    return "I have enough information for a diagnosis now.", True


def build_diagnosis(conversation):
    """
    Rule-based scoring produces the structured diagnosis. Gemini is used
    only as an optional final step to phrase the summary in natural,
    senior-technician language; if the AI call fails or is disabled, a
    template-based summary is used instead so the feature never breaks.
    """
    ctx = conversation.context or {}
    category = ctx.get("category", "general")
    info = REPAIR_SUGGESTIONS.get(category, REPAIR_SUGGESTIONS["general"])
    answers = ctx.get("answers", {})
    media_analysis = ctx.get("media_analysis")

    template_summary = (
        f"Based on what you've described ({ctx.get('initial_complaint', 'your issue')}), "
        f"this looks like a {category.replace('_', ' ')} issue. "
        f"Likely cause(s): {', '.join(info['causes'])}."
    )
    if media_analysis:
        template_summary += f" From the media you shared: {media_analysis}"

    used_ai = False
    final_summary = template_summary
    ai_text = ai_client.generate_diagnosis_text(
        category=category,
        answers=answers,
        causes=info["causes"],
        media_analysis=media_analysis,
    )
    if ai_text:
        final_summary = ai_text
        used_ai = True

    return {
        "category": category,
        "summary": final_summary,
        "probable_causes": info["causes"],
        "suggested_repair": info["repair"],
        "urgency": info["urgency"],
        "used_ai": used_ai,
    }
