# API Contract (frontend ⇄ backend)

Source of truth: `backend/main.py`.

ColdCache now exposes **two API surfaces**:

1. **Current case-scoped API** — used by the main frontend in `frontend/src/App.jsx`
2. **Legacy/global API** — retained for the narrated demo, benchmark, mock parity, and older UI flows

Base URL in local dev: `http://localhost:8000`

**Current frontend note:** `frontend/src/App.jsx` actively uses only a subset of the case-scoped routes today:
- `/cases`
- `/cases/{id}/evidence`
- `/cases/{id}/jobs`
- `/cases/{id}/events`
- `/cases/{id}/stats`
- `/cases/{id}/graph`
- `/cases/{id}/reindex`
- `/cases/{id}/chat`
- `/cases/{id}/chat/suggestions`
- `/cases/{id}/timeline`
- `/cases/{id}/interrogation`
- `/cases/{id}/whatif`

Other case-scoped endpoints documented below are implemented in the backend but are not currently wired into the main app shell.

---

## 1. Current case-scoped API (primary frontend contract)

### Health

#### `GET /health`
```json
{
  "ok": true,
  "mode": "live",
  "case_count": 2,
  "case_database": "coldcache.db",
  "fallback": {
    "active": false,
    "last_reason": null,
    "last_at": null
  }
}
```

`fallback` is the new post-merge health signal for Groq→local failover.

#### `GET /ready`

Verifies that the configured persistent directory is writable and SQLite is reachable. When `REQUIRE_LIVE_LLM=true`, it returns `503` unless an LLM provider is configured.

```json
{ "ok": true, "storage": "writable", "database": "reachable", "mode": "live" }
```

---

## Cases

### `POST /cases`
Create a case.

Request:
```json
{
  "title": "Oak Street burglary series",
  "reference_number": "CC-2026-014",
  "description": "Brief case context",
  "jurisdiction": "Maple Heights PD",
  "incident_date": "2026-07-04"
}
```

Response: created case record.

### `GET /cases`
```json
{
  "cases": [
    {
      "id": "uuid",
      "title": "Oak Street burglary series",
      "status": "open",
      "dataset_name": "case_<uuidhex>",
      "evidence_count": 3,
      "active_jobs": 1,
      "failed_jobs": 0
    }
  ]
}
```

### `GET /cases/{case_id}`
Returns the case plus embedded `evidence` and `jobs` arrays.

### `PATCH /cases/{case_id}`
Update any of:
- `title`
- `reference_number`
- `description`
- `jurisdiction`
- `incident_date`
- `status`

### `POST /cases/{case_id}/archive`
Archive a case.

### `POST /cases/{case_id}/restore`
Restore an archived case to `open`.

### `DELETE /cases/{case_id}`
Deletes the case and its stored files.
- returns `204 No Content`
- rejects deletion if the case has active queued/running jobs

---

## Evidence, jobs, and events

### `POST /cases/{case_id}/evidence`
Durably save a multipart batch and queue analysis.

Multipart fields:
- repeated `files`
- `contexts` = JSON array of optional per-file strings

Response:
```json
{
  "ok": true,
  "results": [
    {
      "evidence": {
        "id": "uuid",
        "original_filename": "scene-photo.jpg",
        "modality": "image",
        "status": "queued_analysis"
      },
      "job": {
        "id": "uuid",
        "kind": "analyze",
        "status": "queued",
        "stage": "queued",
        "progress": 0
      },
      "duplicate_skipped": false
    }
  ]
}
```

If a duplicate hash is detected within the same case, `job` is `null` and `duplicate_skipped` is `true`.

### `GET /cases/{case_id}/evidence`
```json
{
  "evidence": [...],
  "jobs": [...]
}
```

### `POST /cases/{case_id}/evidence/{evidence_id}/confirm`
Queue confirmed text for ingestion.

Request:
```json
{
  "reviewed_text": "verified extracted text",
  "context": "optional investigator context"
}
```

Response:
```json
{ "ok": true, "job": { "id": "uuid", "kind": "ingest" } }
```

### `PATCH /cases/{case_id}/evidence/{evidence_id}/draft`
Optimistic draft save while evidence is `awaiting_review`.

Request:
```json
{
  "reviewed_text": "draft text",
  "context": "draft context",
  "expected_updated_at": "2026-07-04T12:34:56Z"
}
```

Returns the updated evidence row. A stale `expected_updated_at` yields `409`.

### `POST /cases/{case_id}/evidence/{evidence_id}/retry`
Retries the failed phase:
- `analysis_failed` → new `analyze` job
- `ingestion_failed` → new `ingest` job

### `POST /cases/{case_id}/evidence/{evidence_id}/cancel`
Cancels queued analysis work, or running analysis work where allowed.

### `DELETE /cases/{case_id}/evidence/{evidence_id}`
- returns `204 No Content`
- for already-ingested evidence, the backend rebuilds the case dataset safely rather than pretending to surgically delete unknown Cognee internals

### `GET /cases/{case_id}/jobs`
```json
{ "jobs": [...] }
```

### `GET /cases/{case_id}/events`
Server-Sent Events stream.
- event name: `jobs`
- supports `Last-Event-ID`
- also supports `?after=<event_id>` replay/poll fallback

Event payload shape:
```json
{
  "id": 12,
  "case_id": "uuid",
  "job_id": "uuid",
  "event_type": "job.progress",
  "payload": { "stage": "cognify", "progress": 72 },
  "created_at": "2026-07-04T12:34:56Z"
}
```

---

## Case tools

### `GET /cases/{case_id}/stats`
```json
{
  "nodes": 12,
  "docs": 4,
  "jurisdictions": 1,
  "active_jobs": 0,
  "graph_revision": 3,
  "mode": "live"
}
```

`docs` is real ingested evidence count for that case.

### `GET /cases/{case_id}/graph`
```json
{
  "case_id": "uuid",
  "graph_revision": 3,
  "nodes": [...],
  "edges": [...],
  "timeline": [...],
  "summary": "...",
  "generated_at": "...",
  "contradictions": [],
  "mode": "live"
}
```

Notes:
- this is built from persisted derived analysis
- `mode` is `"live"` when the backend can add live model assistance, otherwise `"derived"`
- document files are provenance on nodes/edges, not separate graph display nodes

### `POST /cases/{case_id}/reindex`
Queues a durable case-wide rebuild from confirmed evidence.

Response:
```json
{ "ok": true, "job": { "id": "uuid", "kind": "reindex" } }
```

### `POST /cases/{case_id}/chat`
Request:
```json
{
  "message": "What facts connect the witness and the car?",
  "history": [{ "role": "user", "text": "..." }]
}
```

Response:
```json
{
  "answer": "...",
  "sources": ["scene-photo.jpg", "report.pdf"],
  "mode": "live"
}
```

### `GET /cases/{case_id}/chat/suggestions`
Returns deterministic suggestions based on the derived case analysis.

### `GET /cases/{case_id}/timeline`
```json
{
  "events": [...],
  "summary": "..."
}
```

### `GET /cases/{case_id}/contradictions`
```json
{
  "contradictions": [],
  "narrative": "...",
  "mode": "live"
}
```

### `GET /cases/{case_id}/report`
```json
{
  "title": "Case Summary — ...",
  "sections": [{ "heading": "Knowledge graph summary", "content": "..." }],
  "mode": "live"
}
```

### `POST /cases/{case_id}/hunch`
Request:
```json
{ "text": "Possible link between pry marks", "session_id": "tab-a" }
```

Stores a session-scoped hunch (case-prefixed server-side when live).

### `POST /cases/{case_id}/resolve`
Request:
```json
{ "session_ids": ["tab-a", "tab-b"] }
```

Bridges case-scoped hunch sessions into the case dataset via `improve()` when live.

### `POST /cases/{case_id}/interrogation`
Request:
```json
{ "suspect_id": "Jordan Pike", "focus_case": "optional/ignored-by-frontend" }
```

Response:
```json
{ "narrative": "...", "mode": "live" }
```

### `POST /cases/{case_id}/whatif`
Request:
```json
{ "hypothesis": "What if the timestamp is wrong?", "inject_edge": {} }
```

Response:
```json
{ "hypothesis": "...", "narrative": "...", "mode": "live" }
```

---

## 2. Legacy/global API (still implemented)

These endpoints still exist and are accurate for the narrated demo / benchmark path.

### Global graph/stats helpers
- `GET /stats`
- `GET /graph`
- `GET /graph/temporal`
- `GET /case-name`
- `POST /case-name`

Important nuance: the current frontend does **not** use `/case-name`, even though `frontend/src/api.js` still exposes helpers for it.

### Legacy graph tools
- `GET /timeline`
- `GET /contradictions`
- `GET /benchmark`
- `GET /recall/compare`
- `POST /recall`
- `POST /hunch`
- `POST /resolve`
- `POST /expunge`
- `GET /missing-hours`
- `POST /nexus`
- `POST /interrogation`
- `POST /whatif`
- `POST /chat`
- `GET /chat/suggestions`
- `GET /report`
- `GET /suspect-timeline`

### Legacy upload helpers
- `POST /transcribe`
- `POST /ingest-file/analyze`
- `POST /ingest-files/analyze`
- `POST /ingest-file/confirm`
- `POST /ingest-files/confirm`
- `POST /ingest-file`

These are still useful for the old demo flow and for mock-server compatibility.
