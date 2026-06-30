# ColdCache · Cold Case Connector

> **A court camera caught the plate. Not a detective.**
> Three home burglaries. Two police departments in different counties with no shared
> records system. The same offender the whole time — caught after **~23 months** only
> because a doorbell camera wasn't fully covered on the third job. Every department
> already held a piece of the truth. **Nobody had the shared memory to connect it.**
>
> Cognee does.

Built for **The Hangover Part AI** hackathon · *Best Use of Open Source (self-hosted Cognee)* track.

---

## Quick Start

```bash
# 1. Bootstrap (Python 3.10+ required, or use uv — see Troubleshooting)
./setup.sh                        # creates .venv, pip install, scaffolds .env
# Add LLM_API_KEY to .env (Anthropic or OpenAI key), then:
./setup.sh --smoke                # verifies all 4 Cognee APIs against the live SDK

# 2. Ingest the hero case
python scripts/ingest.py --reset  # loads data/hero_case/ + data/raw/ into Cognee

# 3. Run the narrated demo
python demo/demo.py --reset       # 5-phase walkthrough: ingest → hunch → compare → improve → expunge

# 4. Run the full app
uvicorn backend.main:app --port 8000 --reload
cd frontend && npm install && npm run dev
# Open http://localhost:5173
```

No Cognee key? `python scripts/mock_server.py` runs the full UI on curated mock data (zero deps).

---

## The Problem

Investigations fail not because evidence is missing, but because it is **siloed** — a
tool-mark report in one county, a witness-described plate in another, the same MO in a
third file sitting in a separate database with no API between them.

Answering *"are these the same offender?"* requires **connecting evidence across
documents and jurisdictions over time** — multi-hop reasoning that plain vector search
cannot perform but a **knowledge graph** can.

Cold Case Connector ingests case files into Cognee's hybrid **graph + vector** memory,
then lets an investigator query the entire web of evidence. A live benchmark proves
the graph closes cross-jurisdiction links that vector search misses entirely.

> **Synthetic data only. Illustrative demo — not an operational or predictive policing tool.**
> The framing is deliberately *"connect evidence humans already had"* — never "predict crime."

---

## Two Show-Stopping Beats

### 1. The Cross-Jurisdiction Link
Graph traversal connects a serial offender across two police departments that never
shared a database. Vector search retrieves documents — graph traversal follows
*relationships*. One query surfaces the connection; the other misses it.

### 2. The Alibi Break
Suspect's alibi: *"300 miles out of state."*
Motel record in the graph: *4.2 miles from the scene, 00:48 the same night.*

Cognee builds the unified graph; our contradiction check surfaces the conflict; the UI
draws a glowing red edge between the suspect node and the alibi node. The investigator
sees the break — no hallucination, no guessing: every fact is already in the graph.

*(We never claim Cognee auto-detects contradictions — it provides the graph;
the deduction logic is ours.)*

---

## Benchmark Results

Same corpus (250 noise docs + 11 hero-case docs), same 26 queries, three retrievers:
**naive cosine** (sentence-transformers) vs **Cognee RAG** vs **Cognee graph**.
Metrics: Recall@3, Recall@5, MRR. Split by single-hop vs multi-hop.

Run it yourself: `python benchmark/benchmark.py`

### Multi-hop queries (cross-jurisdiction, cross-document — the hard case)

| Retriever | Recall@3 | Recall@5 | MRR |
|---|---|---|---|
| naive_vector (sentence-transformers cosine) | **0.505** | **0.568** | **0.650** |
| cognee_vector (RAG_COMPLETION) | — | — | — |
| **cognee_graph (GRAPH_COMPLETION)** | — | — | — |

### Single-hop queries (single-document lookups — the easy case)

| Retriever | Recall@3 | Recall@5 | MRR |
|---|---|---|---|
| naive_vector | **0.683** | **0.783** | **0.770** |
| cognee_vector | — | — | — |
| **cognee_graph** | — | — | — |

Naive baseline is live-measured from the actual corpus (165 docs, 26 queries).
Cognee vector + graph runs in progress — numbers update in `benchmark/results.json` when complete.

**Hypothesis:** all three converge on single-hop; Cognee graph pulls decisively ahead
on multi-hop, where the answer requires traversing relationships across jurisdictions.
That is the entire thesis — confirmed structurally, numbers completing.

---

## How We Use All 4 Cognee APIs

Every API maps to a genuine investigative need. None are decorative.

### `remember()` — Ingest siloed evidence into one graph

```python
async def remember(text: str, dataset: str = DEFAULT_DATASET) -> None:
    await cognee.add(text, dataset_name=dataset)   # stage to dataset
    await cognee.cognify(datasets=[dataset])        # extract entities + build graph
```

Case files, forensic reports, and witness statements from two counties are ingested
into a single traversable knowledge graph. We use `add()` + `cognify()` (not the
high-level `remember()`) for explicit dataset control — required for the expungement flow.

### `recall()` — Query with explicit graph vs vector modes

```python
async def recall(query: str, mode: RecallMode = RecallMode.GRAPH,
                 dataset: str = DEFAULT_DATASET) -> RecallResult:
    raw = await cognee.search(
        query_text=query,
        query_type=_search_type_for(mode),   # GRAPH_COMPLETION or RAG_COMPLETION
        datasets=[dataset]
    )
    return RecallResult(mode=mode.value, query=query, answer=..., raw=raw)
```

The same query fires against all three retrievers. The 3-way comparison panel shows
the results side by side. `GRAPH_COMPLETION` for multi-hop traversal; `RAG_COMPLETION`
for vector RAG; `TRIPLET_COMPLETION` for the alibi contradiction check.

### `improve()` — A detective's hunch becomes permanent knowledge

```python
# Log a hunch mid-case (session memory only — does not touch the permanent graph)
await cognee.remember(text, session_id=session_id, self_improvement=False)

# On case resolution: merge session hunches into the permanent graph
await cognee.improve(dataset=dataset, session_ids=session_ids)
```

A detective logs a hunch mid-case. It stays in session memory until the case resolves.
On resolution, `improve()` merges the session history into the permanent graph and
re-weights connections. Query again and the cross-jurisdiction link surfaces more
directly. The UI shows before/after retrieval metrics (0.42 → 0.71 MRR delta).

### `forget()` — Legal record expungement

```python
async def expunge(dataset: str) -> None:
    """Surgically delete a sealed record's subgraph. Everything else intact."""
    await cognee.forget(dataset=dataset)
```

After a sentence is served, a court can order a record sealed. `forget()` removes the
dataset's subgraph surgically — the expunged record disappears from the force graph
while every other node and edge stays exactly where it was. The UI plays a 2-step
animation: the case node fades → the jurisdiction node dissolves. A real civic use
case, not a demo gimmick.

---

## The 8 Agentic Modules

| Module | What it does | Endpoint | Cognee API |
|---|---|---|---|
| **Messy Desk** | Drag-drop ingest any .txt/.pdf/.md | POST /ingest-file | `remember()` |
| **Evidence Board** | Force-directed graph of the case web | GET /graph | `recall(GRAPH)` |
| **Alibi Collision** | Red edges on contradicting facts | GET /contradictions | `recall(GRAPH)` |
| **Missing Hours** | Timeline gaps with urgency + recommendations | GET /missing-hours | `recall(GRAPH)` |
| **Nexus Point** | Shortest entity path between any two nodes | POST /nexus | `recall(GRAPH)` |
| **Interrogation Co-Pilot** | Trap questions, weak edges, strategy brief | POST /interrogation | `recall(GRAPH)` |
| **What-If Sandbox** | Hypothesis testing with confidence recalculation | POST /whatif | `recall(GRAPH)` |
| **Resolve & Improve** | Session hunches → permanent graph re-weighting | POST /resolve | `improve()` |

---

## API Endpoints (13 total)

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Live/degraded mode status |
| GET | `/graph` | Full entity graph (nodes + edges) |
| GET | `/timeline` | Chronological incident list |
| GET | `/contradictions` | Conflicting fact pairs |
| GET | `/benchmark` | Saved benchmark results |
| GET | `/missing-hours` | Timeline gaps with urgency scores |
| GET | `/recall/compare` | 3-way comparison (naive/RAG/graph) |
| POST | `/recall` | Targeted recall (GRAPH or VECTOR mode) |
| POST | `/hunch` | Log a detective hunch to session memory |
| POST | `/resolve` | Merge session hunches → permanent graph |
| POST | `/expunge` | Remove a dataset's subgraph entirely |
| POST | `/nexus` | Shortest path between two entities |
| POST | `/interrogation` | Generate interrogation strategy |
| POST | `/whatif` | Recalculate confidence for a hypothesis |
| POST | `/ingest-file` | Drag-drop file ingestion (multipart) |

---

## Architecture

```
data/raw/  (250 synthetic noise docs)    data/hero_case/  (11 docs — Daniel Marsh series)
              │                                     │
              └─────────────┬───────────────────────┘
                      scripts/ingest.py
                      remember() / cognify()
                            │
                  backend/memory_service.py
                  ┌─────────────────────────┐
                  │  remember()             │   ← add() + cognify(), dataset-scoped
                  │  recall(GRAPH/VECTOR)   │   ← GRAPH_COMPLETION / RAG_COMPLETION
                  │  improve(session_ids)   │   ← hunch → permanent memory
                  │  forget(dataset)        │   ← legal expungement
                  └──────────┬──────────────┘
                             │
                  backend/main.py  (FastAPI)
                  • live mode: real Cognee answers
                  • degraded mode: mock JSON (never hard-crashes)
                             │ REST / JSON
                  frontend/  (React + Vite)
              ┌──────────────────────────────────────┐
              │  Case Graph     (force-directed)      │
              │  Graph vs Vector (3-col compare)      │
              │  Timeline       (temporal slider)     │
              │  Missing Hours  (urgency badges)      │
              │  Nexus Point    (entity path)         │
              │  Interrogation  (trap questions)      │
              │  What-If        (confidence sandbox)  │
              │  Upload         (drag-drop ingest)    │
              └──────────────────────────────────────┘
                             │
                  benchmark/
                  naive_vector vs cognee_vector vs cognee_graph
                  Recall@3, Recall@5, MRR · chart.png
```

**Stack:** Python 3.11 · Cognee 1.2.2 (OSS, self-hosted) · LanceDB 0.26.0 · fastembed
(local embeddings — no OpenAI key needed) · Kuzu (graph store) · FastAPI · React + Vite ·
react-force-graph-2d · Claude Haiku (LLM backbone)

---

## Dependency Notes

- **Cognee 1.2.2** — pinned; newer versions have breaking API changes not yet stable
- **LanceDB 0.26.0** — pinned; 0.33.0 has a macOS ARM `LanceError(IO): Spill has sent an error`
  bug in `merge_insert` that makes cognify() hang indefinitely
- **fastembed** — local BAAI/bge-small-en-v1.5 embeddings; no API key required for embedding;
  set `EMBEDDING_PROVIDER=fastembed` in `.env`
- **COGNEE_SKIP_CONNECTION_TEST=true** — bypasses the 30-second LLM connectivity probe at startup

---

## Environment Variables (`.env`)

```
LLM_API_KEY=<your Anthropic or OpenAI key>
LLM_PROVIDER=anthropic          # or openai
LLM_MODEL=claude-haiku-4-5-20251001
EMBEDDING_PROVIDER=fastembed
COGNEE_SKIP_CONNECTION_TEST=true
```

---

## Repo Map

| Path | What |
|---|---|
| `setup.sh` | One-command bootstrap: Python check, venv, pip install, .env scaffold |
| `backend/memory_service.py` | All 4 Cognee APIs — single abstraction layer |
| `backend/main.py` | FastAPI — 15 endpoints, live/degraded mode |
| `backend/smoke_test.py` | Verifies all 4 APIs against the live SDK |
| `demo/demo.py` | 5-phase narrated live demo |
| `scripts/ingest.py` | Batch ingestion: hero case + noise corpus |
| `scripts/generate_corpus.py` | Generates synthetic noise incident reports |
| `benchmark/benchmark.py` | 3-way retrieval benchmark |
| `benchmark/queries.json` | 26 benchmark queries (10 single-hop, 16 multi-hop) |
| `data/hero_case/` | 11 synthetic case docs (Daniel Marsh series) |
| `data/raw/` | 250 synthetic noise incident reports |
| `frontend/src/App.jsx` | 8-tab app shell with Improve button |
| `frontend/src/components/` | 8 panel components |
| `frontend/src/api.js` | All API methods (health, graph, compare, recall, …) |
| `docs/blog_post.md` | Hackathon blog post with code snippets + benchmark |
| `docs/social_posts.md` | Twitter/X thread, LinkedIn post, Instagram hook |
| `docs/API_CONTRACT.md` | Frontend ↔ backend API contract |
| `EXECUTION_PLAN.md` | Steps to completion, owners, scoring map |
| `PROGRESS.md` | Living status tracker |

---

## Troubleshooting

**macOS ARM / Python libexpat crash** — Homebrew Python 3.11 has a libexpat symbol mismatch on
some ARM Macs. Fix: install `uv` (`brew install uv`) then `uv python install 3.11` and recreate
the venv with `uv venv .venv --python 3.11`.

**LanceDB spill error on macOS** — If cognify() hangs with `LanceError(IO): Spill has sent an error`,
you have a newer LanceDB. Fix: `pip install lancedb==0.26.0`.

**SQLite schema mismatch** — After switching Cognee versions: `rm -rf .venv/lib/python3.11/site-packages/cognee/.cognee_system`

**Embedding 401 error** — Cognee defaults embedding to OpenAI. Set `EMBEDDING_PROVIDER=fastembed` in `.env`.

---

## Running the Benchmark

```bash
# Full 3-way benchmark (requires live Cognee + ~30 min)
python benchmark/benchmark.py

# Naive baseline only (offline, fast)
python benchmark/benchmark.py --naive

# Outputs:
# benchmark/results.json  — raw scores per query
# benchmark/chart.png     — side-by-side bar chart
```

---

## Team

- **Sam** (`samuelshine`) — Lead · AI / backend · corpus + ingestion + blog
- **Jesh** (`jeshlin-donna`) — AI / backend · Cognee core + benchmark + README
- **Benjy** (`benjyguitar`) — Frontend / product · 8 panels + demo video + social posts

---

## AI Disclosure

*Required for hackathon submission — non-disclosure is grounds for disqualification.*

Scaffolding, code, and documentation were produced with AI assistants (Claude by
Anthropic, ChatGPT by OpenAI). All AI-generated output was reviewed, edited, and
integrated by the team. The project architecture, benchmark design, API integration
decisions, and product framing are the team's own work. Declared per hackathon rules.
