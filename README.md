# FinBuddy

AI-powered personal finance assistant with conversational transaction tracking. Talk to it like a chat app — it extracts structured transaction data from natural language, persists it to a relational database, and surfaces spending patterns on a live dashboard.

```
"spent 500 on groceries today" → parsed → ₹500 expense, category: food, logged automatically
```

---

## Why This Exists

Most expense trackers require manual form entry: open app → tap "add transaction" → fill 4 fields → save. FinBuddy removes that friction — you describe what happened in plain English, and the assistant does the structuring.

This project was built to explore a specific engineering problem: **how do you reliably extract structured data (amount, category, date) from unstructured LLM output, without the conversation breaking when the model's response doesn't match the expected format?** The answer is in `core/llm.py` — defensive parsing with graceful fallback rather than assuming the model always cooperates.

---

## Features

- **Conversational transaction logging** — natural language in, structured SQLite row out
- **JWT-based authentication** — bcrypt-hashed PINs, httpOnly cookies (not localStorage, to reduce XSS exposure)
- **Analytics dashboard** — income vs. expense trend (Chart.js line chart), spending-by-category breakdown (doughnut chart)
- **Persistent chat memory** — the assistant has context of recent conversation turns and recent transactions when responding
- **Finance-scoped responses** — the model is prompted to decline off-topic questions, with varied refusal phrasing

---

## Architecture

```
finbuddy/
├── core/
│   ├── db.py          # SQLite layer — normalized schema, no ORM
│   ├── auth.py        # bcrypt hashing + JWT issuance/validation
│   └── llm.py         # Gemini API wrapper + response parsing
├── prompts/
│   └── finance_prompt.py   # Single source of truth for the system prompt
├── routers/
│   ├── auth.py         # /login, /register, /logout
│   └── api.py           # /chat, /dashboard, /api/* data endpoints
├── templates/            # Jinja2 HTML (login, register, chat, dashboard)
├── static/
│   ├── css/main.css       # Dark theme design system
│   └── js/                # Vanilla JS — chat handling, Chart.js rendering
└── main.py                # FastAPI app entrypoint
```

**Request flow for a chat message:**

```
User message
    → POST /api/chat
    → store_message() [user turn persisted]
    → fetch_chat_history() + fetch_recent_transactions() [context loaded]
    → build_chat_prompt() [prompts/finance_prompt.py]
    → call_gemini() [core/llm.py]
    → _parse_response() splits reply text from EXTRACTED_JSON block
    → store_transaction() if a transaction was detected
    → store_message() [bot turn persisted]
    → JSON response to frontend
```

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI | Async-native, automatic OpenAPI docs, type-safe with Pydantic |
| Database | SQLite (raw `sqlite3`) | No ORM overhead for a project this size; schema is explicit and auditable |
| Auth | bcrypt + python-jose (JWT) | Stateless sessions, no server-side session table needed |
| LLM | Google Gemini (`gemini-2.5-flash`) | Fast, cheap, sufficient reasoning for structured extraction |
| Frontend | Jinja2 + vanilla JS + Chart.js | No build step, no framework overhead — kept deliberately simple |

---

## Database Schema

```sql
users          (id, username, pin_hash, created_at)
transactions   (id, user_id, date, amount, type, category, description, created_at)
chat_memory    (id, user_id, role, message, created_at)
```

Transactions use **normalized columns**, not a JSON blob — this was a deliberate redesign decision (see [Design Decisions](#design-decisions)) so that category/date-range queries don't require `json_extract()`.

---

## Getting Started

### Prerequisites
- Python 3.11+
- A [Google Gemini API key](https://aistudio.google.com/apikey) (free tier available)

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/finbuddy.git
cd finbuddy

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Open .env and add your GEMINI_API_KEY and a random SECRET_KEY
```

### Run

```bash
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** — you'll be redirected to `/login`. Register a new account (username + 4-6 digit PIN), and you'll land on the chat page.

### Try it

```
"got paid 25000 salary today"
"spent 800 on dinner with friends"
"how much have I spent this month?"
```

Then check `/dashboard` to see the charts populate.

---

## Design Decisions

A few choices that came from iterating past an initial, less-defensible version:

- **JSON blob → normalized columns.** The first version stored each transaction as a JSON string in a single column. This made category/date filtering require `json_extract()` on every query. Switched to proper typed columns with an index on `(user_id, date)`.
- **No password → bcrypt PIN.** The original had no authentication — username alone was the identity. Added bcrypt-hashed PINs and JWT-based sessions.
- **Direct `bcrypt` over `passlib`.** `passlib` (last released 2020) has a broken compatibility shim with `bcrypt` 4.x that throws on `__about__` attribute lookup. Switched to calling `bcrypt.hashpw()` / `bcrypt.checkpw()` directly — fewer dependencies, no abandoned-library risk.
- **httpOnly cookies over localStorage.** JWTs are stored in httpOnly cookies so client-side JS cannot read the token, reducing the XSS attack surface.

---

## What I'd Do Differently at Scale

Being upfront about current limitations:

- **SQLite → PostgreSQL** for concurrent writes beyond a single-user demo.
- **No rate limiting** on `/api/chat` — a production version needs per-user request throttling to control Gemini API costs.
- **No retry/backoff** on Gemini API failures — currently a single try/except with a generic user-facing error.
- **No automated tests yet** — `tests/` exists but isn't populated. Next priority is covering `core/db.py` and `core/auth.py`.

---

## License

MIT
