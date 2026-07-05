# Cognee API Notes — VERIFIED against source + current ColdCache integration

> Source of truth for SDK signatures: `github.com/topoteretes/cognee` @ `main`, `cognee/api/v1/*`.
> Source of truth for app behavior: `backend/memory_service.py` and `backend/main.py` in this repo.

| Question | Verified answer |
|---|---|
| `SearchType` import path | `from cognee import SearchType` works in the pinned version; ColdCache keeps a defensive import loop for compatibility |
| `INSIGHTS` enum member | **Does not exist** in this Cognee version; ColdCache maps its `insights` mode to `TRIPLET_COMPLETION` |
| `add` | `await cognee.add(data, dataset_name="...")` |
| `cognify` | `await cognee.cognify(datasets=[...], ...)` and it is synchronous by default |
| `search` | `await cognee.search(query_text, query_type=SearchType..., datasets=[...])` |
| `recall` | `await cognee.recall(query_text, datasets=[...], ...)` |
| `remember` | high-level helper exists, but ColdCache intentionally uses `add()` + `cognify()` for dataset control |
| `improve` | meaningful when given `session_ids` |
| `forget` | `forget(dataset="x")` deletes that dataset |

---

## ColdCache-specific integration notes

### 1. Case-scoped UI vs legacy global dataset

The current frontend is **case-scoped** and server-resolves dataset names from `case_id`.

The old narrated demo / benchmark still targets the legacy global dataset:
```text
coldcases
```

Do not assume that `scripts/ingest.py` populates the current case home. It only fills the legacy/global path.

### 2. Recall output handling

Cognee search/recall result shapes vary enough that ColdCache now extracts answer text defensively in `_extract_answer_text()`.

Notable real shape handled by the code:
```python
[{"dataset_id": ..., "dataset_name": ..., "search_result": ["answer text"]}]
```

This is why endpoints no longer stringify whole dicts into user-facing `answer` fields.

### 3. Groq → local Ollama fallback for Cognee

`memory_service.recall()` and `memory_service.cognify()` now have production logic beyond the raw SDK call:

- detect hard Groq failures
- detect degraded Cognee replies such as `"Got it."`
- temporarily swap Cognee's global LLM config to local Ollama
- retry once
- restore the original config afterward

Relevant env vars:
- `OLLAMA_ENDPOINT`
- `OLLAMA_TEXT_MODEL`
- `COLDCACHE_RECALL_TIMEOUT_S`
- `COLDCACHE_FALLBACK_TIMEOUT_S`
- `COLDCACHE_LOCAL_FALLBACK_TIMEOUT_S`
- `COLDCACHE_LLM_RETRY_FLOOR_S`
- `CACHING=false`

### 4. Cognee retry-floor monkeypatch

Cognee hardcodes a 240-second retry delay floor for structured-output LLM retries. ColdCache mutates the underlying stop object in place so the fallback path can trigger in seconds instead of minutes.

Default in this repo:
```text
COLDCACHE_LLM_RETRY_FLOOR_S=8
```

### 5. Recall cache

ColdCache keeps a best-effort recall cache on disk for repeated identical legacy/global queries.

Relevant env vars:
- `COLDCACHE_CACHE_DIR`
- `COLDCACHE_DISABLE_RECALL_CACHE`

---

## Multimodal ingestion notes

### Current behavior in `backend/main.py`

| Function | Current fallback order |
|---|---|
| `describe_image()` | Groq vision → local Ollama vision (`OLLAMA_VISION_MODEL`) → Claude last resort |
| `transcribe_audio()` | Groq Whisper (`LLM_TRANSCRIPTION_MODEL`) → local Whisper |

This is newer than the original repo docs, which described a single-provider path.

### PDF/video/image pipeline

- image uploads go through `describe_image()`
- video uploads sample frames, then reuse `describe_image()`
- scanned PDF pages also reuse `describe_image()`

So the same Groq→local fallback chain now covers all of those modalities.

---

## Local-model caveat still worth knowing

Cognee typed ingestion works more reliably than some high-level interactive completion paths on smaller local models. That is one reason the current case tools lean on persisted derived analysis plus a compact direct completion in `backend/main.py`, instead of routing every UI interaction through Cognee's higher-level completion wrappers.

---

## Backend startup behavior

`backend/main.py` loads the repo `.env` itself before deciding `LIVE` vs `DEGRADED`, so:
```bash
uvicorn backend.main:app --port 8000
```
is enough once `.env` is configured.

`GET /health` is the fastest way to confirm:
- whether the backend is live
- how many cases exist
- whether fallback was recently activated

For hosting probes use `GET /ready`; it also verifies the configured `COLDCACHE_DATA_DIR` is writable and SQLite is reachable.
