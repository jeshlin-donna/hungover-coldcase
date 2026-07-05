# ColdCache — Execution Plan / Current Status

This file started as the hackathon execution checklist. It now doubles as a compact status map for the merged repo.

---

## 1. What the repo is now

ColdCache currently has two parallel product surfaces:

1. **Primary app:** a durable, multi-case workspace with backend-owned evidence/jobs/datasets
2. **Legacy demo surface:** the older global demo/benchmark routes kept for mock parity, benchmark scripts, and narrated demo flows

When making changes, document clearly which surface you are touching.

---

## 2. Primary current architecture

### Frontend
- `CaseHome.jsx`
- `CaseImportPanel.jsx`
- `GraphPanel.jsx`
- `CaseTimelinePanel.jsx`
- `CaseInterrogationPanel.jsx`
- `CaseWhatIfPanel.jsx`
- `ChatPanel.jsx`

### Backend
- app-owned SQLite + file store in `backend/case_store.py`
- durable worker in `backend/main.py`
- Cognee wrapper in `backend/memory_service.py`
- persisted derived analysis in `backend/case_analysis.py`

### Reliability features
- Groq → local Ollama fallback for Cognee recall and cognify
- Groq → local fallback for multimodal extraction
- health endpoint exposes fallback state
- reload-safe SSE + polling queue rehydration

---

## 3. Status by workstream

| Workstream | Status | Notes |
|---|---|---|
| Case persistence | ✅ | shipped |
| Durable ingestion jobs | ✅ | shipped |
| Per-case datasets | ✅ | shipped |
| Graph rebuild / atomic reindex | ✅ | shipped |
| Fallback system | ✅ | shipped |
| Main-doc accuracy pass | ✅ | completed in this branch |
| Full 3-way benchmark | 🔄 | still pending full live run |
| Private deployment hardening | ✅ | Docker Compose, persistent volume, TLS, Basic Auth, CORS, readiness |
| Multi-user production controls | ⬜ | per-user identity, audit logging, application rate limits |

---

## 4. Recommended mental model for contributors

### If you are changing the current app
Prefer documenting and testing these routes first:
- `/cases`
- `/cases/{id}/evidence`
- `/cases/{id}/events`
- `/cases/{id}/graph`
- `/cases/{id}/chat`
- `/cases/{id}/timeline`
- `/cases/{id}/interrogation`
- `/cases/{id}/whatif`

### If you are changing demo / benchmark behavior
Expect to touch:
- `/graph`, `/recall`, `/report`, `/benchmark`, `/expunge`
- `scripts/ingest.py`
- `demo/demo.py`
- `benchmark/benchmark.py`

---

## 5. Remaining high-value follow-ups

1. Regenerate final benchmark numbers.
2. Decide whether to fully remove unused legacy frontend components or restore them intentionally.
3. Decide whether `/case-name` remains backend-only legacy functionality or should be removed/reworked for multi-case UX.
4. Add per-user identity, audit logging, and application rate limits before sensitive multi-user hosting. The documented private deployment is protected at the edge with Basic Auth.
