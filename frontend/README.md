# Frontend — ColdCache

React + Vite frontend for the **current multi-case workspace**.

The active app shell is no longer the original single-workspace demo. It now opens on a durable **Case Home**, then moves through case-scoped import/review into the workspace.

---

## Run

```bash
# backend
source ../.venv/bin/activate
uvicorn backend.main:app --port 8000

# frontend
npm install
npm run dev
```

Optional alternate backend:
```bash
VITE_API_BASE=http://host:8000 npm run dev
```

---

## Current UI flow

### 1. Case home

`CaseHome.jsx`
- loads `GET /cases`
- caches the last known non-sensitive case summary list in localStorage
- supports create / archive / restore / delete
- is authoritative only when the backend is reachable; cache is a reconnect aid

### 2. Import / review queue

`CaseImportPanel.jsx`
- uploads via `POST /cases/{id}/evidence`
- refreshes from both polling and SSE (`GET /cases/{id}/events`)
- lets investigators review/edit extracted text
- auto-saves drafts via `PATCH /cases/{id}/evidence/{evidence_id}/draft`
- confirms via `POST /cases/{id}/evidence/{evidence_id}/confirm`
- retries/cancels durable jobs

### 3. Workspace tabs

Mounted by `App.jsx` today:

| UI area | Component | Backend |
|---|---|---|
| Evidence Board | `GraphPanel.jsx` | `GET /cases/{id}/graph`, `POST /cases/{id}/reindex` |
| Timeline | `CaseTimelinePanel.jsx` | `GET /cases/{id}/timeline` |
| Interrogation | `CaseInterrogationPanel.jsx` | `POST /cases/{id}/interrogation` |
| What-If | `CaseWhatIfPanel.jsx` | `POST /cases/{id}/whatif` |
| Chat aside | `ChatPanel.jsx` | `POST /cases/{id}/chat`, `GET /cases/{id}/chat/suggestions` |

The header case label comes from the selected case record's stored title.

---

## Components currently imported by `App.jsx`

- `CaseHome.jsx`
- `CaseImportPanel.jsx`
- `GraphPanel.jsx`
- `CaseTimelinePanel.jsx`
- `CaseInterrogationPanel.jsx`
- `CaseWhatIfPanel.jsx`
- `ChatPanel.jsx`

---

## Components present in the repo but not part of the main app shell

These still exist under `src/components/`, mostly for legacy/demo compatibility:
- `InterrogationPanel.jsx`
- `TimelinePanel.jsx`
- `UploadPanel.jsx`
- `WhatIfPanel.jsx`
- `SuspectTimelinePanel.jsx` (imported in `App.jsx` but not rendered)

`GraphPanel.jsx` is dual-purpose: it supports the current case-scoped graph and still contains logic for the older global demo graph when no `caseId` is supplied.

---

## API notes

`src/api.js` still exposes both:
- **current case-scoped helpers** (`cases`, `caseEvidence`, `caseStats`, `caseTimeline`, etc.)
- **legacy/global helpers** (`graphTemporal`, `compare`, `missingHours`, `nexus`, `report`, `caseName`, `setCaseName`, etc.)

The current main UI primarily uses the case-scoped helpers.

Notable nuance:
- `caseName()` / `setCaseName()` still exist in `api.js`
- the current frontend does **not** call them
- `/case-name` is effectively backend-only / legacy at the moment

---

## Developer notes

- `CaseImportPanel.jsx` intentionally combines polling and SSE so reload/reconnect stays honest.
- `GraphPanel.jsx` can launch and watch a durable reindex job.
- `App.jsx` starts empty until a case is selected; this is the expected post-merge behavior.
- If you only populated the legacy `coldcases` dataset via `scripts/ingest.py`, the current frontend will still show an empty case home until you create a case in the app.
