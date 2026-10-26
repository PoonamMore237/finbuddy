# FinBuddy 3.0 — Advanced Generative AI Personal Finance Copilot

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-3.5%20Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**FinBuddy** is a full-stack, enterprise-grade AI financial copilot. Moving far beyond basic LLM prompts, it uses **Gemini 3.5 Flash with native function calling and tool execution**, **multimodal vision OCR for receipts and bills**, **autonomous financial health audits**, and a **state-of-the-art interactive FinTech dashboard**.

---

## 🚀 Key Highlights & Advanced Gen AI Features

### 1. Autonomous Agentic Tool Execution
Instead of brittle prompt-engineering and fragile regex parsing, FinBuddy uses Gemini native tool calling (`google.genai` SDK) to dynamically execute python tools against the user's live database:
- `log_transaction(amount, type, category, description, date)`: Validates and persists normalized financial records.
- `get_financial_summary(month)`: Queries live income, expenses, category breakdowns, and savings rates so the model reasons over actual mathematical ground truth.
- `set_category_budget(category, monthly_limit)`: Dynamically configures and updates category spending thresholds via natural dialogue.
- `simulate_sip_wealth(monthly_investment, annual_return_rate_pct, years)`: Runs compound interest calculations, wealth gain projections, and inflation adjustments.
- `search_financial_rules(topic)`: RAG knowledge base for 50/30/20 budgeting, Section 80C tax deductions, and emergency fund sizing.

### 2. Multimodal Receipt & Invoice Scanner
- Drag and drop or upload photos of physical receipts, grocery slips, restaurant bills, or utility invoices.
- Gemini Multimodal Vision automatically extracts: Merchant name, date, itemized bill breakdown, taxes, total amount, and assigns the correct category.
- Automatically records the expense and presents an itemized audit card in chat.

### 3. Agent Reasoning Trace Transparency
- The UI features an expandable **"🧠 Agent Reasoning"** drawer on assistant responses.
- Users can inspect the model's intermediate thoughts, tool calls, and observations.

### 4. Autonomous AI Financial Health Audit & Diagnostic Engine
- Deterministic 4-factor scoring model (0 to 100): Savings rate, 50/30/20 budget adherence, expense volatility, and tracking diligence.
- Generates an executive AI diagnostic report highlighting key strengths, spending leak warnings, and an actionable 3-step recommendation plan with projected monthly savings.

### 5. Interactive & Polished FinTech UI
- **Obsidian Dark Aesthetic:** Custom glassmorphism, responsive drawer layout, vibrant emerald & electric indigo accents.
- **Interactive Wealth Simulator:** Sliders for Monthly SIP, Expected Return %, and Horizon with real-time future value and inflation forecasting.
- **Live Category Budget Progress:** Color-coded progress bars with Safe, Warning, and Exceeded status pills.
- **Voice Input:** Web Speech API dictation for hands-free expense tracking.
- **Interactive Ledger:** Real-time search, category filtering, manual entry modal, and instant deletion with live chart sync.
- **Data Portability:** 1-click export of transactions to CSV.

---

## 🏛 Architecture

```
finbuddy/
├── core/
│   ├── agent.py       # Autonomous multi-tool financial agent loop
│   ├── audit.py       # AI Financial Health Audit & scoring engine
│   ├── vision.py      # Multimodal receipt & bill OCR processor
│   ├── knowledge.py   # Grounded financial knowledge base (RAG)
│   ├── db.py          # SQLite layer with normalized tables (users, transactions, budgets, memory)
│   ├── auth.py        # bcrypt PIN hashing + JWT issuance & verification
│   └── llm.py         # Backward-compatible LLM bridge
├── routers/
│   ├── auth.py        # /login, /register, /logout
│   └── api.py         # /chat, /scan-receipt, /dashboard, /budgets, /financial-health, /export
├── templates/         # Jinja2 templates (chat, dashboard, login, register)
├── static/
│   ├── css/main.css   # FinTech dark design system
│   └── js/            # chat.js & dashboard.js
├── tests/             # Automated test suite (pytest)
├── Dockerfile         # Multi-cloud production container image
├── docker-compose.yml # Container composition for local & VPS deployment
├── render.yaml        # Render cloud blueprint with persistent disk
├── Procfile           # Railway & Heroku Procfile
├── fly.toml           # Fly.io deployment configuration
├── cloudrun.yaml      # Google Cloud Run serverless manifest
└── main.py            # FastAPI entrypoint with lifespan startup & dynamic cloud PORT
```

---

## 🛠 Local Setup

### Prerequisites
- Python 3.11+
- [Google Gemini API Key](https://aistudio.google.com/apikey)

### 1. Clone & Activate Virtual Environment
```bash
git clone https://github.com/YOUR_USERNAME/finbuddy.git
cd finbuddy

python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the project root:
```ini
GEMINI_API_KEY=your_google_gemini_api_key
SECRET_KEY=your_random_jwt_signing_key_here
```

### 4. Run the Application
```bash
uvicorn main:app --reload --port 8000
```
Open **http://localhost:8000** in your browser. Register with a username and a 4–6 digit PIN.

---

## 🧪 Running Automated Tests

```bash
pytest
```
Runs 8 automated unit and integration tests covering database operations, auth hashing, budget tracking, wealth compounding, knowledge retrieval, and API healthchecks.

---

## ☁️ Cloud Deployment

FinBuddy is cloud-ready with native manifests for all popular hosting platforms:

| Platform | Deployment Method | Config File |
|---|---|---|
| **Render** | 1-Click Git Blueprint with persistent disk | `render.yaml` |
| **Railway** | Git Push with zero configuration | `Procfile` |
| **Google Cloud Run** | Serverless container deployment | `cloudrun.yaml` |
| **Fly.io** | Global edge container with volume mount | `fly.toml` |
| **Self-Hosted VPS** | One-command Docker Compose | `docker-compose.yml` |

See [DEPLOYMENT.md](file:///d:/finbuddy/DEPLOYMENT.md) for step-by-step instructions.

---

## 📄 License
MIT License. Built for modern, high-intelligence personal finance tracking.
