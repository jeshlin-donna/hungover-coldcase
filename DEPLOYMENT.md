# Deploying ColdCache

Split deployment: **frontend on Vercel**, **backend on Render** (or Railway/Fly.io — same
idea). The backend needs a persistent, long-running process (Cognee's local
SQLite/LanceDB storage + multi-minute graph-extraction calls), which serverless
platforms like Vercel's Python functions don't support well — see `render.yaml` at the
repo root for the exact config used here.

## 1. Backend → Render

1. Push this repo to GitHub (already done).
2. In Render: **New → Blueprint**, point at this repo. Render will read `render.yaml`
   at the root and create the web service automatically.
3. Before first deploy, set the one secret Render config leaves blank:
   - `LLM_API_KEY` → your Groq key (**Environment** tab → "Add secret", never commit this)
4. Deploy. First boot will be slow (installing `cognee`, `torch`/`fastembed`, etc.).
5. Confirm it's live: `curl https://<your-render-url>/health` → `{"ok":true,"mode":"live"}`

**Note on the free tier:** Render's free web services spin down after inactivity and
have a cold-start delay on the next request — fine for a demo, not for a low-latency
production app.

## 2. Frontend → Vercel

1. In Vercel: **New Project**, import this repo.
2. Set **Root Directory** to `frontend/` (monorepo — Vercel needs to know where the
   Vite app lives; `frontend/vercel.json` handles the rest).
3. Add one environment variable:
   - `VITE_API_BASE` → `https://<your-render-backend-url>` (no trailing slash)
4. Deploy. `frontend/src/api.js` already reads `import.meta.env.VITE_API_BASE` at
   build time, so no code changes are needed to point it at the deployed backend.

## Security notes

- The Groq key lives only in Render's server-side env vars — it's never sent to or
  readable from the frontend bundle. Confirmed: nothing in `frontend/src/` reads or
  embeds `LLM_API_KEY`.
- There is currently **no auth or rate limiting** on the backend. Anyone with the
  Render URL can call every endpoint and consume your Groq quota. Fine for a
  short-lived hackathon demo; add an API-key check or rate limiter (e.g.
  `slowapi`) before leaving this running publicly long-term.
- CORS is wide open (`allow_origins=["*"]` in `backend/main.py`) — tighten this to
  your actual Vercel domain if you want to lock down who can call the API from a
  browser.
