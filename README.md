# AI Car Mechanic Chatbot

A web-based chatbot where a car owner chats with a virtual mechanic agent for
troubleshooting and diagnosis.

## Live Links

- **Frontend:** https://ai-car-mechanic-chatbot-8res.vercel.app
- **Backend API:** https://ai-car-mechanic-chatbot-1.onrender.com/api

> Note: the backend runs on Render's free tier, which spins down after ~15
> minutes of inactivity. The first request after an idle period can take
> 30-60 seconds to wake it back up — this is expected, not a bug. The free
> tier also doesn't persist the SQLite file across restarts/redeploys, so
> conversation/booking data created during a demo may be cleared afterward.

**Stack (exactly as specified in the task):**
- **Frontend:** React / Next.js — deploy on Vercel free tier
- **Backend:** Python + Django / Django REST Framework — deploy on AWS free tier
- **Database:** SQLite
- **AI:** Gemini free API, used only where AI is actually required

```
.
├── backend/    Django REST Framework API (chat, upload, diagnosis, booking)
├── frontend/   Next.js chat UI
├── API_DOCUMENTATION.md
├── ARCHITECTURE.md
└── README.md   (this file)
```

---

## 1. Backend setup (Django + DRF + SQLite)

### Requirements
- Python 3.10+
- pip

### Steps

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # then edit .env (see below)

python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver 0.0.0.0:8000
```

The API is now live at `http://127.0.0.1:8000/api/`.

### Environment variables (`backend/.env`)

| Variable | Purpose | Required |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key | Yes (use a random string in production) |
| `DJANGO_DEBUG` | `True`/`False` | Yes |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames | Yes in production |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origin(s) | Yes |
| `GEMINI_API_KEY` | Gemini free-tier API key | Optional — see below |
| `GEMINI_MODEL` | Gemini model name (default `gemini-1.5-flash`) | Optional |

**Without `GEMINI_API_KEY` set**, the bot still works end-to-end: topic
classification, follow-up questions, diagnosis and booking all run on rule
based logic. The bot simply skips media analysis and uses a template-based
diagnosis summary instead of an AI-phrased one. This was intentional — see
`ARCHITECTURE.md` for why AI usage is minimized.

### Running tests / sanity check

```bash
python manage.py check
python manage.py test   # if you add tests
```

---

## 2. Frontend setup (Next.js)

### Requirements
- Node.js 18+
- npm

### Steps

```bash
cd frontend
npm install

cp .env.local.example .env.local
# edit .env.local -> NEXT_PUBLIC_API_BASE_URL should point at your backend,
# e.g. http://127.0.0.1:8000/api for local dev

npm run dev
```

Open `http://localhost:3000`.

### Production build

```bash
npm run build
npm start
```

---

## 3. Deployment

### Frontend → Vercel (free tier)

1. Push this repo to GitHub.
2. In Vercel, "Add New Project" → import the repo → set **Root Directory** to `frontend`.
3. Add environment variable `NEXT_PUBLIC_API_BASE_URL` = your deployed backend URL
   (e.g. `https://your-backend.example.com/api`).
4. Deploy. Vercel builds with `npm run build` automatically.

### Backend → AWS free tier (EC2)

1. Launch a `t2.micro`/`t3.micro` Ubuntu EC2 instance (free tier eligible).
2. SSH in, install Python 3, pip, and (recommended) `nginx` + `gunicorn`.
3. Clone the repo, `cd backend`, create a virtualenv, `pip install -r requirements.txt`.
4. Create `backend/.env` with production values:
   - `DJANGO_DEBUG=False`
   - `DJANGO_ALLOWED_HOSTS=your-ec2-public-dns-or-domain`
   - `CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app`
   - `GEMINI_API_KEY=...` (optional)
5. `python manage.py migrate && python manage.py collectstatic --noinput`
6. Run with Gunicorn: `gunicorn config.wsgi:application --bind 0.0.0.0:8000`
   (put this behind `nginx` as a reverse proxy, and/or run it as a `systemd`
   service so it survives reboots).
7. Open port 80/443 (or 8000 for a quick test) in the EC2 security group.
8. Point the frontend's `NEXT_PUBLIC_API_BASE_URL` at this backend's public
   URL and redeploy the frontend.

> SQLite is file-based, so on EC2 it just needs a persistent EBS volume
> (the default root volume is fine) — no separate database service required,
> matching the free-tier constraint.

---

## 4. Bot behaviour summary

- Acts like a senior automobile technician.
- Only handles car/mechanical queries; politely rejects anything else.
- Asks category-specific follow-up questions (engine, brakes, battery/electrical,
  noise/vibration, overheating/leaks) before diagnosing.
- Can analyze uploaded images/audio/video when Gemini is configured.
- After diagnosis, suggests a repair and offers a "Book Mechanic" call to action.
- If the customer books, creates a mechanic booking through the backend
  (`POST /api/booking/`), returned with a booking reference / ID.

See `ARCHITECTURE.md` for how conversation state and AI-usage minimization work,
and `API_DOCUMENTATION.md` for full endpoint documentation.