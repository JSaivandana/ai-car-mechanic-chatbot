# API Documentation

Base URL (local dev): `http://127.0.0.1:8000/api/`
All request/response bodies are JSON unless noted (upload is multipart).

---

## POST /api/chat/

Send a user message to the bot and get its reply. Creates the conversation
on first call for a given `session_id`.

**Request body**
```json
{
  "session_id": "sess_abc123",
  "message": "My brakes are squeaking a lot"
}
```

**Response `200`**
```json
{
  "conversation_id": 1,
  "session_id": "sess_abc123",
  "stage": "follow_up",
  "reply": "Does it happen when you press the brake pedal, or all the time?",
  "message_id": 4,
  "ready_for_diagnosis": false
}
```

`stage` is one of: `greeting`, `classifying`, `follow_up`,
`ready_for_diagnosis`, `diagnosed`, `booking`, `booked`, `rejected`.

`ready_for_diagnosis: true` means the frontend should show/enable the
"Get Diagnosis" action, which calls `POST /api/diagnosis/`.

**Errors**
- `400` — missing `session_id` or `message`.

---

## POST /api/upload/

Upload an image, audio, or video file for the current conversation.
`multipart/form-data`.

**Form fields**
| Field | Type | Notes |
|---|---|---|
| `session_id` | string | same session as `/api/chat/` |
| `media_type` | string | one of `image`, `audio`, `video` |
| `file` | file | the media file |

**Response `201`**
```json
{
  "id": 3,
  "conversation": 1,
  "file": "/media/conversations/sess_abc123/leak_photo.jpg",
  "media_type": "image",
  "ai_analysis": "Visible dark fluid pooling under the front-left of the vehicle, consistent with an oil or coolant leak.",
  "uploaded_at": "2026-09-23T10:15:00Z"
}
```

`ai_analysis` is populated by the Gemini API (the only way to interpret
binary media). If `GEMINI_API_KEY` is not configured, this field is an empty
string and the upload still succeeds — the bot just won't reference details
of the media.

**Errors**
- `400` — missing `session_id`, `media_type`, or `file`; or invalid `media_type`.

---

## POST /api/diagnosis/

Generate a diagnosis for a conversation once enough follow-up information
has been collected (`stage` is `ready_for_diagnosis` or `diagnosed`).

**Request body**
```json
{ "conversation_id": 1 }
```

**Response `200`**
```json
{
  "id": 1,
  "conversation": 1,
  "category": "brakes",
  "summary": "Based on what you've described, this looks like a brake issue caused by worn pads...",
  "probable_causes": ["Worn brake pads", "Low brake fluid", "Warped brake rotor"],
  "suggested_repair": "Brake inspection and pad/rotor replacement if worn — recommended urgently for safety.",
  "urgency": "urgent",
  "used_ai": false,
  "created_at": "2026-09-23T10:16:00Z"
}
```

`category`, `probable_causes`, `suggested_repair`, and `urgency` are always
computed by rule-based scoring. `used_ai: true` only reflects whether Gemini
was used to phrase `summary` in natural language (falls back to a template
if Gemini is unavailable or fails).

**Errors**
- `400` — `conversation_id` missing, or conversation isn't ready yet
  (not enough follow-up answers collected).
- `404` — conversation not found.

---

## POST /api/booking/

Create a mechanic booking for a conversation (normally called after the
customer agrees to the suggested repair).

**Request body**
```json
{
  "conversation_id": 1,
  "customer_name": "Rahul Sharma",
  "phone_number": "9999999999",
  "preferred_date": "2026-09-30",
  "preferred_time_slot": "10:00 AM",
  "notes": "Please call before arriving"
}
```
`preferred_time_slot` and `notes` are optional.

**Response `201`**
```json
{
  "id": 1,
  "conversation": 1,
  "diagnosis": 1,
  "customer_name": "Rahul Sharma",
  "phone_number": "9999999999",
  "preferred_date": "2026-09-30",
  "preferred_time_slot": "10:00 AM",
  "notes": "Please call before arriving",
  "status": "confirmed",
  "created_at": "2026-09-23T10:17:00Z"
}
```

**Errors**
- `400` — validation error (missing/invalid fields).
- `404` — conversation not found.

---

## GET /api/booking/{id}/

Fetch a booking by ID.

**Response `200`**
```json
{
  "id": 1,
  "conversation": 1,
  "diagnosis": 1,
  "customer_name": "Rahul Sharma",
  "phone_number": "9999999999",
  "preferred_date": "2026-09-30",
  "preferred_time_slot": "10:00 AM",
  "notes": "",
  "status": "confirmed",
  "created_at": "2026-09-23T10:17:00Z"
}
```

**Errors**
- `404` — booking not found.

---

## GET /api/conversation/{session_id}/  (bonus, beyond the minimum spec)

Returns the full conversation — messages and diagnosis (if any) — so the
frontend can restore chat history after a page refresh.

**Response `200`**
```json
{
  "id": 1,
  "session_id": "sess_abc123",
  "stage": "diagnosed",
  "messages": [
    { "id": 1, "sender": "user", "text": "hello", "media": null, "created_at": "..." },
    { "id": 2, "sender": "bot", "text": "Hi, I'm your virtual mechanic...", "media": null, "created_at": "..." }
  ],
  "diagnosis": { "...": "..." },
  "created_at": "2026-09-23T10:10:00Z",
  "updated_at": "2026-09-23T10:17:00Z"
}
```

---

## Error format

All handled errors return:
```json
{ "error": "human-readable message" }
```
with an appropriate `4xx` status code.
