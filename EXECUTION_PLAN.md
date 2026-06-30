# HungOver — Cold Case Connector

**The memory layer that connects the evidence humans already had.**

> Three burglaries. Two police departments. Zero shared memory. Caught after 23 months by luck — not investigation. Cognee would have connected them in one query.

- **Team:** HungOver (3) — **Sam (lead · AI/backend)**, Jesh (AI/backend), Benjy (frontend / product)
- **Track:** Best Use of **Open Source** (self-hosted Cognee) → MacBook per member
- **Window:** Jun 29 – Jul 5, 2026. We're on **Day 2 (Jun 30)**. Submission target: **Jul 4 EOD**, buffer Jul 5.
- **AI disclosure:** Claude/ChatGPT used for code + docs. Declared in submission.

---

## 0. The North Star — how we actually win

The judges are **Cognee's own engineers**. We win by being the one submission that:

1. **Uses all 4 lifecycle APIs for real reasons** — `remember` (ingest), `recall` (graph+vector+insights modes), `improve()` (session hunch → permanent memory), `forget()` (legal expungement)
2. **Earns the graph win empirically** — 3-way benchmark (naive vs RAG vs GRAPH) with Recall@k + MRR, showing graph >> vector on multi-hop queries
3. **Tells one gripping story** — Daniel Marsh 3-burglary series, 2 departments, 23 months
4. **Builds all 5 proposal modules** — not just a chatbot, a full investigative co-pilot
5. **Looks spectacular** — 8-panel UI, temporal slider, force graph, alibi break animation

### Judging criteria map
| Criterion | What earns it | Owner |
|---|---|---|
| Potential Impact | Cross-jurisdiction evidence gap is a real, serious problem; expungement = civic responsibility | Jesh |
| Creativity & Innovation | 5 agentic modules (alibi, missing hours, nexus, interrogation co-pilot, what-if sandbox) | Sam |
| Technical Excellence | 3-way benchmark, async pipeline, 8 endpoints, graph schema | Jesh |
| **Best Use of Cognee** (heaviest) | All 4 APIs + GRAPH/VECTOR/INSIGHTS modes + session_ids in improve() + dataset-level forget() | Jesh + Sam |
| User Experience | 8 panels, drag-drop ingestion, temporal slider, animations | Benjy |
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
              │ 13 endpoints        │   benchmark/
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

## 3. Remaining schedule (Day 2 evening → Day 7)

### Day 2 (TODAY — Jun 30): Build sprint ← WE ARE HERE
- [x] Priority 0 + smoke test passes
- [x] Demo.py live end-to-end passes (all 5 phases)
- [x] Frontend: 3 core panels polished (dark theme, animations)
- [x] Blog post + social posts + README rewrite
- [ ] 250-doc noise corpus (66/250 done, agent running)
- [ ] 5 new backend endpoints (agent running)
- [ ] 5 new frontend panels + temporal slider (agent running)
- [ ] Full 3-way benchmark run (agent waiting on corpus)

### Day 3 (Wed Jul 1): Integration + benchmark
- [ ] All agents merged + committed
- [ ] Full benchmark produces results.json + chart.png with real numbers
- [ ] README + blog updated with real numbers
- [ ] Backend wired live (run uvicorn + verify all 13 endpoints)
- [ ] Frontend hitting real backend (not just mock)
- [ ] improve() before/after metric captured from real run
- [ ] Sam: source/clean data/raw to 250 docs, SOURCES.md

### Day 4 (Thu Jul 2): Demo polish
- [ ] Full integration run-through (all 8 panels, all happy paths)
- [ ] Dry-run demo.py twice on clean state
- [ ] ISSUES.md — log any bugs, fix them
- [ ] Drag-drop ingestion tested live (upload a new doc, see it in graph)
- [ ] What-If sandbox tested with real what-if scenarios
- [ ] Nexus point tested between all node pairs

### Day 5 (Fri Jul 3): Video + final content
- [ ] Benjy: record 2-min demo video (screen + voiceover)
  - Script: 23-month hook → ingest → compare (vector vs graph fails → graph wins) → alibi break → interrogation co-pilot → resolve/improve → expunge
- [ ] Publish blog post
- [ ] Final README pass (drop placeholder numbers, put real ones)
- [ ] All: browse Cognee GitHub issues, claim + submit 1-2 real PRs ($100 each)

### Day 6 (Sat Jul 4 — load-bearing day): QA + submit
- [ ] Clean-clone test (fresh venv, follow README, confirm everything works)
- [ ] Make repo public
- [ ] Tag v1.0
- [ ] Fill submission form: repo link, video link, blog link, 4-API writeup, AI disclosure, team
- [ ] Sam: publish blog; Benjy: publish social posts
- [ ] Submit early (don't wait for deadline)

### Day 7 (Sun Jul 5): Buffer
- [ ] Fix anything broken from QA
- [ ] Final submission confirmation

---

## 4. Definition of Done
- [ ] Public GitHub repo, clean README with story + benchmark chart
- [ ] All 4 Cognee APIs used and documented
- [ ] 3-way benchmark: graph > vector on multi-hop (real numbers)
- [ ] All 8 UI panels functional
- [ ] 2-min demo video uploaded
- [ ] AI disclosure in submission
- [ ] Blog published + social posts live
- [ ] Clean-clone test passes

---

## 5. The 8 agentic modules (from proposal)

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
- **Team:** HungOver
- **Product:** Cold Case Connector
- **One-liner:** "Every detective had a piece of the evidence. Nobody had the shared memory to connect it. Cognee does."
- **AI disclosure:** Built with Claude Code (Anthropic) for code generation and documentation. All AI usage declared per hackathon rules.
