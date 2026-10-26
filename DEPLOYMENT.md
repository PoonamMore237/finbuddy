# Deploying FinBuddy to the Cloud

FinBuddy 3.0 is built to be cloud-agnostic. It runs seamlessly on any cloud container or PaaS provider with zero modifications.

---

## Prerequisites
Before deploying, make sure you have:
1. **Google Gemini API Key** — from [Google AI Studio](https://aistudio.google.com/apikey).
2. **SECRET_KEY** — Any random 32+ character string used to sign JWT session cookies.

---

## Option 1: Deploy on Render (Recommended — Quick & Free/Low Cost)

Render is the simplest way to deploy FinBuddy with a persistent disk for SQLite.

### Steps:
1. Push your repository to **GitHub** or **GitLab**.
2. Sign in to [Render.com](https://render.com).
3. Click **New +** → **Blueprint** (or **Web Service**).
4. Select your `finbuddy` repository. Render will automatically detect `render.yaml`.
5. Under **Environment Variables**, add:
   - `GEMINI_API_KEY`: `your_actual_gemini_api_key`
   - `SECRET_KEY`: (Click generate or type a random string)
6. Click **Apply / Create Web Service**.
7. In ~2 minutes, your service will be live at `https://finbuddy-xxxx.onrender.com`.

---

## Option 2: Deploy on Railway (Fastest)

Railway auto-detects the `Procfile` and `requirements.txt`.

### Steps:
1. Go to [railway.app](https://railway.app) and click **Start a New Project**.
2. Select **Deploy from GitHub repo** and pick `finbuddy`.
3. In the Railway dashboard under **Variables**, set:
   - `GEMINI_API_KEY`: `your_gemini_api_key`
   - `SECRET_KEY`: `your_random_secret_string`
   - `PORT`: `8000`
4. Click **Deploy**. Railway will assign a public HTTPS domain.

---

## Option 3: Deploy on Google Cloud Run (Serverless)

Ideal if you are already using Google Cloud with your Gemini API project.

### Commands:
```bash
# 1. Authenticate with Google Cloud
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID

# 2. Build and push container to Google Artifact Registry / GCR
gcloud builds submit --tag gcr.io/YOUR_GCP_PROJECT_ID/finbuddy:latest

# 3. Deploy to Cloud Run
gcloud run deploy finbuddy \
    --image gcr.io/YOUR_GCP_PROJECT_ID/finbuddy:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars GEMINI_API_KEY="your_api_key",SECRET_KEY="your_random_secret"
```

Cloud Run will output your live URL (e.g. `https://finbuddy-xyz.a.run.app`).

---

## Option 4: Deploy on Fly.io (Global Edge)

```bash
# 1. Install Fly CLI and log in
fly auth login

# 2. Create the app (detected from fly.toml)
fly launch --no-deploy

# 3. Create persistent storage volume for the SQLite database
fly volumes create finbuddy_data --size 1

# 4. Set secrets
fly secrets set GEMINI_API_KEY="your_gemini_api_key" SECRET_KEY="your_secret_key"

# 5. Deploy
fly deploy
```

---

## Option 5: Self-Hosted Docker or VPS (AWS EC2, DigitalOcean, Linode)

To run FinBuddy on any Ubuntu/Debian VPS with Docker:

```bash
# 1. Clone repository on your server
git clone https://github.com/YOUR_USER/finbuddy.git
cd finbuddy

# 2. Create your .env file
cat <<EOF > .env
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=$(openssl rand -hex 32)
EOF

# 3. Launch with Docker Compose
docker compose up -d --build

# 4. Verify health
curl http://localhost:8000/health
```

---

## Monitoring & Health Checks
- **Healthcheck Endpoint:** `GET /health` returns `{"status": "ok", "service": "finbuddy"}`.
- All major cloud providers will automatically monitor this endpoint for container restarts and zero-downtime rolling deploys.
