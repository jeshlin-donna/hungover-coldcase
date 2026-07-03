# API Contract (frontend ⇄ backend)

Benjy builds against the **mock JSON** in `frontend/mock/` and the **stdlib mock server**
(`python scripts/mock_server.py`, no pip needed). Sam's FastAPI implements these exact
shapes so swapping mock → real is a one-line base-URL change.

Base URL: `http://localhost:8000`. All responses JSON. CORS open in dev.

---

### `GET /graph`
The case web for the force-graph view.
```json
{
  "nodes": [{"id": "tool:pry-8mm", "label": "Pry bar (8mm, left nick)", "type": "tool"}],
  "edges": [{"source": "case:MH-0312", "target": "tool:pry-8mm", "relation": "tool_used"}]
}
```
`type` ∈ `case | tool | vehicle | mo | suspect | jurisdiction | alibi | receipt | evidence`.
Frontend colors by `type`. After a successful `POST /ingest-file`, the graph also includes
a session evidence node whose `id` matches the upload response's `graph_node_id`.

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
{"ok": true, "metric": "recall@3 on multi-hop", "before": 0.42, "after": 0.71}
```

### `POST /expunge`  `{ "dataset": "case:RV-0788" }`
Runs `forget()`. Returns which nodes vanished + the post-deletion graph (unrelated nodes
stay) so the UI can animate the subgraph removal.
```json
{"ok": true, "removed": ["case:RV-0788","RV-0788-FOR"], "graph": { "nodes": [], "edges": [] }}
```

### `GET /benchmark`
Serves `benchmark/results.json` for the in-app benchmark chart.

### `POST /ingest-file`
Accepts multipart form data with one `file` field. In LIVE mode, the backend extracts text
for the detected modality, calls `remember()`, and adds an evidence node to the session graph.
In DEGRADED mode, it returns the same response shape without writing to Cognee.
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
