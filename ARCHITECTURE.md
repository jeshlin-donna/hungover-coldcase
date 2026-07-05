# ColdCache Architecture — How Everything Actually Works

This document describes the **current merged repo**. The important architectural fact is that
ColdCache now has **two coexisting backends in one FastAPI app**:

1. a **primary case-scoped workspace** used by the current frontend
2. a **legacy/global demo surface** retained for benchmark, mock-server parity, and the narrated demo

> Scope note: this document describes the code as it exists now, not the pre-merge plan.

---

## 1. High-level system map

```text
React case UI (frontend/src/App.jsx)
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
FastAPI (backend/main.py)
  ├─ /cases*                       current app API
  ├─ /health                       mode + fallback state
  ├─ /ready                        storage + database readiness
  ├─ /graph /recall /report ...    legacy/global demo API
  ├─ multimodal extractors
  └─ durable job worker
          │
          ├─ application SQLite + file store (backend/case_store.py)
          │    ├─ $COLDCACHE_DATA_DIR/coldcache.db
          │    └─ $COLDCACHE_DATA_DIR/cases/<case_id>/...
          │
          ├─ persisted derived analysis (backend/case_analysis.py)
          │
          └─ Cognee wrapper (backend/memory_service.py)
               ├─ remember / cognify
               ├─ recall / search
               ├─ improve
               └─ forget
```

---

## 2. Current data model

### 2.1 Durable case workspace

The current frontend is case-scoped. Each case has:
- metadata in `cases`
- uploaded evidence in `evidence_items`
- immutable review history in `evidence_revisions`
- analysis/ingestion/reindex jobs in `jobs`
- replayable progress events in `job_events`
- cached derived analysis in `case_analyses`

All of this is application-owned in `backend/case_store.py`, not delegated to Cognee.

### 2.2 Per-case Cognee dataset

Each case gets an immutable dataset name of the form:
```text
case_<uuid_without_dashes>
```

The UI never chooses dataset names directly; `backend/main.py` resolves them server-side from `case_id`.

### 2.3 Legacy/global dataset

The benchmark, narrated demo, and older global routes still use:
```text
coldcases
```

That dataset is populated by `scripts/ingest.py` and is separate from the current case database/UI.

---

## 3. Ingestion pipeline — current case workflow

### 3.1 Upload and durable staging

`POST /cases/{case_id}/evidence`:
1. streams each upload into a bounded temp file under `data/upload_tmp/`
2. hashes while streaming
3. enforces size/count limits
4. atomically moves the file into `$COLDCACHE_DATA_DIR/cases/<case_id>/originals/`
5. inserts `evidence_items` + an `analyze` job in SQLite
6. returns immediately with durable IDs

Duplicates are detected by SHA-256 **within the same case** and returned as `duplicate_skipped: true`.

### 3.2 Background analysis

A startup worker in `backend/main.py` continuously:
- claims queued jobs transactionally
- assigns a 45s renewable lease
- heartbeats while running
- emits append-only `job_events`
- recovers expired `running` jobs back to `queued`

### 3.3 Review and confirmed ingestion

After analysis, evidence enters `awaiting_review`.

The investigator can:
- edit `reviewed_text`
- save optimistic drafts via `PATCH /cases/{case_id}/evidence/{evidence_id}/draft`
- confirm via `POST /cases/{case_id}/evidence/{evidence_id}/confirm`

Confirmed content is wrapped by `case_analysis.knowledge_packet()` before Cognee sees it, so the packet includes:
- `CASE_ID`
- `EVIDENCE_ID`
- source filename
- modality
- investigator context
- reviewed text
- provenance instructions

### 3.4 `remember()` / `cognify()` path

`backend/memory_service.py` still exposes the Cognee lifecycle through:
- `remember()` → `cognee.add()` + `cognify()`
- `cognify()` → typed extraction with `ColdCaseGraph`

If Groq-backed extraction fails, ColdCache retries against local Ollama. If typed local extraction also fails, it drops to untyped extraction rather than hard-failing the ingest.

---

## 4. Query pipeline — current case workflow

### 4.1 Persisted derived analysis

Current case tools do **not** rely exclusively on Cognee high-level completions.

`backend/case_analysis.py` builds and caches a deterministic, source-grounded analysis per:
```text
(case_id, graph_revision)
```

It extracts:
- people
- locations
- vehicles
- evidence items
- typed edges with filename provenance
- dated/timed events for the timeline

This payload powers:
- `GET /cases/{id}/graph`
- `GET /cases/{id}/timeline`
- fallback answers for chat/interrogation/what-if/report
- deterministic suggestions

### 4.2 Direct case-tool completion

For current case tools, `backend/main.py` uses `_case_llm_answer()` — a compact OpenAI-compatible completion over the persisted analysis, not a raw high-level Cognee completion.

Why:
- faster than Cognee's session-context wrappers for simple UI tasks
- bounded (`LLM_CASE_MAX_TOKENS=1600` by default, `timeout=45`)
- degrades cleanly to deterministic answers when no live provider is available

### 4.3 Cognee recall fallback

`backend/memory_service.py` still powers legacy/global recall and any direct Cognee lookups.

`recall()` now:
- maps app modes to `SearchType`
- detects hard Groq failures
- also detects degraded replies like `"Got it."`
- swaps Cognee's global LLM config to local Ollama
- retries once
- restores the original config afterward

This is serialized behind a lock because Cognee's LLM config is global.

---

## 5. Multimodal extraction pipeline (`backend/main.py`)

| Modality | Extractor | Current behavior |
|---|---|---|
| Image | `describe_image()` | Groq vision → local Ollama vision → Claude last resort |
| Audio | `transcribe_audio()` | Groq Whisper → local Whisper |
| Video | `extract_video_description()` | frame sampling + image extractor |
| PDF | `extract_pdf_content()` | text extraction; scanned pages go through image extractor |
| Spreadsheet | `parse_spreadsheet()` | `pandas` summary |
| Text | direct decode | passthrough |

The important post-merge nuance: multimodal extraction now tries hard **not to fail closed** when Groq is unavailable.

---

## 6. Health and fallback reporting

`GET /health` now returns:
- backend mode: `live` or `degraded`
- persistent case count
- case DB filename
- fallback state:
  - `active`
  - `last_reason`
  - `last_at`

This reflects real Groq→local fallback activity from `backend/main.py` / `backend/memory_service.py`.

---

## 7. The two API surfaces

### 7.1 Primary current app API

Used by the current frontend:
- `/cases`
- `/cases/{case_id}`
- `/cases/{case_id}/evidence`
- `/cases/{case_id}/jobs`
- `/cases/{case_id}/events`
- `/cases/{case_id}/stats`
- `/cases/{case_id}/graph`
- `/cases/{case_id}/reindex`
- `/cases/{case_id}/chat`
- `/cases/{case_id}/chat/suggestions`
- `/cases/{case_id}/timeline`
- `/cases/{case_id}/contradictions`
- `/cases/{case_id}/report`
- `/cases/{case_id}/hunch`
- `/cases/{case_id}/resolve`
- `/cases/{case_id}/interrogation`
- `/cases/{case_id}/whatif`

### 7.2 Legacy/global API

Still present in `backend/main.py` for demo/benchmark compatibility:
- `/graph`, `/graph/temporal`, `/stats`, `/case-name`
- `/timeline`, `/contradictions`, `/benchmark`
- `/recall/compare`, `/recall`, `/hunch`, `/resolve`, `/expunge`
- `/missing-hours`, `/nexus`, `/interrogation`, `/whatif`
- `/chat`, `/chat/suggestions`, `/report`, `/suspect-timeline`
- `/transcribe`, `/ingest-file/analyze`, `/ingest-files/analyze`, `/ingest-file/confirm`, `/ingest-files/confirm`, `/ingest-file`

The merged frontend mainly uses the first set.

---

## 8. Reindexing and deletion behavior

### 8.1 Case reindex

`POST /cases/{case_id}/reindex` creates a durable `reindex` job that:
- builds a replacement dataset from confirmed evidence
- only activates it after success
- bumps `graph_revision`
- invalidates cached derived analysis atomically

### 8.2 Evidence deletion

Deleting already-ingested evidence is handled safely:
- non-ingested evidence is deleted directly
- ingested evidence triggers a case dataset rebuild path rather than a brittle surgical delete

### 8.3 Case deletion

Deleting a case:
- rejects active work
- expunges the case dataset when live
- removes app-owned records and files

---

## 9. Frontend architecture (`frontend/src/`)

`App.jsx` now behaves as a case workspace shell:
- no default hero-case landing page
- open/create/archive/delete cases in `CaseHome`
- enter upload/review flow first for empty cases
- open directly to the Evidence Board for cases that already have evidence
- render chat in a persistent right-hand aside

### Components currently mounted by `App.jsx`

| Component | Role |
|---|---|
| `CaseHome.jsx` | case list, create form, archive/restore/delete |
| `CaseImportPanel.jsx` | upload queue, SSE+poll refresh, review/confirm/retry/cancel |
| `GraphPanel.jsx` | case-scoped evidence board + rebuild action |
| `CaseTimelinePanel.jsx` | derived case timeline |
| `CaseInterrogationPanel.jsx` | case-scoped questioning assistant |
| `CaseWhatIfPanel.jsx` | case-scoped hypothesis sandbox |
| `ChatPanel.jsx` | case chat |

### Components still in repo but not part of the main shell

Several older single-workspace demo panels remain in `frontend/src/components/` for legacy/demo compatibility, but they are no longer the dominant app architecture.

---

## 10. Legacy/global helpers worth knowing about

### `/case-name`

The backend still exposes `GET/POST /case-name`, and `_get_case_label()` still supports:
- manual override via `POST /case-name`
- auto-generated short labels from ingested legacy evidence
- curated demo default when no evidence exists

However, the current frontend does **not** call these endpoints. The active case label in the main UI comes from the selected case's stored title.

### Global `/graph` and `/stats`

The live-stats fix landed on the legacy/global graph surface:
- `docs_ingested` now uses real backend counts
- `case_label` comes from `_get_case_label()`

That behavior is accurate for the old global demo routes, not the current case-scoped stats ribbon.

---

## 11. Running the right thing for the right purpose

Use this split to avoid confusion:

| Goal | Use |
|---|---|
| current UI / durable cases | create cases in the frontend and upload evidence |
| benchmark / narrated demo | `scripts/generate_corpus.py`, `scripts/ingest.py`, `demo/demo.py` |
| frontend-only work | `scripts/mock_server.py` |
