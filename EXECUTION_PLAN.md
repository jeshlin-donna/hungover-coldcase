# ColdCache — Cold Case Connector

**The memory layer that connects the evidence humans already had.**

> Three burglaries. Two police departments. Zero shared memory. Caught after 23 months by luck — not investigation. Cognee would have connected them in one query.

- **Team:** ColdCache (3) — **Sam (lead · AI/backend)**, Jesh (AI/backend), Benjy (frontend / product)
- **Track:** Best Use of **Open Source** (self-hosted Cognee) → MacBook per member
- **Window:** Jun 29 – Jul 5, 2026. Submission target: **Jul 4 EOD**, buffer Jul 5.
- **AI disclosure:** Claude/ChatGPT used for code + docs. Declared in submission.

---

## 0. The North Star — how we actually win

The judges are **Cognee's own engineers**. We win by being the one submission that:

1. **Uses all 4 lifecycle APIs for real reasons** — `remember` (ingest), `recall` (graph+vector modes), `improve()` (session hunch → permanent memory), `forget()` (legal expungement)
2. **Earns the graph win empirically** — 3-way benchmark (naive vs RAG vs GRAPH) with Recall@k + MRR, showing graph >> vector on multi-hop queries
3. **Tells one gripping story** — Daniel Marsh 3-burglary series, 2 departments, 23 months
4. **Builds all 8 proposal modules** — not just a chatbot, a full investigative co-pilot
5. **Looks spectacular** — 8-panel UI, temporal slider, force graph, alibi break animation

### Judging criteria map
| Criterion | What earns it | Owner |
|---|---|---|
| Potential Impact | Cross-jurisdiction evidence gap is a real, serious problem; expungement = civic responsibility | Jesh |
| Creativity & Innovation | 8 agentic modules (alibi, missing hours, nexus, interrogation co-pilot, what-if sandbox, messy desk) | Sam |
| Technical Excellence | 3-way benchmark, async pipeline, 15 endpoints, graph schema | Jesh |
| **Best Use of Cognee** (heaviest) | All 4 APIs + GRAPH/VECTOR modes + session_ids in improve() + dataset-level forget() | Jesh + Sam |
| User Experience | 8 panels, dark theme, drag-drop ingestion, temporal slider, animations | Benjy |
| Presentation Quality | Story-first README, blog post, social posts, 2-min demo video, benchmark chart | All |

---

## 1. Full Architecture

```
data/raw/ (250 noise docs)          data/hero_case/ (11 docs)
         └──────────────┬────────────────────┘
                scripts/ingest.py
                remember() / cognify()
                        │
              backend/memory_service.py
              (all 4 Cognee APIs)
                        │
              backend/main.py (FastAPI)
              ┌─────────┴──────────┐
              │ 15 endpoints        │   benchmark/
              │ /recall /hunch      │   3-way: naive vs RAG vs GRAPH
              │ /resolve /expunge   │   Recall@k, MRR, chart.png
              │ /missing-hours      │
              │ /nexus /whatif      │
              │ /interrogation      │
              │ /ingest-file        │
              └────────┬────────────┘
                       │ REST/JSON
              frontend/ (React + Vite)
              ┌─────────────────────────────────────┐
              │ Case Graph (force-graph + legend)    │
              │ Graph vs Vector (3-col compare)      │
              │ Timeline (temporal slider)           │
              │ Missing Hours (info bounty)          │
              │ Nexus Point (shortest path)          │
              │ Interrogation Co-Pilot               │
              │ What-If Sandbox                      │
              │ Upload (drag-drop ingestion)         │
              └─────────────────────────────────────┘
```

**Stack:** Python 3.11 · Cognee 1.2.2 (OSS, self-hosted) · lancedb 0.26.0 · fastembed (local embeddings) · FastAPI · React + Vite · react-force-graph-2d · Claude Haiku (via keychain key)

---

## 2. Roles

- **Sam (lead · AI/backend):** corpus sourcing, hero case, ingestion pipeline, expunge flow, blog post, demo orchestration
- **Jesh (AI/backend):** Cognee core, memory_service, benchmark, improve() loop, README, submission
- **Benjy (frontend/product):** all 8 UI panels, temporal slider, drag-drop, 2-min demo video, social posts

---

## 3. Steps to completion

### Phase 1 — Foundation (DONE)
- [x] Priority 0 + smoke test passes (cognee 1.2.2 + Ollama gemma4:e4b + nomic-embed-text — all 5 API phases verified)
- [x] Demo.py live end-to-end passes (all 5 phases)
- [x] Backend: 15 endpoints implemented (FastAPI, live/degraded mode)
- [x] Frontend: 8 panels implemented (dark theme, animations)
- [x] Blog post + social posts + README written

### Phase 2 — Corpus & Benchmark (IN PROGRESS)
- [x] Complete 250-doc noise corpus (250/250 done)
- [ ] Full 3-way benchmark run produces results.json + chart.png
- [ ] Update README + blog with real benchmark numbers
- [x] Capture real improve() before/after metric delta (BEFORE: avg R@3=0.75, MRR=0.611 live from cognee_graph; improve() confirmed working; AFTER timed out — gemma4:e4b 4096-token context limit during session agent structured output)

### Phase 3 — Integration & QA
- [x] All agents merged + committed
- [x] Wire frontend to live backend (uvicorn + verify all 15 endpoints respond correctly)
- [x] Test all 8 panels against live Cognee (not just mock)
- [x] Test drag-drop ingestion end-to-end (upload new doc → appears in graph)
- [x] Dry-run demo.py twice on clean state
- [x] Fix any bugs discovered during integration

### Phase 4 — Content & Submission prep
- [ ] Benjy: record 2-min demo video (screen + voiceover)
  - Script: 23-month hook → ingest → 3-way compare (vector fails, graph wins) → alibi break → interrogation co-pilot → resolve/improve → expunge
- [ ] Sam: publish blog post on Medium/Dev.to
- [ ] Benjy: publish social posts (Twitter/X thread, LinkedIn, Instagram) on submission day
- [ ] All: browse Cognee GitHub issues, claim + submit 1-2 real PRs ($100 each)

### Phase 5 — Final QA & Submit
- [x] Clean-clone test: fresh venv, follow README from scratch, confirm everything works
- [ ] Make repo public
- [ ] Tag v1.0
- [ ] Fill submission form: repo link, video link, blog link, 4-API writeup, AI disclosure, team
- [ ] Submit early (don't wait for deadline)

---

## 4. Definition of Done
- [ ] Public GitHub repo, clean README with story + benchmark chart
- [ ] All 4 Cognee APIs used and documented
- [ ] 3-way benchmark: graph > vector on multi-hop (real numbers)
- [ ] All 8 UI panels functional
- [ ] 2-min demo video uploaded
- [ ] AI disclosure in submission
- [ ] Blog published + social posts live
- [x] Clean-clone test passes

---

## 5. The 8 agentic modules

| Module | Endpoint | UI Panel | Cognee API used |
|---|---|---|---|
| Messy Desk (ingestion) | POST /ingest-file | UploadPanel | remember() |
| Dynamic Evidence Board | GET /graph | GraphPanel | recall(GRAPH) |
| Alibi Collision Engine | GET /contradictions | GraphPanel (red edges) | recall(GRAPH) |
| Missing Hours | GET /missing-hours | MissingHoursPanel | recall(GRAPH) |
| Nexus Point | POST /nexus | NexusPanel | recall(GRAPH) |
| Interrogation Co-Pilot | POST /interrogation | InterrogationPanel | recall(GRAPH) |
| What-If Sandbox | POST /whatif | WhatIfPanel | recall(GRAPH) |
| Resolve & Improve | POST /resolve | App.jsx metric card | improve(session_ids) |

---

## 6. Risk register
| Risk | Mitigation |
|---|---|
| Benchmark shows graph ≈ vector | Design multi-hop queries that structurally need graph traversal; if still weak, lead with relationship-extraction demo |
| Live demo crashes | Degraded mode serves mock data — demo never hard-crashes |
| Corpus licensing | Only synthetic/public data; document in SOURCES.md |
| Time slips | Jul 4 is load-bearing — protect it |

---

## 7. Side tracks
- **Blog post** ($100 Keychron): docs/blog_post.md → publish on Medium/Dev.to by Jul 4
- **Social posts** (swag): docs/social_posts.md → tag @wemakedevs + @cognee_ai on submission day
- **Cognee PRs** ($100 each, max 5/person): browse topoteretes/cognee issues, claim, submit real PRs

---

## 8. Submission copy
- **Team:** ColdCache
- **Product:** Cold Case Connector
- **One-liner:** "Every detective had a piece of the evidence. Nobody had the shared memory to connect it. Cognee does."
- **AI disclosure:** Built with Claude Code (Anthropic) for code generation and documentation. All AI usage declared per hackathon rules.
