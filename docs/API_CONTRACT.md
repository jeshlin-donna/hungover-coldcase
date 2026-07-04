# API Contract (frontend ⇄ backend)

Benjy builds against the **mock JSON** in `frontend/mock/` and the **stdlib mock server**
(`python scripts/mock_server.py`, no pip needed). Sam's FastAPI implements these exact
shapes so swapping mock → real is a one-line base-URL change.

Base URL: `http://localhost:8000`. All responses JSON. CORS open in dev.

> **Planned v2 case-scoped contract:** the endpoints below are currently session/global APIs.
> The durable replacement—`/cases`, case evidence, jobs, SSE progress, and migration rules—is in
> [`CASE_PERSISTENCE_PLAN.md`](CASE_PERSISTENCE_PLAN.md). V2 resolves Cognee datasets from
> `case_id`; clients will not submit arbitrary dataset names.

## V2 durable case APIs (implemented)

- `POST /cases`, `GET /cases`, `GET/PATCH /cases/{case_id}` — durable case lifecycle.
- `POST /cases/{case_id}/evidence` — persist a multipart batch and queue analysis; returns `202`.
- `GET /cases/{case_id}/evidence` — complete reload snapshot of evidence and jobs.
- `POST /cases/{case_id}/evidence/{evidence_id}/confirm` — save review revision and queue ingestion.
- `PATCH /cases/{case_id}/evidence/{evidence_id}/draft` — optimistic, reload-safe review drafts.
- `POST /cases/{case_id}/evidence/{evidence_id}/retry|cancel` — durable recovery controls.
- `DELETE /cases/{case_id}/evidence/{evidence_id}` — guarded removal; ingested evidence rebuilds the case dataset.
- `GET /cases/{case_id}/jobs` — polling/reconciliation snapshot.
- `GET /cases/{case_id}/events` — replayable SSE events (`Last-Event-ID`/`after`) with polling fallback.
- `GET /cases/{case_id}/stats|graph|chat/suggestions` and `POST /cases/{case_id}/chat` — isolated case tools.
- `POST /cases/{case_id}/reindex` — rebuild the case's Cognee dataset from confirmed evidence records and invalidate the derived graph cache.
- `POST /cases/{case_id}/archive|restore` and `DELETE /cases/{case_id}` — lifecycle controls.
- Case-scoped `timeline`, `contradictions`, `report`, `hunch`, `resolve`, `interrogation`, and `whatif` routes.

Evidence and job state is stored in application SQLite; original files are stored beneath the
case ID. Analysis jobs recover to `queued` after an interrupted backend process. Cognee dataset
names are immutable UUID-derived values held by the server.
Uploads stream through bounded temporary storage (25 MB/file, 50 files and 250 MB/batch by
default). SHA-256 duplicates within a case are reported and skipped instead of reprocessed.

`GET /cases/{case_id}/graph` returns semantic case, person, location, vehicle, and evidence nodes.
Files are provenance on nodes/edges rather than document nodes. Relationships are typed factual
claims (`occurred_at`, `observed_near`, `examined`, etc.); mere co-occurrence never creates an
edge. The result is cached by graph revision. `timeline`, `chat`, `interrogation`, and `whatif`
consume the same case analysis. When Cognee recall fails, responses use `mode: "derived"` rather
than returning demo content or failing silently.

---

### `GET /graph`
The case web for the force-graph view.
```json
{
  "nodes": [{"id": "tool:pry-8mm", "label": "Pry bar (8mm, left nick)", "type": "tool"}],
  "edges": [{"source": "case:MH-0312", "target": "tool:pry-8mm", "relation": "tool_used"}],
  "mode": "live"
}
```
`type` ∈ `case | tool | vehicle | mo | suspect | jurisdiction | alibi | receipt | evidence`.
Frontend colors by `type`. After a successful `POST /ingest-file`, the graph also includes
a session evidence node whose `id` matches the upload response's `graph_node_id`. The curated
graph/edges are always returned as-is (the reliable demo visual — never blocked by a live
call failing). In LIVE mode the response additionally carries a `cognee_insight` string from
a real Cognee `TRIPLET_COMPLETION` ("insights") query over the same case data, plus
`"mode": "live"`; if that live call errors, `mode` stays `"degraded"` and a
`cognee_insight_error` field is included instead — the curated graph itself is unaffected.

### `GET /timeline`
```json
{"events": [{"date": "2023-03-03", "case": "MH-2023-0312", "jurisdiction": "Maple Heights",
             "title": "Burglary — 14 Maple Heights Dr", "summary": "Rear slider, cam obscured."}]}
```

### `GET /recall/compare?query=...`
The 3-way split-screen. `sources` are doc IDs; `connects` is the set of cases the answer
actually linked (drives the "only graph connected both jurisdictions" highlight).
```json
{
  "query": "Is there forensic evidence linking Maple Heights and Riverside?",
  "results": {
    "naive_vector":  {"answer": "...", "sources": ["MH-0312-FOR"], "connects": ["MH-2023-0312"], "latency_ms": 120},
    "cognee_vector": {"answer": "...", "sources": ["MH-0312-FOR","MH-0102-FOR"], "connects": ["MH-2023-0312"], "latency_ms": 340},
    "cognee_graph":  {"answer": "...", "sources": ["MH-0312-FOR","RV-0788-FOR"], "connects": ["MH-2023-0312","RV-2023-0788"], "latency_ms": 410}
  }
}
```

### `POST /recall`  `{ "query": "...", "mode": "graph|vector|insights" }`
→ `{ "mode": "...", "answer": "...", "sources": ["..."], "latency_ms": 0 }`

### `POST /hunch`  `{ "text": "...", "session_id": "case-001" }`
→ `{ "ok": true }`  (detective's in-session note → Cognee session memory)

### `POST /resolve`  `{ "session_ids": ["case-001"] }`
Runs `improve()`. Returns the **before/after** so the UI can animate the metric climbing.
```json
{"ok": true, "metric": "recall@3 on multi-hop", "before": 0.42, "after": 0.71, "mode": "degraded"}
```
In LIVE mode, `before`/`after` are real recall@3 scores measured by running a fixed
multi-hop probe query (alibi vs. physical evidence) through `recall(mode=GRAPH)` immediately
before and after the real `improve()` call — the same measurement method as
`benchmark/benchmark_improve.py`'s q17 case — and `mode` is `"live"`. `improve()` always
runs regardless of whether the probe measurement succeeds; if either probe call fails, the
static demo numbers are returned instead with `"mode": "improve-ok-metric-degraded"` to make
clear the resolution itself still completed.

### `POST /expunge`  `{ "dataset": "case:RV-0788" }`
Runs `forget()`. Returns which nodes vanished + the post-deletion graph (unrelated nodes
stay) so the UI can animate the subgraph removal.
```json
{"ok": true, "removed": ["case:RV-0788","RV-0788-FOR"], "graph": { "nodes": [], "edges": [] }}
```

### `GET /benchmark`
Serves `benchmark/results.json` for the in-app benchmark chart.

### `POST /ingest-file/analyze`
Accepts multipart fields `file` and optional `context`. This extracts
or generates reviewable text but does not write to Cognee. The response includes `review_id`,
`extracted_text`, and `requires_confirmation: true`.

### `POST /ingest-files/analyze`
Accepts repeated multipart `files` fields and a `contexts` JSON array with one optional context entry per file.
Returns `{ "results": [...] }` in the same order, with independent success/error states. Media
analysis runs with bounded concurrency so a large drop does not overload the local model.

### `POST /ingest-file/confirm`
Accepts JSON `{ "review_id": "...", "extracted_text": "edited, verified text", "context": "..." }`.
Only this confirmation step calls `remember()` and adds the evidence node to the graph.

### `POST /ingest-files/confirm`
Accepts `{ "items": [{ "review_id", "extracted_text", "context" }] }`. Items are cognified
sequentially to respect the embedded graph database's single-writer constraint. Failed items do
not roll back successful siblings and remain available for correction/retry.

### `POST /ingest-file`
Compatibility endpoint for plain text files, which can be ingested directly.
```json
{
  "ok": true,
  "filename": "case-note.txt",
  "size_bytes": 148,
  "dataset": "coldcases",
  "mode": "live",
  "type": "text",
  "description": null,
  "graph_node_id": "evidence:upload-1"
}
```

### `GET /chat/suggestions`
Returns three questions generated from the active case graph. The UI uses generic prompts only
when no live case graph is available.

### `POST /chat`
Accepts `{ "message": "...", "history": [...] }`. In live mode, both the latest question and
recent conversation context are passed to graph completion; conversation text is never treated
as case evidence.
