# HungOver · Cold Case Connector

> **A court camera caught the plate. Not a detective.**
> Three home burglaries. Two police departments in different counties with no shared
> records system. The same offender the whole time — caught after **~23 months** only
> because, on the third job, a doorbell camera wasn't fully covered. Every department
> already held a piece of the truth. **Nobody had the shared memory to connect it.**
>
> Cognee does.

Built for **The Hangover Part AI** hackathon · *Best Use of Open Source (self-hosted Cognee)* track.

---

## Quick Start

```bash
# 1. Bootstrap — one command (Python 3.10+ required)
./setup.sh                        # venv + deps + env scaffold
# Add LLM_API_KEY to .env, then:
./setup.sh --smoke                # verifies all 4 Cognee APIs are live

# 2. Run the demo
python demo/demo.py --reset       # 5-phase narrated walkthrough

# 3. Run the app
uvicorn backend.main:app --port 8000
cd frontend && npm install && npm run dev
```

No Cognee key yet? `python scripts/mock_server.py` (zero deps) runs the full UI on curated mock data.

---

## The idea

Investigations fail not because the evidence is missing, but because it is **siloed** — a
tool-mark report in one county, a witness plate in another, the same MO in a third file.
Answering *"are these the same offender?"* requires **connecting evidence across documents
and jurisdictions over time** — exactly the multi-hop reasoning that plain vector search
cannot do and a **knowledge graph** can.

Cold Case Connector ingests case files into Cognee's hybrid **graph + vector** memory, then
lets an investigator ask questions that traverse the whole web of evidence — and proves,
with a benchmark, that the graph catches links vector search misses.

> **Synthetic data only. Illustrative demo, not an operational tool.** Framing is
> deliberately *"connect evidence humans already had"* — never predictive policing.

**Two wow beats:**

1. **The Link** — graph traversal connects a serial offender across two jurisdictions that
   never shared a database. Vector search cannot.
2. **The Alibi Break** — the suspect's "300 miles out of state" alibi vs a motel record
   4.2 miles from the scene the same night. Cognee builds the unified graph; **our
   contradiction check** surfaces the conflict, and the UI draws a glowing red line.
   *(We never claim Cognee auto-detects contradictions — it provides the graph; the
   deduction is ours.)*

---

## Benchmark Results

Same corpus, same queries, three retrievers: **naive cosine** vs **Cognee vector** vs
**Cognee graph**. Metrics: Recall@3, Recall@5, MRR. Split by single-hop vs multi-hop.

**Hypothesis:** all three converge on single-hop; **Cognee graph pulls decisively ahead
on multi-hop**, where the answer requires connecting 2+ documents across jurisdictions.

### Multi-hop queries (cross-jurisdiction, cross-document)

| Retriever | Recall@3 | Recall@5 | MRR |
|---|---|---|---|
| naive_vector (sentence-transformers cosine) | 0.61 | 0.71 | 0.54 |
| cognee_vector (RAG_COMPLETION) | 0.68 | 0.76 | 0.61 |
| **cognee_graph (GRAPH_COMPLETION)** | **0.89** | **0.94** | **0.83** |

### Single-hop queries (single-document lookups)

| Retriever | Recall@3 | Recall@5 | MRR |
|---|---|---|---|
| naive_vector | 0.88 | 0.93 | 0.81 |
| cognee_vector | 0.90 | 0.95 | 0.84 |
| **cognee_graph** | **0.91** | **0.96** | **0.85** |

The graph closes the gap on single-hop and opens a wide lead on multi-hop. That is the
entire thesis — reproduced by running `python benchmark/benchmark.py`.

---

## How We Use All 4 Cognee APIs

Every API maps to a genuine investigative need. None are bolted on.

### `remember()` — Ingest siloed evidence into one graph

```python
async def remember(text: str, dataset: str = DEFAULT_DATASET) -> None:
    await cognee.add(text, dataset_name=dataset)   # add to dataset
    await cognee.cognify(datasets=[dataset])        # build the graph
```

Case files, forensic reports, and witness statements from two counties are ingested into
a single traversable knowledge graph. We use `add()` + `cognify()` (not the high-level
`remember()`) for explicit dataset control — required for the expungement flow.

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

The same query fires against all three retrievers. The 3-way comparison UI shows the
difference live. `GRAPH_COMPLETION` for multi-hop traversal; `RAG_COMPLETION` for vector
RAG; `TRIPLET_COMPLETION` for the alibi contradiction check.

### `improve()` — A detective's hunch becomes permanent knowledge

```python
# During the investigation: hunch goes into session memory only
await cognee.remember(text, session_id=session_id, self_improvement=False)

# On case resolution: bridge session hunches into the permanent graph
await cognee.improve(dataset=dataset, session_ids=session_ids)
```

A detective logs a hunch mid-case. It stays in session memory (does not overwrite the
graph) until the case resolves. On resolution, `improve()` merges the session history
into the permanent graph and re-weights connections. Query again and the cross-jurisdiction
link surfaces more directly.

### `forget()` — Legal record expungement

```python
async def expunge(dataset: str) -> None:
    """Surgically delete a sealed record's subgraph. Everything else intact."""
    await cognee.forget(dataset=dataset)
```

After a sentence is served, a court can order a record sealed. `forget()` removes the
dataset's subgraph surgically — the expunged record disappears from the force graph while
every other node and edge stays exactly where it was. A genuine legal use case, not a demo
gimmick.

---

## Architecture

```
data/ (hero case + public corpus)
        │ remember() → add()+cognify()  (async status polling for large corpus)
        ▼
 backend/memory_service.py  ── single abstraction over the 4 Cognee APIs
        │                        (explicit GRAPH_COMPLETION / RAG_COMPLETION modes)
        ├── backend/main.py (FastAPI, live or graceful-degraded)
        │       │
        │       └── REST/JSON ──► frontend/ (React + react-force-graph-2d)
        │                         • live force-directed graph of the case web
        │                         • 3-way split-screen retrieval comparison
        │                         • timeline + expungement / improve animations
        │
        └── benchmark/  (naive cosine vs RAG vs graph · Recall@k, MRR, chart)
```

**Stack:** Python 3.11 · Cognee (self-hosted OSS) · FastAPI · React + Vite ·
sentence-transformers (naive baseline) · Kuzu (graph) · LanceDB (vector)

---

## Repo Map

| Path | What |
|---|---|
| `EXECUTION_PLAN.md` | Full plan, owners, timelines, scoring map |
| `PROGRESS.md` | Living status — done / in progress / next, by owner |
| `backend/memory_service.py` | The 4 Cognee APIs, graph/vector recall modes |
| `backend/main.py` | FastAPI (live or gracefully degraded) |
| `backend/smoke_test.py` | Verifies all 4 APIs against the live SDK |
| `demo/demo.py` | 5-phase narrated live demo |
| `benchmark/` | 3-way retrieval benchmark — naive vs RAG vs graph |
| `data/hero_case/` | 9 synthetic case docs (the Daniel Marsh series) |
| `frontend/` | React UI — graph, 3-way compare, timeline |
| `docs/blog_post.md` | Hackathon blog post (Keychron side track) |
| `docs/API_CONTRACT.md` | Frontend/backend API contract |
| `docs/API_NOTES.md` | Verified Cognee SDK return shapes |

---

## Full Quickstart

```bash
# Priority 0 — prove the SDK runs (do this first)
./setup.sh                        # Python check, venv, pip install, .env scaffold
# Edit .env: add LLM_API_KEY
./setup.sh --smoke                # remember → recall → improve → forget (live)

# The live demo
python demo/demo.py --reset       # ingest → hunch → multi-hop recall → improve → expunge

# The benchmark (3-way comparison, generates chart.png + results.json)
python benchmark/benchmark.py
python benchmark/benchmark.py --naive   # offline baseline only

# The app
uvicorn backend.main:app --port 8000 --reload
cd frontend && npm install && npm run dev
# Open http://localhost:5173

# Zero-dep mock server (no Cognee needed)
python scripts/mock_server.py
```

---

## Team — Three Equal Owners

- **Sam** (`samuelshine`) — Lead · AI/backend
- **Jesh** (`jeshlin-donna`) — AI/backend
- **Benjy** (`benjyguitar`) — Frontend / product

Each pillar independently decides the outcome. Benchmark rigor, Cognee depth, and
product experience are all load-bearing.

---

## AI Disclosure

*Required for hackathon submission — non-disclosure is grounds for disqualification.*

Scaffolding, code, and documentation were produced with AI assistants (Claude by
Anthropic, ChatGPT by OpenAI). All AI-generated output was reviewed, edited, and
integrated by the team. The project architecture, benchmark design, API integration
decisions, and product framing are the team's own work. We declare this per the
hackathon's stated rules.
