# ColdCache — Progress Tracker

> **Last updated:** 2026-07-01 — all 8 modules built, corpus complete, typed schema added, live pipeline verified
> Detailed plan: `EXECUTION_PLAN.md`

Legend: ✅ done · 🔄 in progress · ⬜ todo

---

## ✅ Done
| Item | Owner | Notes |
|---|---|---|
| Concept + story locked | All | 3 burglaries, 2 depts, 23 months |
| Repo + EXECUTION_PLAN + PROGRESS | Jesh | |
| `backend/memory_service.py` — all 4 Cognee APIs | Jesh | Verified against source |
| **Priority 0 smoke test passes** | Jesh | cognee 1.2.2 + lancedb 0.26.0 + fastembed + Claude key |
| `data/hero_case/` — 11 synthetic docs | Sam/Jesh | |
| **`demo/demo.py` live end-to-end passes** | Jesh | All 5 phases. Alibi answer: "card records place Marsh 4.2mi from scene at 00:48" |
| **Backend — 13 endpoints** | Jesh | /recall /hunch /resolve /expunge /graph /timeline /contradictions /benchmark /missing-hours /nexus /interrogation /whatif /ingest-file |
| **Frontend — 8 panels** | Jesh/Benjy | Case Graph · Compare · Timeline · Missing Hours · Nexus · Interrogation · What-If · Upload |
| GraphPanel — legend, click detail, expunge animation, alibi edges | Jesh | |
| ComparePanel — 3-col, GRAPH WINS banner, skeleton loader, multi-hop badge | Jesh | |
| TimelinePanel — horizontal, jurisdiction colors, temporal slider | Jesh | |
| MissingHoursPanel — urgency badges, recommendations, info bounty | Jesh | |
| NexusPanel — entity path visualization, hops + strength | Jesh | |
| InterrogationPanel — trap questions, weak edges, strategy callout | Jesh | |
| WhatIfPanel — confidence bar charts, hypothesis sandbox | Jesh | |
| UploadPanel — drag-drop ingestion (Messy Desk) | Jesh | |
| `docs/blog_post.md` — 1500-word blog with code + benchmark table | Jesh | |
| `docs/social_posts.md` — Twitter, LinkedIn, Instagram | Jesh | |
| `README.md` — story-first, quick start, 4-API usage, AI disclosure | Jesh | |
| `scripts/ingest.py` + `scripts/generate_corpus.py` | Jesh | |
| `data/raw/` — 250/250 synthetic noise incident reports | Agent | Complete |
| **Naive benchmark baseline** (full 261-doc corpus) | Agent | R@3: single_hop=0.5, multi_hop=0.401, all=0.439 · R@5: 0.6/0.417/0.487 · MRR: 0.379/0.485/0.444 (see `benchmark/results.json`) |
| **Typed Cognee schema** (`backend/schema.py`) | Agent | Person/Location/TimePoint/Evidence/Object nodes; WAS_AT/AT_TIME/DEPICTS/REPORTED_BY/CONTRADICTS edges, wired into `cognify()`. Matches design-doc Version 2 blueprint. |
| **Live local-LLM pipeline verified** | Agent | Full `remember→cognify→recall` cycle passes against Ollama (llama3.1:8b) + local Postgres/pgvector — real graph extraction with correct node/edge counts, no mocking. |

---

## 🔄 In progress
| Item | ETA | Notes |
|---|---|---|
| **Full 3-way benchmark** (naive + cognee_vector + cognee_graph) | needs a faster LLM or more headroom | Naive leg is done (see above). Attempted the Cognee legs twice against local Ollama (llama3.1:8b): pipeline itself works end-to-end (verified in smoke test), but on this machine the run died partway through 261-doc ingestion both times — first from an uncaught exception on a single flaky structured-output response (fixed: `benchmark.py` now catches/logs/skips per-doc failures instead of crashing the whole run), then from **system memory pressure** (swap was at ~13.3/14.3GB used with Chrome/Teams/Slack/Outlook/Defender competing with Ollama for RAM — not a code bug). Recommend either running with a real API key (Claude/GPT-4o-mini) for a same-day full run, or re-running the local Ollama pipeline on a quieter machine / with other apps closed. |

---

## ⬜ To do (Day 3 → Day 7)
| # | Item | Owner |
|---|---|---|
| 1 | Drop real benchmark numbers into README + blog post | Jesh | Naive baseline numbers in; Cognee legs pending a faster LLM run |
| 2 | Capture real improve() before/after delta | Jesh |
| 3 | Push to GitHub (needs your terminal: `git push origin main`) | Jesh |
| 4 | Test all 8 panels against live backend (uvicorn + real Cognee) | Sam/Jesh |
| 5 | **2-min demo video** (screen + voiceover) | Benjy |
| 6 | Publish blog post (Medium/Dev.to) | Sam |
| 7 | Social posts live on submission day | Benjy |
| 8 | Cognee GitHub PRs ($100 each) | All |
| 9 | Clean-clone QA test | All |
| 10 | Make repo public · tag v1.0 · submit form | Jesh |

---

## 📋 All 8 modules — status
| Module | Endpoint | Panel | Status |
|---|---|---|---|
| Messy Desk (drag-drop) | POST /ingest-file | UploadPanel | ✅ |
| Evidence Board (graph) | GET /graph | GraphPanel | ✅ |
| Alibi Collision Engine | GET /contradictions | GraphPanel (red edges) | ✅ |
| Missing Hours | GET /missing-hours | MissingHoursPanel | ✅ |
| Nexus Point | POST /nexus | NexusPanel | ✅ |
| Interrogation Co-Pilot | POST /interrogation | InterrogationPanel | ✅ |
| What-If Sandbox | POST /whatif | WhatIfPanel | ✅ |
| Resolve & Improve | POST /resolve | App.jsx metric card | ✅ |

---

## 🏆 Judging coverage
| Criterion | Evidence | Strength |
|---|---|---|
| Potential Impact | Cross-jurisdiction gap is real; expungement = civic | ★★★★★ |
| Creativity & Innovation | 8 agentic modules, temporal slider, what-if sandbox, interrogation co-pilot | ★★★★★ |
| Technical Excellence | 3-way benchmark, 13 endpoints, graph schema, async | ★★★★☆ |
| Best Use of Cognee | All 4 APIs, 3 search modes, session_ids, dataset-level forget | ★★★★★ |
| User Experience | 8 panels, dark theme, animations, drag-drop, temporal slider | ★★★★★ |
| Presentation Quality | Blog, social posts, README, demo.py, chart (pending real numbers) | ★★★★☆ |

---

## Team
- **Sam** (`samuelshine`) — Lead · AI / backend
- **Jesh** (`jeshlin-donna`) — AI / backend
- **Benjy** (`benjyguitar`) — frontend / product / demo video
