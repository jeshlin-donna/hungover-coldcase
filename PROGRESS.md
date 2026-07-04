# ColdCache — Progress Tracker

> **Last updated:** 2026-07-04 — Vision pipeline swapped to Ollama/Groq; all 20 endpoints verified; full 3-way benchmark pending.
> Detailed plan: `EXECUTION_PLAN.md`

## Case-scoped persistence milestone — in progress

The persistence foundation is implemented: application-owned SQLite/WAL storage, case CRUD,
durable original files, evidence/revision/job records, restart recovery, background analysis and
ingestion, immutable per-case Cognee dataset names, and graph revision tracking. The blank case
home, case creation, reload-rehydrated import/review queue, retries/cancellation, and case-scoped
graph/chat/suggestions/stats plus SSE/poll reconciliation are now implemented. Remaining tool routes, caching, and lifecycle
hardening now include idempotent state transitions, duplicate skipping, persisted drafts, bounded
streaming uploads, leases/heartbeats, replayable events, archive/restore, and guarded deletion.
Evidence-level removal after Cognee ingestion still requires a verified SDK delete or dataset rebuild. Design:
[`docs/CASE_PERSISTENCE_PLAN.md`](docs/CASE_PERSISTENCE_PLAN.md).

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
| **Backend — 20 endpoints** | Jesh/Sam | /recall /hunch /resolve /expunge /graph /graph/temporal /timeline /contradictions /benchmark /recall/compare /missing-hours /nexus /interrogation /whatif /chat /report /suspect-timeline /transcribe /ingest-file + /health |
| **Frontend — 8 panels** | Jesh/Benjy | Case Graph · Compare · Timeline · Missing Hours · Nexus · Interrogation · What-If · Upload |
| GraphPanel — legend, click detail, expunge animation, alibi edges | Jesh | |
| ComparePanel — 3-col, GRAPH WINS banner, skeleton loader, multi-hop badge | Jesh | |
| TimelinePanel — horizontal, jurisdiction colors, temporal slider | Jesh | |
| MissingHoursPanel — urgency badges, recommendations, info bounty | Jesh | |
| NexusPanel — entity path visualization, hops + strength | Jesh | |
| InterrogationPanel — trap questions, weak edges, strategy callout | Jesh | |
| WhatIfPanel — confidence bar charts, hypothesis sandbox | Jesh | |
| UploadPanel — verified case-file import | Jesh | |
| `docs/blog_post.md` — 1500-word blog with code + benchmark table | Jesh | |
| `docs/social_posts.md` — Twitter, LinkedIn, Instagram | Jesh | |
| `README.md` — story-first, quick start, 4-API usage, AI disclosure | Jesh | |
| `scripts/ingest.py` + `scripts/generate_corpus.py` | Jesh | |
| `data/raw/` — 250/250 synthetic noise incident reports | Agent | Complete |
| **Naive benchmark baseline** (full 261-doc corpus) | Agent | R@3: single_hop=0.5, multi_hop=0.401, all=0.439 · R@5: 0.6/0.417/0.487 · MRR: 0.379/0.485/0.444 (see `benchmark/results.json`) |
| **Typed Cognee schema** (`backend/schema.py`) | Agent | Person/Location/TimePoint/Evidence/Object nodes; WAS_AT/AT_TIME/DEPICTS/REPORTED_BY/CONTRADICTS edges, wired into `cognify()`. Matches design-doc Version 2 blueprint. |
| **Live local-LLM pipeline verified (Ollama gemma4:e4b)** | Sam | Full `remember→cognify→recall→improve→forget` smoke test passes against local Ollama (`gemma4:e4b` LLM + `nomic-embed-text:latest` embeddings). All 5 API phases confirmed. `COGNEE_SKIP_CONNECTION_TEST=true` added to avoid 30s probe per doc. |
| **`benchmark/benchmark_improve.py`** | Sam | Script to measure real `improve()` before/after metric delta using hero-case docs. Running now against Ollama. |
| **Real Cognee graph recall numbers (BEFORE improve())** | Sam | Live `cognee_graph` recall on 3 multi-hop queries: avg R@3=0.75, avg MRR=0.611. q07 (cross-jurisdiction forensic link): R@3=1.0, MRR=1.0. q17 (alibi contradiction): R@3=1.0, MRR=0.5. `improve()` itself confirmed working — AFTER recall timed out due to `gemma4:e4b` 4096-token context limit on session agent structured output (model constraint, not Cognee bug). Results in `benchmark/improve_results.json`. |
| Test all 8 panels against live backend (uvicorn + real Cognee) | Sam/Jesh | ✅ |
| Test drag-drop ingestion end-to-end (upload new doc → appears in graph) | Sam/Jesh | ✅ |
| Dry-run demo.py twice on clean state | Sam/Jesh | ✅ |
| Fix any bugs discovered during integration | Sam/Jesh | ✅ |
| Clean-clone QA test | All | ✅ Fresh venv setup, keyless/degraded API contract, generated corpus, frontend production build, and live 5-phase Cognee smoke test verified from scratch. |
| **Vision pipeline — Ollama + Groq** | Sam | `describe_image()` and `transcribe_audio()` now auto-route: Groq (detected via `LLM_ENDPOINT`) uses groq SDK (llava vision + whisper-large-v3); Ollama (default) calls `/api/chat` with base64 images. No Anthropic SDK dependency. Configurable via `VISION_MODEL` env var. |
| **Unified multimodal ingest** | Sam | All 6 modalities (image/audio/video/PDF/spreadsheet/text) fully working with Groq + Ollama. Docs updated: requirements.txt, .env.example, docs/API_NOTES.md, README.md. |

---

## 🔄 In progress
| Item | ETA | Notes |
|---|---|---|
| **Full 3-way benchmark** (naive + cognee_vector + cognee_graph) | in progress | Naive leg done. `benchmark_improve.py` complete — BEFORE cognee_graph R@3=0.75 confirmed live. Full 261-doc benchmark (`benchmark.py`) is the current task. |

---

## ⬜ To do (Day 3 → Day 7)
| # | Item | Owner |
|---|---|---|
| 1 | Drop real benchmark numbers into README + blog post | Jesh | Naive baseline numbers in; Cognee legs pending a faster LLM run |
| 2 | Capture real improve() before/after delta | Jesh |
| 3 | Push to GitHub (needs your terminal: `git push origin main`) | Jesh |
| 5 | **2-min demo video** (screen + voiceover) | Benjy |
| 6 | Publish blog post (Medium/Dev.to) | Sam |
| 7 | Social posts live on submission day | Benjy |
| 8 | Cognee GitHub PRs ($100 each) | All |
| 10 | Make repo public · tag v1.0 · submit form | Jesh |

---

## 📋 All 8 modules — status
| Module | Endpoint | Panel | Status |
|---|---|---|---|
| Import Case Files and Data | POST /ingest-files/analyze + /ingest-files/confirm | UploadPanel | ✅ multi-file + partial retry |
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
| Technical Excellence | 3-way benchmark (naive done), 20 endpoints, graph schema, async, fully local Ollama vision | ★★★★★ |
| Best Use of Cognee | All 4 APIs, 3 search modes, session_ids, dataset-level forget | ★★★★★ |
| User Experience | 8 panels, dark theme, animations, drag-drop, temporal slider | ★★★★★ |
| Presentation Quality | Blog, social posts, README, demo.py, chart (pending real numbers) | ★★★★☆ |

---

## Team
- **Sam** (`samuelshine`) — Lead · AI / backend
- **Jesh** (`jeshlin-donna`) — AI / backend
- **Benjy** (`benjyguitar`) — frontend / product / demo video
