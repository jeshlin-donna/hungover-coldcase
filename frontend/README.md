# Frontend — ColdCache Cold Case Connector

React + Vite. **8 panels** covering the full investigative co-pilot workflow.

## Run

```bash
# Terminal 1 — backend (pick ONE):
python ../scripts/mock_server.py          # zero-dep stdlib mock (works anywhere)
#   or, on a machine with deps:
source ../.venv/bin/activate
uvicorn backend.main:app --port 8000      # FastAPI (auto live/degraded)

# Terminal 2 — frontend:
npm install
npm run dev                               # http://localhost:5173
```

The header badge shows backend mode (`live` / `degraded`). Use a different backend:
```bash
VITE_API_BASE=http://host:8000 npm run dev
```

## The 8 Panels

| Tab | Component | What it does |
|---|---|---|
| Case Graph | `GraphPanel.jsx` | Force-directed entity graph, alibi red edges, expunge animation |
| Graph vs Vector | `ComparePanel.jsx` | 3-col naive/RAG/graph compare, GRAPH WINS banner on multi-hop |
| Timeline | `TimelinePanel.jsx` | Chronological incidents + temporal slider (Jan 2023–Dec 2025) |
| Missing Hours | `MissingHoursPanel.jsx` | Timeline gaps with CRITICAL/HIGH urgency + recommendations |
| Nexus | `NexusPanel.jsx` | Shortest entity path between any two graph nodes |
| Interrogation | `InterrogationPanel.jsx` | Trap questions, weak edges, strategy brief |
| What-If | `WhatIfPanel.jsx` | Hypothesis → before/after confidence bar chart |
| Upload | `UploadPanel.jsx` | **Multimodal drag-drop** — all file types, see below |

## Multimodal Upload Panel

`UploadPanel.jsx` accepts any of these — the backend routes each to the right extractor:

| File type | Pipeline shown to user |
|---|---|
| 🖼️ `.jpg .png .gif .webp` | Image preview → "Claude Vision will extract forensic details" |
| 🎙️ `.mp3 .wav .m4a .ogg .aac` | "Transcribing audio…" → transcript shown inline |
| 🎬 `.mp4 .mov .avi .webm` | "Extracting frames…" → per-timestamp descriptions |
| 📄 `.pdf` | "Extracting PDF…" → page-by-page text |
| 📊 `.xlsx .xls .csv` | "Parsing spreadsheet…" → column/row summary |
| 📃 `.txt .md` | Direct ingest |

After ingestion, the extracted description appears inline in the "Recently ingested" list.

## API

All backend calls go through `src/api.js`. Routes match `docs/API_CONTRACT.md` exactly.

## Where to extend

- `GraphPanel.jsx` — improve() animation: re-fetch graph after POST /resolve, pulse newly-promoted edges
- `ComparePanel.jsx` — add per-mode latency display
- `UploadPanel.jsx` — add audio waveform preview, video thumbnail extraction
- `src/api.js` — single source of backend routes
