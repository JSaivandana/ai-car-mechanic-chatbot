# Architecture

## Overview

```
┌──────────────────┐        HTTPS/JSON        ┌───────────────────────┐
│   Next.js (React) │ ───────────────────────► │  Django REST Framework │
│   Chat UI         │ ◄─────────────────────── │  (backend/)            │
│   (Vercel)        │                           │  (AWS EC2)             │
└──────────────────┘                           └────────────┬──────────┘
                                                              │
                                          ┌───────────────────┼───────────────────┐
                                          │                   │                   │
                                    SQLite (db.sqlite3)  Rule engine        Gemini API
                                    conversations,        (bot_logic.py)    (ai_client.py)
                                    messages, media,       — no network      — network call,
                                    diagnoses, bookings     call, pure       used in 3 narrow
                                                             Python logic     spots only
```

## Request flow

1. The frontend generates a `session_id` (stored in `localStorage`) the
   first time a visitor opens the chat, and sends it with every request.
2. `POST /api/chat/` gets-or-creates a `Conversation` row for that
   `session_id`, stores the user's message, and calls
   `bot_logic.handle_user_message()`.
3. `bot_logic.py` is a **rule-based state machine** driven by
   `Conversation.stage` and `Conversation.context` (a JSON field used for
   slot-filling): `greeting → classifying → follow_up → ready_for_diagnosis
   → diagnosed → booking → booked` (with a `rejected` branch for
   off-topic queries).
4. Once enough follow-up answers are collected, the frontend calls
   `POST /api/diagnosis/`, which runs rule-based scoring
   (`bot_logic.build_diagnosis()`) against a keyword → category → repair
   knowledge base, then saves a `Diagnosis` row.
5. If the customer agrees, the frontend shows the "Book Mechanic" form and
   calls `POST /api/booking/`, creating a `Booking` row linked to the
   conversation and diagnosis.

## Data model

- **Conversation** — one per chat session; holds `stage` and `context`
  (the rule engine's working memory: detected category, collected
  follow-up answers, any media-analysis text).
- **Message** — every user/bot turn, for chat history display.
- **MediaUpload** — uploaded image/audio/video, plus an optional
  `ai_analysis` text field.
- **Diagnosis** — one per conversation: category, causes, suggested
  repair, urgency, and whether AI was used to phrase the summary.
- **Booking** — links back to the conversation (and diagnosis, if any),
  with customer contact details, preferred date/time, and status.

## Why AI usage is minimized (evaluation criterion)

The task explicitly asks to "use traditional backend logic wherever
possible and minimize AI/API usage." Concretely:

| Capability | How it's implemented | Uses AI? |
|---|---|---|
| Detecting the topic/category of a message | Keyword matching against a category → keyword map | No |
| Rejecting clearly irrelevant queries (weather, jokes, etc.) | Keyword reject-list | No |
| Classifying a genuinely ambiguous free-text message | — | **Yes** — Gemini, only when the keyword engine can't decide |
| Choosing which follow-up question to ask next | Static per-category question list + slot-filling in `context` | No |
| Interpreting an uploaded photo/audio/video | — | **Yes** — Gemini is the only way to read binary media |
| Scoring the diagnosis (category, causes, repair, urgency) | Rule-based lookup table (`REPAIR_SUGGESTIONS`) | No |
| Phrasing the diagnosis as a natural paragraph | Gemini if available, else a template string | **Optional** — always has a non-AI fallback |
| Booking creation/lookup | Plain Django ORM + validation | No |

So a full conversation — greeting, symptom classification, follow-up
questions, diagnosis, and booking — can complete **without ever calling
Gemini**, as long as the user's initial message contains a recognizable
car-related keyword (which is true for the overwhelming majority of real
symptom descriptions). AI is reserved for the two things rule-based logic
genuinely cannot do (media understanding, and disambiguating truly
unclear text), plus one optional cosmetic step (natural-language
phrasing) that degrades gracefully.

## Frontend structure

- `pages/index.js` — page shell.
- `components/ChatWindow.js` — owns all chat state (messages, session id,
  conversation id, diagnosis, booking) and calls the API helpers.
- `components/MessageBubble.js` — renders a single chat message.
- `components/MediaUpload.js` — three buttons (photo/audio/video) that open
  a native file picker and call `onUpload(file, mediaType)`.
- `components/BookingModal.js` — the "Book Mechanic" form shown after a
  diagnosis.
- `lib/api.js` — thin fetch wrappers for all 5+1 backend endpoints, plus
  `session_id` management via `localStorage`.

## Deployment topology

- **Frontend** is stateless and deployed to **Vercel** (free tier) directly
  from the `frontend/` directory.
- **Backend** is a standard WSGI Django app deployed to a free-tier **AWS
  EC2** instance behind Gunicorn (+ optionally nginx), using **SQLite** as
  a simple file-based database — no extra managed database service needed,
  keeping the whole stack inside the free tier as required.
- CORS is restricted via `CORS_ALLOWED_ORIGINS` to the deployed frontend
  origin.
