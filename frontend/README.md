# Frontend — ColdCache Cold Case Connector

React + Vite. Three panels: **Case Graph** (force-graph + expunge demo), **Graph vs
Vector** (3-way retrieval compare), **Timeline**.

## Run (Benjy — you're unblocked, no Cognee needed)
```bash
# terminal 1 — backend (pick ONE):
python ../scripts/mock_server.py          # zero-dep stdlib mock (works anywhere)
#   or, on a machine with deps:
uvicorn backend.main:app --port 8000      # FastAPI (auto live/degraded)

# terminal 2 — frontend:
npm install
npm run dev                               # http://localhost:5173
```

The header badge shows the backend mode (`live` / `degraded` / `offline`). Point at a
different backend with `VITE_API_BASE=http://host:8000 npm run dev`.

## Where to extend
- `src/components/GraphPanel.jsx` — add the `improve()` animation (re-fetch graph, pulse
  the newly-promoted edge after POST /resolve).
- `src/components/ComparePanel.jsx` — add per-mode latency + a "why graph won" callout.
- `src/api.js` — single source of backend routes; matches `docs/API_CONTRACT.md`.
