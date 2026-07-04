# Case-scoped persistence and resumable ingestion status

This started as the design plan for Samuel's case-persistence work. It now documents the
**current shipped implementation** and the few remaining follow-ups.

---

## What is implemented now

ColdCache's primary UI is a **durable multi-case workspace**:
- the app opens on a blank **Case Home**
- cases are created and stored in application SQLite
- every uploaded file belongs to exactly one case
- evidence analysis and ingestion run as durable jobs
- progress survives reloads and backend restarts
- each case resolves to its own immutable Cognee dataset name
- case tools (`graph`, `chat`, `timeline`, `interrogation`, `whatif`, etc.) read through `case_id`

The browser is no longer authoritative for uploads, review text, or job status.

---

## Current user journey

1. `/` loads `CaseHome.jsx` and fetches `GET /cases`.
2. The user creates or opens a case.
3. Empty cases land in the import flow; cases with evidence open directly to the Evidence Board.
4. `POST /cases/{case_id}/evidence` stores files durably before background analysis starts.
5. Analysis jobs continue if the tab reloads or closes.
6. Returning to the case rehydrates evidence + jobs from the backend and reconnects to SSE.
7. Files enter `awaiting_review`; investigators can edit extracted text and autosave drafts.
8. Confirmation queues ingestion into that case's dataset.
9. The case workspace reads case-scoped graph/timeline/chat/interrogation/what-if data.

---

## Current architecture

```text
React case shell
  ├─ CaseHome
  ├─ CaseImportPanel
  ├─ GraphPanel
  ├─ CaseTimelinePanel
  ├─ CaseInterrogationPanel
  ├─ CaseWhatIfPanel
  └─ ChatPanel
                    │
                    │ REST + SSE
                    ▼
FastAPI case services (backend/main.py)
  ├─ SQLite app state via backend/case_store.py
  ├─ file storage under data/cases/<case_id>/...
  ├─ durable worker with leases + recovery
  ├─ case analysis cache via backend/case_analysis.py
  └─ Cognee adapter via backend/memory_service.py
                    │
                    ▼
Cognee dataset per case: case_<uuid_without_dashes>
```

---

## Current persistent schema (actual code)

Source of truth: `backend/case_store.py`.

### `cases`

| Field | Current implementation |
|---|---|
| `id` | UUID string primary key |
| `title` | required |
| `reference_number` | optional |
| `description` | optional |
| `jurisdiction` | optional |
| `incident_date` | optional |
| `status` | currently `open` / `archived` in normal UI flow |
| `dataset_name` | immutable `case_<uuidhex>` |
| `graph_revision` | integer revision counter |
| `created_at`, `updated_at`, `last_activity_at` | timestamps |

### `evidence_items`

| Field | Current implementation |
|---|---|
| `id`, `case_id` | UUID + owning case |
| `original_filename` | original client filename |
| `media_type`, `modality` | routing/display metadata |
| `size_bytes` | stored size |
| `sha256` | duplicate detection within a case |
| `storage_key` | backend-owned relative path under `data/` |
| `context` | investigator context |
| `status` | upload/analysis/review/ingestion lifecycle |
| `model_output` | raw extracted text |
| `reviewed_text` | investigator-confirmed text |
| `error_message` | durable failure surface |
| `created_at`, `updated_at` | timestamps |

Current evidence status flow:
```text
queued_analysis -> analyzing -> awaiting_review
awaiting_review -> queued_ingestion -> ingesting -> ingested
analysis_failed / ingestion_failed -> retry path
queued/running analysis -> cancellable in allowed states
```

### `jobs`

| Field | Current implementation |
|---|---|
| `id`, `case_id`, `evidence_id` | evidence_id nullable for case-wide jobs like reindex |
| `kind` | `analyze`, `ingest`, `reindex` |
| `status` | `queued`, `running`, `succeeded`, `failed`, `cancelled` |
| `stage` | human-readable progress stage |
| `progress` | integer percent |
| `attempt` | retry counter |
| `error_message` | durable failure message |
| `cancel_requested` | cancellation flag |
| `started_at`, `finished_at` | lifecycle timestamps |
| `lease_owner`, `lease_expires_at`, `heartbeat_at` | recovery-friendly job lease fields |
| `idempotency_key` | reserved column, not heavily exercised yet |

### `evidence_revisions`

Stores immutable review snapshots when evidence is confirmed.

### `job_events`

Append-only progress/event stream for SSE replay and polling reconciliation.

### `case_analyses`

Stores the persisted derived analysis keyed by case and `graph_revision`.

---

## Current backend behavior

### Uploads
- streamed to `data/upload_tmp/`
- size-limited (25 MB/file, 50 files and 250 MB/batch defaults)
- hashed while streaming
- atomically moved into durable case storage

### Worker / recovery
- queued jobs are claimed transactionally
- running jobs get renewable 45-second leases
- heartbeats keep leases fresh
- expired jobs recover back to `queued`
- job events are recorded durably for replay

### Review flow
- investigators can edit extracted text before ingestion
- drafts autosave via `PATCH /cases/{case_id}/evidence/{evidence_id}/draft`
- optimistic concurrency uses `expected_updated_at`

### Ingestion
- confirmed evidence is wrapped in a provenance-rich packet before Cognee sees it
- per-case writes are serialized safely
- graph revision is bumped after successful ingestion

### Reindex
- `POST /cases/{case_id}/reindex` creates a durable case-wide job
- a replacement dataset is built first
- activation is atomic
- cached derived analysis is invalidated only after success

### Deletion
- non-ingested evidence deletes directly
- ingested evidence uses a safe dataset rebuild path
- cases with active jobs cannot be deleted

---

## Current frontend behavior

### Implemented
- blank case home
- create/open/archive/restore/delete case actions
- durable import queue with SSE + polling
- autosaved review drafts
- case-scoped Evidence Board / Timeline / Interrogation / What-If / Chat
- visible case graph rebuild action

### Not currently surfaced in the main UI
- backend `/case-name` helper endpoints
- backend case-scoped `report`, `hunch`, and `resolve` routes
- legacy global demo routes and panels

Those routes still exist, but they are not the dominant product path anymore.

---

## What this work fixed vs the old architecture

Before this merge:
- uploads and progress lived largely in React state
- reloads could lose queue context
- process-memory collections like `PENDING_INGESTIONS` / `UPLOADED_NODES` were authoritative for the main UI
- all features pointed at the shared global `coldcases` dataset

Now:
- the current app's authoritative state is backend-owned
- each case is isolated
- jobs survive browser lifecycle events
- case tools resolve server-side from `case_id`

(Those legacy global collections still exist in `backend/main.py`, but only for the older demo-compatible routes.)

---

## Remaining follow-ups

### High confidence / likely
- finer-grained extractor progress where provider/tooling allows it
- stronger use of `idempotency_key`
- optional Postgres/object storage/dedicated worker split for heavier deployments

### Product decisions still open
- whether to expose case-scoped `report` / `resolve` / `hunch` again in the main frontend
- whether to remove or rework the legacy `/case-name` surface for multi-case UX
- whether to prune or fully revive leftover legacy frontend components

---

## Verification checklist

- reload during analysis: queue rehydrates
- backend restart during running job: expired lease recovers cleanly
- duplicate file in same case: skipped instead of reprocessed
- case-scoped graph/chat/report isolation: case A does not read case B
- ingested evidence deletion: rebuild path keeps remaining case knowledge intact
- SSE disconnect: polling fallback still reconciles state
