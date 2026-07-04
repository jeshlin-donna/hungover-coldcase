# Cognee API Notes — VERIFIED against source

> Source of truth: `github.com/topoteretes/cognee` @ `main`, `cognee/api/v1/*`.
> Verified by reading the actual function definitions (no live key needed). The only item
> still flagged for a live keyed run is the runtime shape of recall/search results.

| Question | Verified answer |
|---|---|
| `SearchType` import path | `from cognee import SearchType` (re-exported from `cognee.api.v1.search`) |
| `SearchType` members | `SUMMARIES, CHUNKS, RAG_COMPLETION, HYBRID_COMPLETION, TRIPLET_COMPLETION, GRAPH_COMPLETION, GRAPH_COMPLETION_DECOMPOSITION, GRAPH_SUMMARY_COMPLETION, CYPHER, NATURAL_LANGUAGE, GRAPH_COMPLETION_COT, GRAPH_COMPLETION_CONTEXT_EXTENSION, FEELING_LUCKY, TEMPORAL, CODING_RULES, CHUNKS_LEXICAL, AGENTIC_COMPLETION` |
| ⚠️ `INSIGHTS`? | **Does NOT exist in this version.** Use `TRIPLET_COMPLETION` for relationships/triples. Its triplet embeddings must be created after `cognify()`; `memory_service.prepare_insights()` does this lazily on the first insights recall. (Old scaffold assumed INSIGHTS → would crash.) |
| `add` | `await cognee.add(data, dataset_name="main_dataset", ..., run_in_background=False)` |
| `cognify` | `await cognee.cognify(datasets=Union[str,list]=None, ..., run_in_background=False)` — **synchronous by default** |
| `search` | `await cognee.search(query_text, query_type=SearchType.GRAPH_COMPLETION, datasets=Optional[list|str], ...)` → `list[RecallResponse]` |
| `recall` | `await cognee.recall(query_text, query_type=None, *, datasets=None, top_k=15, auto_route=True, session_id=None, ...)` → `list[RecallResponse]` |
| `remember` | `await cognee.remember(data, dataset_name="main_dataset", *, session_id=None, run_in_background=False, self_improvement=True, session_ids=None, ...)`. No session_id → permanent (add+cognify). With session_id → session memory. |
| `improve` | `await cognee.improve(dataset="main_dataset", run_in_background=False, session_ids=Optional[List[str]])`. Real session→permanent bridging only when `session_ids` given. |
| `forget` | `await cognee.forget(data_id=None, dataset=None, dataset_id=None, everything=False, memory_only=False)`. `forget(dataset="x")` deletes the whole dataset; `memory_only=True` keeps raw files. |
| `datasets.get_status` | `await cognee.datasets.get_status([dataset_ids])` — takes **dataset UUIDs**, not names; returns `{id: {pipeline: status}}`. Not needed in the synchronous flow. |
| `prune` | `await cognee.prune.prune_data()` and `await cognee.prune.prune_system(graph=True, vector=True, metadata=False, cache=True)`. ColdCache's clean reset passes `metadata=True`; otherwise stale document metadata can deduplicate re-added files after the graph/vector stores have been deleted. |

The narrated demo and full benchmark stage their documents together, then call `cognify()`
with `data_per_batch=1` and `chunk_size=1200`. This keeps extraction serial and each
structured response inside the local Ollama model's context window; the default batch of
20 launches document extractions together and can stall a local run. It also avoids
rebuilding the whole growing graph after every document.
`ColdCaseNode` also normalizes a model-emitted `null` description to the empty string,
preserving Cognee's required string field without retrying an otherwise valid extraction.

## Backend startup behavior
`backend/main.py` loads the repository `.env` before deciding LIVE vs DEGRADED mode. The
documented `uvicorn backend.main:app --port 8000` command therefore uses the configured
`LLM_API_KEY` without requiring the user to export every variable into the shell first.

## Still to confirm on a live keyed run (one thing)
`recall()` / `search()` return `list[RecallResponse]`. Confirm what a `RecallResponse`
contains (answer text + source chunk/doc refs) so `benchmark.extract_ranked_ids` and
`backend/main.py extract_ids` map results → gold DOC_IDs cleanly. If results don't embed
the `DOC_ID:` strings, switch extraction to use the response's source/metadata fields.

## How these were verified
Read directly from source via `gh api` (tree) + `curl raw.githubusercontent.com`:
`api/v1/{add,cognify,search,recall/recall,remember/remember,improve/improve,forget/forget,
datasets/datasets,prune/prune}.py` and `modules/search/types/SearchType.py`.

## Multimodal ingestion — Vision model
Image, video (keyframe), and scanned-PDF ingestion all route through `describe_image()` in
`backend/main.py`. This calls the local **Ollama** vision endpoint — no cloud API key needed.

| Env var | Default | Purpose |
|---|---|---|
| `VISION_MODEL` | `llava:7b` | Ollama model with vision support |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |

To use a different vision model: `ollama pull <model>` then set `VISION_MODEL=<model>` in `.env`.
Supported alternatives: `moondream`, `minicpm-v`, `llava:13b`, `bakllava`.

The call goes to Ollama's `/api/chat` endpoint with the image base64-encoded in the `images` field.
All blocking I/O runs in `asyncio.to_thread()` so the FastAPI event loop is never blocked.
Timeout is 120 seconds (large images / first-load model warm-up can be slow).
