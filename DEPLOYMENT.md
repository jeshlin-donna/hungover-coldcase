# Deploying ColdCache

The repo is currently set up for a split deployment:
- **backend on Render** via `render.yaml`
- **frontend on Vercel** via `frontend/vercel.json`

That matches the current codebase, but there is one important post-merge nuance:

> The main UI now depends on the app-owned case database (`data/coldcache.db`) and case file storage (`data/cases/`), not just the old global Cognee demo dataset.

---

## 1. Backend → Render

`render.yaml` is the source of truth.

### What it provisions
- one Python web service
- persistent Render disk mounted at `/opt/render/project/cognee_data`
- health check on `/health`
- Groq-based live config by default

### Deploy steps
1. Push the repo to GitHub.
2. In Render, create a **Blueprint** from the repo.
3. Set the missing secret:
   - `LLM_API_KEY`
4. Deploy.

### Runtime notes
- Render uses the Groq path from `render.yaml`.
- The local Ollama fallback path is **not** available on Render unless you provide your own reachable Ollama service and point `OLLAMA_ENDPOINT` at it.
- Persistent case data on Render comes from the mounted disk, not ephemeral container storage.

### Health check
```bash
curl https://<your-render-url>/health
```
Expect a payload like:
```json
{
  "ok": true,
  "mode": "live",
  "case_count": 0,
  "case_database": "coldcache.db",
  "fallback": {
    "active": false,
    "last_reason": null,
    "last_at": null
  }
}
```

---

## 2. Frontend → Vercel

`frontend/vercel.json` already matches the current Vite app.

### Deploy steps
1. Import the repo into Vercel.
2. Set **Root Directory** to `frontend/`.
3. Add:
   - `VITE_API_BASE=https://<your-render-backend-url>`
4. Deploy.

---

## 3. What setup.sh is and is not

`setup.sh` is a **local developer bootstrap**. It is not part of the hosted deployment path.

Use it locally to:
- create `.venv`
- install Python deps
- scaffold `.env`
- run the smoke test

Hosted deployments should follow `render.yaml` / `frontend/vercel.json` instead.

---

## 4. Optional legacy corpus preload

If you want the hosted backend's **legacy/global** routes (`/graph`, `/recall`, `/report`, benchmark/demo flows) to have the old hero corpus preloaded, you still need to run the ingest scripts separately in that environment.

That is independent from the current case home UI, which can start empty and let users create cases interactively.

---

## 5. Security notes

- The frontend never needs `LLM_API_KEY`.
- There is still no auth layer in the backend.
- CORS is permissive by default in dev-oriented code.
- Treat public deployment as demo-grade unless you add auth, quotas, and tighter CORS.
