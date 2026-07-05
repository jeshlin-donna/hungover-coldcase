# ColdCache · Cold Case Connector

> **A court camera caught the plate. Not a detective.**
> Three burglaries. Two police departments. Shared evidence in pieces, not in memory.
> ColdCache turns verified case files into a persistent, queryable graph.

Built for the **WeMakeDevs × Cognee Hackathon** · *Best Use of Open Source (self-hosted Cognee)* track.

**Hosting:** the durable free deployment is Docker Compose on an OCI Always Free VM; Cloudflare Pages or Vercel can optionally host only the static frontend. See [DEPLOYMENT.md](DEPLOYMENT.md). Do not use an ephemeral free backend for real cases.

> **Current app shape:** the primary UI is now a **multi-case workspace**. It opens on a blank case home, stores case metadata/evidence/jobs in SQLite, assigns each case its own Cognee dataset, and rehydrates progress after reloads or backend restarts.

> **Automatic fallback:** when Groq is rate-limited or returns a degraded Cognee reply, ColdCache can automatically retry against **local Ollama** instead of hanging or hard-failing. `GET /health` exposes the current fallback state.

---

## Running the App

There are three useful ways to run this repo, depending on what you want to exercise.

### Option A — Current app UI (case home + durable case workspaces)

**Prerequisites:**
- Python 3.10+
- Node 18+
- Optional but recommended: [Ollama](https://ollama.com) if you want local-only mode **or** Groq→local fallback

**1) Bootstrap Python deps and `.env`**
```bash
./setup.sh
```

This creates `.venv`, installs Python dependencies, and copies `.env.example` to `.env` if needed.

**2) Configure `.env`**

Choose one of these live setups:

**Groq + optional local fallback (recommended for speed)**
```dotenv
LLM_PROVIDER=custom
LLM_MODEL=groq/llama-3.1-8b-instant
LLM_ENDPOINT=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_...
LLM_INSTRUCTOR_MODE=tool_call
COGNEE_SKIP_CONNECTION_TEST=true

# Optional but recommended so rate limits can fall back locally
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_ENDPOINT=http://localhost:11434/v1
OLLAMA_VISION_MODEL=moondream
OLLAMA_TEXT_MODEL=llama3.1:8b
CACHING=false
```

If you want the fallback path available locally, run:
```bash
ollama serve
ollama pull moondream
ollama pull llama3.1:8b
```

**Fully local Ollama**
```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=gemma4:e4b
LLM_ENDPOINT=http://localhost:11434/v1
LLM_API_KEY=ollama_dummy_key
LLM_INSTRUCTOR_MODE=json_mode
LLM_MAX_COMPLETION_TOKENS=16384
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text:latest
VISION_MODEL=llava:7b
OLLAMA_BASE_URL=http://localhost:11434
COGNEE_SKIP_CONNECTION_TEST=true
```

Typical local pulls:
```bash
ollama pull gemma4:e4b
ollama pull nomic-embed-text
ollama pull llava:7b
```

**3) Optional smoke test**
```bash
./setup.sh --smoke
```

**4) Start the backend**
```bash
source .venv/bin/activate
uvicorn backend.main:app --port 8000 --reload
```

Check:
```bash
curl http://localhost:8000/health
```
You should see `mode` plus the new `fallback` block.

**5) Start the frontend**
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

**6) Use the current workflow**
- Create a case on the blank case home.
- Upload evidence into that case.
- Review/edit extracted text.
- Confirm ingestion.
- Continue into the Evidence Board / Timeline / Interrogation / What-If workspace.

### Persistent case storage

ColdCache's current UI does **not** require preloading the old hero corpus to function. Case data lives in:
- `$COLDCACHE_DATA_DIR/coldcache.db` — app-owned SQLite database (`data/` locally)
- `$COLDCACHE_DATA_DIR/cases/` — stored originals per case

Back up both together:
```bash
source .venv/bin/activate
python scripts/backup_cases.py
```

### Option B — Narrated demo / benchmark corpus (legacy global dataset flow)

These scripts still matter for the benchmark, `demo/demo.py`, and the legacy non-case-scoped routes under `/graph`, `/recall`, `/report`, etc.

```bash
source .venv/bin/activate
python scripts/generate_corpus.py
python scripts/ingest.py --reset
python demo/demo.py --reset
```

Important: this populates the legacy global `coldcases` dataset. It does **not** create rows in the current multi-case UI.

### Option C — Mock mode (no live LLM required)

```bash
# Terminal 1
python scripts/mock_server.py

# Terminal 2
cd frontend
npm install
npm run dev
```

This is useful for frontend work and preserves the mock-compatible global API surface.

---

## What changed in the merged codebase

### Persistent case workspaces

The dominant app architecture is now case-scoped:
- blank **Case Home** on `/`
- case CRUD via `/cases`
- durable evidence/job/event records in SQLite
- files stored under `$COLDCACHE_DATA_DIR/cases/<case_id>/...`
- one immutable Cognee dataset name per case
- reload-safe analysis/ingestion jobs with lease recovery
- case-scoped graph/chat/timeline/interrogation/what-if/report endpoints

See [`docs/CASE_PERSISTENCE_PLAN.md`](docs/CASE_PERSISTENCE_PLAN.md).

### Groq → local Ollama automatic fallback

ColdCache now has two fallback layers:

1. **Multimodal extraction fallback** in `backend/main.py`
   - `describe_image()` tries **Groq vision → local Ollama vision → Claude fallback**
   - `transcribe_audio()` tries **Groq Whisper → local Whisper**

2. **Cognee query/ingestion fallback** in `backend/memory_service.py`
   - `recall()` detects both hard Groq failures **and** degraded Cognee replies like `"Got it."`
   - `cognify()` retries against local Ollama if Groq extraction fails
   - typed local extraction can fall back one more step to untyped extraction rather than failing ingest outright
   - Cognee's internal 240-second retry floor is monkeypatched down via `COLDCACHE_LLM_RETRY_FLOOR_S` so the local fallback gets a chance to run quickly

Current health output includes:
```json
{
  "ok": true,
  "mode": "live",
  "fallback": {
    "active": false,
    "last_reason": null,
    "last_at": null
  }
}
```

### Current frontend surface

`frontend/src/App.jsx` now mounts:
- `CaseHome`
- `CaseImportPanel`
- `GraphPanel`
- `CaseTimelinePanel`
- `CaseInterrogationPanel`
- `CaseWhatIfPanel`
- `ChatPanel`

Legacy demo components still exist in `frontend/src/components/`, but several older single-case panels are no longer wired into the main app shell.

---

## Multimodal ingestion

Every uploaded file is converted to reviewable text before confirmation:

| Input | Current behavior |
|---|---|
| Image | Groq vision first when configured, otherwise local Ollama vision; Claude remains a last resort fallback |
| Audio | Groq Whisper first when configured, otherwise local Whisper |
| Video | Frame sampling + image description pipeline |
| PDF | PyMuPDF text extraction; scanned pages go through the image path |
| Spreadsheet | `pandas` structured text summary |
| Text | direct decode |

For the current case-scoped UI, uploads are **saved durably before analysis starts**, then confirmed evidence is wrapped into a provenance-rich knowledge packet before `remember()`/`cognify()`.

---

## API overview

There are now **two API surfaces** in `backend/main.py`:

1. **Primary current app APIs** — `/cases`, `/cases/{id}/evidence`, `/cases/{id}/graph`, `/cases/{id}/chat`, etc.
2. **Legacy/global demo APIs** — `/graph`, `/recall`, `/report`, `/timeline`, `/interrogation`, etc.

The current frontend primarily uses the first group. The second group remains for the benchmark, mock-server parity, and narrated demo compatibility.

See:
- [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md)
- [`docs/API_NOTES.md`](docs/API_NOTES.md)

---

## Benchmark status

The naive baseline is checked in and reproducible:

| Retriever | Multi-hop R@3 | Multi-hop R@5 | Multi-hop MRR |
|---|---:|---:|---:|
| naive cosine | 0.401 | 0.417 | 0.485 |
| cognee vector | pending full 261-doc run | pending | pending |
| cognee graph | pending full 261-doc run | pending | pending |

Run:
```bash
source .venv/bin/activate
python benchmark/benchmark.py        # full live run
python benchmark/benchmark.py --naive
```

---

## Repo map

| Path | Purpose |
|---|---|
| `backend/main.py` | FastAPI app, multimodal extraction, durable worker, current + legacy routes |
| `backend/memory_service.py` | Cognee wrapper plus Groq→local fallback logic |
| `backend/case_store.py` | SQLite case/evidence/job/event store |
| `backend/case_analysis.py` | persisted derived analysis used by case tools |
| `frontend/src/App.jsx` | current multi-case app shell |
| `frontend/src/components/CaseHome.jsx` | blank-state case list / create / archive / delete UI |
| `frontend/src/components/CaseImportPanel.jsx` | durable upload/review/confirm queue |
| `docs/CASE_PERSISTENCE_PLAN.md` | current status of the case-scoped architecture |
| `docs/API_CONTRACT.md` | current backend contract |
| `ARCHITECTURE.md` | end-to-end data flow and route split |

---

## Troubleshooting

**The current UI is blank after running `scripts/ingest.py`**
- Expected. `scripts/ingest.py` loads the legacy `coldcases` dataset for the demo/benchmark routes, not the case database used by the current case home.

**Groq works, but fallback never triggers**
- Confirm `ollama serve` is running.
- Check `OLLAMA_ENDPOINT`, `OLLAMA_VISION_MODEL`, `OLLAMA_TEXT_MODEL`.
- Watch `GET /health` for the `fallback` block.

**Case uploads survive reload, but not deletion/restoration mistakes**
- Back up the app database, case files, and Cognee stores together; see `DEPLOYMENT.md`.

**Mock mode vs live mode confusion**
- `GET /health` is the source of truth.
- `mode: "live"` means the backend imported Cognee successfully and has an LLM path configured.

---

## Team

- **Sam** (`samuelshine`) — Lead · AI / backend
- **Jesh** (`jeshlin-donna`) — AI / backend
- **Benjy** (`benjyguitar`) — Frontend / product

---

## AI Disclosure

Scaffolding, code, and documentation were produced with AI assistants and then reviewed/edited by the team. Declared per hackathon rules.
