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

## The idea

Investigations fail not because the evidence is missing, but because it's **siloed** — a
tool-mark report in one county, a witness's plate in another, the same MO in a third file.
Answering *"are these the same offender?"* requires **connecting evidence across documents
and jurisdictions over time** — exactly the multi-hop reasoning that plain vector search
can't do and a **knowledge graph** can.

Cold Case Connector ingests case files into Cognee's hybrid **graph + vector** memory, then
lets an investigator ask questions that traverse the whole web of evidence — and proves,
with a benchmark, that the graph catches links vector search misses.

> ⚠️ **Synthetic data only. Illustrative demo, not an operational tool.** Framing is
> deliberately *"connect evidence humans already had"* — never predictive policing.

## All four Cognee lifecycle APIs, each for a real reason

| API | Where we use it |
|---|---|
| `remember()` | Ingest case files / forensic reports / witness statements from two siloed departments into one graph |
| `recall()` | Ask multi-hop questions — explicit **graph** (`GRAPH_COMPLETION`) vs **vector** (`RAG_COMPLETION`) modes drive the comparison |
| `improve()` | A detective's in-session **hunch** (session memory) is bridged into permanent memory with `session_ids` when the case resolves — memory gets sharper |
| `forget()` | **Record expungement** — a sealed record's subgraph is surgically deleted while everything else stays intact |

## The benchmark (our moat)

Same corpus, same queries, three retrievers: **naive cosine** vs **Cognee vector** vs
**Cognee graph**. Reported as Recall@3/@5 + MRR, split single-hop vs multi-hop.

> **Hypothesis:** all three tie on single-hop; **Cognee graph pulls ahead on multi-hop**,
> where the answer requires connecting ≥2 documents across jurisdictions.

_Numbers + chart land here after the live run (`benchmark/benchmark.py`)._

| Retriever | multi-hop Recall@3 | multi-hop MRR |
|---|---|---|
| naive_vector | _tbd_ | _tbd_ |
| cognee_vector | _tbd_ | _tbd_ |
| **cognee_graph** | _tbd_ | _tbd_ |

## Architecture

```
data/ (hero case + public corpus)
        │ remember()/add()+cognify()  (async status polling)
        ▼
 backend/memory_service.py  ── single abstraction over the 4 Cognee APIs
        │                         (explicit graph vs vector recall modes)
        ├── backend/main.py (FastAPI)  ──REST──►  frontend/ (React + force-graph)
        └── benchmark/  (naive vs RAG vs graph · Recall@k, MRR, chart)
```

## Quickstart

```bash
# 1. Priority 0 — verify the SDK (on a machine that can pip install):
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add LLM_API_KEY
python backend/smoke_test.py  # prints real SDK shapes -> docs/API_NOTES.md

# 2. The live demo (your stage script):
python demo/demo.py --reset

# 3. The benchmark:
python benchmark/benchmark.py          # or --naive for the offline baseline

# 4. The app:
uvicorn backend.main:app --port 8000   # backend (auto live/degraded)
cd frontend && npm install && npm run dev
```

No Cognee yet? The backend serves curated mock data in **degraded mode**, and
`python scripts/mock_server.py` (stdlib, zero deps) runs the UI anywhere.

## Repo map

| Path | What |
|---|---|
| `EXECUTION_PLAN.md` | Full plan, owners, timelines, scoring map |
| `PROGRESS.md` | Living status — done / in progress / next, by owner |
| `backend/memory_service.py` | The 4 Cognee APIs, graph/vector modes |
| `backend/main.py` | FastAPI (live or degraded) |
| `demo/demo.py` | 5-phase narrated live demo |
| `benchmark/` | 3-way retrieval benchmark |
| `data/hero_case/` | 9 synthetic case docs (the Daniel Marsh series) |
| `frontend/` | React UI — graph, 3-way compare, timeline |
| `docs/API_CONTRACT.md` · `docs/API_NOTES.md` | Frontend contract · verified SDK notes |

## Team — three equal owners
- **Sam** (`samuelshine`) — Lead · AI/backend
- **Jesh** (`jeshlin-donna`) — AI/backend
- **Benjy** (`benjyguitar`) — frontend / product

## AI assistance disclosure
Scaffolding, code, and docs were produced with AI assistants (Claude, ChatGPT), reviewed
and integrated by the team. Declared per hackathon rules.
