# Case-scoped persistence and resumable ingestion plan

## Decision

ColdCache should open to a **case home**, not directly into the Daniel Marsh workspace.
With no cases, the home is an intentional blank state with one primary action: **Create case**.
Every uploaded file, review, ingestion job, graph dataset, chat, hunch, report, and derived
artifact belongs to exactly one case.

This must not be solved with browser storage alone. The backend must own uploads and jobs so work
remains useful after a tab closes, a page reloads, or another client opens the case. `localStorage`
may remember the last selected case, but it is never authoritative.

## Current gaps

- React owns the upload queue, review text, progress, and completed-file list.
- `PENDING_INGESTIONS` and `UPLOADED_NODES` are process-memory collections.
- Extraction and cognification happen inline without durable job identities.
- All features query the global `coldcases` Cognee dataset.
- Displayed progress is estimated in the browser, not a backend checkpoint.
- Reload cannot distinguish running, abandoned, failed, or completed work.
- Backend restart cannot resume work or explain where it stopped.

## Target user journey

1. `/` shows a case list. A new installation shows a blank state, not demo evidence.
2. The user creates a case with a title and optional reference, jurisdiction, description,
   incident date, and tags.
3. The app navigates to `/cases/:caseId/import`; case identity stays visible in the header.
4. A multi-file drop creates durable evidence records and stores the raw files before responding.
5. Backend analysis jobs run independently of the browser. Reloading or closing does not cancel.
6. Returning reconstructs the queue from the API and reconnects to progress events.
7. Analyzed files enter `awaiting_review`; context and extracted text can be edited later.
8. Confirmation creates ingestion jobs, cognified only into that case's Cognee dataset.
9. Chat, graph, timeline, reports, prompts, hunches, and deletion resolve through the case.

## Target architecture

```text
React case shell
  ├─ REST: cases, evidence, review actions
  ├─ SSE: case job/event stream (polling fallback)
  └─ local cache: last case + harmless UI preferences only
                    │
FastAPI case services
  ├─ SQLite WAL: durable domain records, jobs, events, revisions
  ├─ File store: data/cases/<case_id>/originals and derived artifacts
  ├─ Worker: claims queued jobs with leases and recovers abandoned leases
  └─ Cognee adapter: maps case_id -> immutable dataset_name
                    │
Cognee dataset per case: case_<uuid_without_dashes>
```

### Recommended MVP stack

- Application-owned **SQLite in WAL mode** through SQLAlchemy 2.x async. Cognee's internal
  relational store is not the ColdCache domain database and must not be coupled to it.
- Original and derived files under `data/cases/` through a storage adapter; production can swap
  to S3-compatible object storage.
- A backend worker may share the FastAPI process for the MVP if all jobs use durable leases and
  startup recovery. Production can split it into a dedicated worker.
- Server-Sent Events provide progress; `GET /jobs?updated_after=` is the reconnect fallback.
- Postgres can replace SQLite when multi-process/multi-user hosting is needed.

## Domain database

All IDs are UUIDs. Mutable user-edited records include timestamps and an optimistic `version`.

### `cases`

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `title` | Required human name |
| `reference_number` | Optional, indexed, not assumed globally unique |
| `description`, `jurisdiction`, `incident_date` | Optional metadata |
| `status` | `open`, `resolved`, `archived`, `deleting`, `delete_failed` |
| `dataset_name` | Immutable unique `case_<uuidhex>`; never based on editable title |
| `created_by` | Nullable until authentication exists |
| `last_activity_at` | Drives case-home ordering |

### `evidence_items`

| Field | Notes |
|---|---|
| `id`, `case_id` | Case ownership is mandatory and indexed |
| `original_filename`, `media_type`, `modality`, `size_bytes` | Display/routing metadata |
| `sha256` | Duplicate detection within a case |
| `storage_key` | Backend-generated path/key, never a client path |
| `status` | State machine below |
| `context` | Optional user context |
| `current_revision_id` | Last confirmed extracted-text revision |
| `cognee_document_id` | Nullable external ID when available |
| `error_code`, `error_message` | Durable sanitized failure details |

```text
uploaded -> queued_analysis -> analyzing -> awaiting_review
                                      └-> analysis_failed -> queued_analysis
awaiting_review -> queued_ingestion -> ingesting -> ingested
                                           └-> ingestion_failed -> queued_ingestion
any non-terminal state -> cancelled
ingested -> deleting -> deleted | delete_failed
```

### `evidence_revisions`

Preserve provenance instead of overwriting extraction:

- `id`, `evidence_id`, `revision_number`
- immutable `model_output` and editable `reviewed_text`
- `context_snapshot`, provider/model, and `prompt_version`
- `created_by`, `created_at`, and `confirmed_at`

### `jobs`

| Field | Notes |
|---|---|
| `id`, `case_id`, `evidence_id` | Evidence nullable for case-level jobs |
| `kind` | `analyze`, `ingest`, `delete_evidence`, `delete_case`, `generate_prompts`, etc. |
| `status` | `queued`, `running`, `succeeded`, `failed`, `cancel_requested`, `cancelled` |
| `stage` | Stable stage such as `vision`, `transcription`, `cognify` |
| `progress_current`, `progress_total`, `progress_percent` | Backend checkpoints |
| `attempt`, `max_attempts`, `next_attempt_at` | Retry policy |
| `lease_owner`, `lease_expires_at`, `heartbeat_at` | Crash recovery/single ownership |
| `idempotency_key` | Prevent duplicate jobs from retries/double-clicks |
| `error_code`, `error_message` | Durable user-safe failure |

### Supporting tables

- `job_events`: append-only progress history and SSE replay cursor.
- `case_chat_messages`: case-scoped conversation and source references.
- `case_hunches`: case-scoped Cognee session IDs and resolution state.
- `case_prompt_suggestions`: generated prompts keyed by graph revision.
- `case_graph_state`: dataset, graph revision, last cognify, and counts.
- `audit_events`: actor/action/target plus non-sensitive metadata.

## Job execution and recovery

### Ownership and leases

Upload returns after durable storage/database insertion. Closing the browser does not cancel work;
only an explicit cancel action does. Workers atomically claim queued jobs, assign a lease, and
heartbeat. On startup, expired `running` jobs return to `queued` when safe to retry, otherwise
they become `failed` with `recovery_required`.

### Idempotency

- Upload accepts a client-generated `Idempotency-Key`.
- Analysis can safely replace derived artifacts for the same revision.
- Ingestion checks for a prior successful job for that revision.
- Cognee writes are serialized per dataset with a case-specific lock.
- Include stable `CASE_ID`, `EVIDENCE_ID`, and `REVISION_ID` markers in submitted text so retries
  can reconcile nodes even if the SDK does not return document IDs.

### Honest progress

Progress comes from backend stages, pages, frames, or completed files. Examples:

- Video: stored 5%, frame extraction 10–30%, `n/N` frames 30–90%, persisted 100%.
- PDF: stored 5%, `n/N` pages 10–85%, assembled/persisted 100%.
- Ingestion: queued 0%, staged in Cognee 35%, cognifying 40–95%, indexed 100%.

When a provider call exposes no internal progress, show an indeterminate animation and elapsed
time—not a fabricated percentage.

## API design

The backend resolves datasets from `case_id`; clients never submit arbitrary dataset names.

### Cases

- `POST /cases`, `GET /cases`, `GET/PATCH /cases/{case_id}`
- `POST /cases/{case_id}/archive`, `/restore`
- `DELETE /cases/{case_id}` starts a typed-confirmation deletion job

### Evidence and jobs

- `POST /cases/{case_id}/evidence` — durable multipart batch upload + optional contexts;
  returns evidence/job IDs quickly.
- `GET /cases/{case_id}/evidence` — reconstruct queue with status filters.
- `GET/PATCH /cases/{case_id}/evidence/{evidence_id}` — detail/revisions/context.
- `POST /cases/{case_id}/evidence/{evidence_id}/analyze` — retry/re-analyze.
- `POST /cases/{case_id}/evidence/{evidence_id}/confirm` — persist review, queue ingestion.
- `POST /cases/{case_id}/evidence/confirm` — batch confirm with independent results.
- `POST /cases/{case_id}/evidence/{evidence_id}/cancel`
- `DELETE /cases/{case_id}/evidence/{evidence_id}`
- `GET /cases/{case_id}/jobs`, `GET /jobs/{job_id}`
- `GET /cases/{case_id}/events` — SSE with `Last-Event-ID` replay

### Case tools

Move `graph`, `timeline`, `contradictions`, `recall`, `chat`, `chat/suggestions`, `report`,
`interrogation`, `whatif`, `hunch`, and `resolve` beneath `/cases/{case_id}`. During migration,
global routes may target only an explicitly configured demo case and must emit deprecation headers.

## Frontend plan

### Routes and case home

- `/` — case home; blank state shows Create case and a separate explicit Load demo case action.
- `/cases/new` — creation form.
- `/cases/:caseId/import` — durable queue/review.
- `/cases/:caseId/workspace/:tab?` — evidence tools and chat.
- Unknown/deleted case IDs show recovery UI and a case-home link.

Case cards show status, evidence counts, active/failed jobs, and last activity. Archive is
reversible; delete is visually and operationally separate.

### Import queue

- Fetch evidence/jobs on mount rather than initializing authoritative state as empty.
- Group `Analyzing`, `Needs review`, `Ingesting`, `Failed`, and `In graph`.
- Show real backend stage, elapsed time, retry/cancel, and durable error details.
- Add an upload optimistically only after the server returns a durable evidence ID.
- Reconnect SSE on reload; replay events, then poll/reconcile if a gap remains.
- Show a compact case-wide active-job indicator outside the import screen.
- Closing a tab needs no warning because work intentionally belongs to the server.

### Browser caching

- Local storage: `last_case_id`, theme, dismissed tips, last workspace tab only.
- Use a query cache (TanStack Query recommended), always keyed by `case_id`.
- Cache is disposable; invalidate from server `case_revision` after reconnect.
- Never store raw evidence, extracted text, case chat, or credentials in local storage.

## Cognee isolation and caching

- One immutable dataset per case: `case_<uuidhex>`.
- Every memory-service call requires a repository-resolved dataset; remove request-path reliance
  on global `DATASET` defaults.
- Increment `case_graph_state.graph_revision` after ingest/delete/improve.
- Cache graph, suggestions, reports, and stats by `(case_id, graph_revision, query/options)`.
- Cross-case intelligence must be a future explicit, permissioned query across selected datasets;
  never merge case graphs for convenience.

## Deletion, privacy, and integrity

- Verify every evidence/job belongs to the case in the URL (prevents cross-case ID access).
- Stream uploads while hashing; enforce per-file, batch, MIME, and count limits.
- Generate storage keys; filenames are display data only.
- Case deletion: mark deleting → settle jobs → Cognee `forget(dataset)` → remove files → retain
  minimal audit tombstone. Failures stay visible and retryable.
- Evidence-level deletion depends on verified SDK document deletion. Until then, rebuild the case
  dataset without that evidence or clearly require whole-case deletion.
- Keep model output and investigator-confirmed text separate forever.

## Use-case matrix

| Scenario | Required behavior |
|---|---|
| Reload during analysis | Queue rehydrates; job continues; progress reconnects |
| Browser closes | Work continues; case home later shows active/completed jobs |
| Backend restarts | Expired leases recover without duplicate Cognee ingestion |
| One batch file fails | Siblings continue; failure retains context/error/retry |
| Duplicate in same case | SHA-256 warning; explicit skip or new revision |
| Same file in another case | Allowed; datasets remain isolated |
| Context edited after analysis | Explicit re-analysis or review-only edit; no silent version mixing |
| Two reviewers edit | Optimistic version conflict requires refresh/merge |
| Archived case | Read-only; running-job policy is explicit |
| Delete during job | Reject new jobs, coordinate cancellation, then forget graph |
| Network disconnect | UI reconnects; event replay fills the gap |
| Provider unavailable | Retry with backoff, then actionable blocked/failed state |

## Implementation phases

### Phase 1 — persistence foundation

1. ✅ Add application-owned SQLite WAL, schema initialization, repositories, and recovery.
2. ✅ Add atomic case-scoped file storage and SHA-256.
3. ✅ Implement backend case CRUD and blank frontend case home/create/select flow.
4. Seed Daniel Marsh only through explicit Load demo case action/script.

### Phase 2 — durable ingestion jobs

1. 🔄 Durable evidence/revision/job tables are active for v2 routes; legacy collections remain until route migration.
2. ✅ Durable IDs, leases/heartbeats, startup recovery, guarded retry, and safe cancellation are active.
3. 🔄 Extractors emit durable stages; page/frame-granular checkpoints remain provider-dependent.
4. Queue confirmation/cognification and serialize writes per case.
5. ✅ Server-rehydrated import queue uses SSE with polling fallback.

### Phase 3 — case-scope every feature

1. 🔄 `case_id` is required for graph, chat, suggestions, stats, and v2 evidence; remaining tools remain.
2. ✅ V2 case routes resolve immutable dataset names server-side.
3. 🔄 Graph revisions are active; derived response caching remains optional.
4. 🔄 All tools now have case-scoped routes; deprecated demo routes remain for explicit demo compatibility.

### Phase 4 — lifecycle hardening

1. ✅ Archive/restore and guarded case/evidence deletion are implemented.
2. Verify evidence-level Cognee deletion or safe dataset rebuild.
3. 🔄 Idempotency, upload quotas, revision provenance, and event audit are active; authentication-era retention remains.
4. Add Postgres/object-storage/dedicated-worker deployment when needed.

## Verification gates

- Reload at every stage without lost records or duplicate work.
- Kill/restart backend during extraction and cognify; verify lease recovery.
- Test mixed batches, partial failures, duplicates, and identical filenames.
- Prove case A chat/graph/report cannot retrieve case B evidence.
- Verify graph revision invalidates cached prompts/reports.
- Exercise archive, delete failure/retry, and disk cleanup.
- Test two-tab optimistic review conflicts.
- Test SSE disconnect/replay and polling fallback.
- Test migration upgrade/downgrade and backup/restore.

## Non-goals for Phase 1

- Authentication and cloud deployment are not required to fix reload persistence, though actor
  fields are retained for future authorization.
- Cross-case search waits until case isolation and permissions are correct.
- Browser-only persistence is explicitly rejected because it cannot safely own background work.
