# HungOver — Progress Tracker

> Living status doc. Updated as we go. Detailed plan lives in `EXECUTION_PLAN.md`.
> **Last updated:** 2026-06-30 (Day 2) — Priority 0 fully green (smoke test passes end-to-end)

Legend: ✅ done · 🔄 in progress · ⬜ todo · 🚧 blocked

---

## ✅ Done
| Item | Owner | Notes |
|---|---|---|
| Concept locked: Cold Case Connector (Open Source track) | All | Cross-jurisdiction siloed-evidence story |
| `EXECUTION_PLAN.md` — plan, owners, timelines, scoring map | Jesh | |
| Repo created + pushed (private) | Jesh | github.com/jeshlin-donna/hungover-coldcase, branch `main` |
| `backend/memory_service.py` — abstraction over all 4 Cognee APIs | Jesh | Signatures verified against cognee source; `INSIGHTS`→`TRIPLET_COMPLETION` caught |
| **Priority 0 — smoke test PASSES** | Jesh | All 5 steps green: remember/cognify/recall(3 modes)/hunch/expunge. Stack: cognee 1.2.2 + lancedb 0.26.0 + fastembed (local, no OpenAI key) + Claude Code Keychain key |
| `docs/API_NOTES.md` filled | Jesh | All signatures verified; RecallResponse shape confirmed |
| `requirements.txt` pinned | Jesh | cognee==1.2.2, lancedb==0.26.0 (0.33 has macOS ARM spill bug) |
| `backend/smoke_test.py` — Priority 0 live-SDK check | Jesh | ✅ passes on personal machine |
| `data/hero_case/` — 9 synthetic case docs + README | Sam/Jesh | Tool/vehicle/MO split across 2 jurisdictions |
| `benchmark/` — 3-way harness + 16 queries | Jesh | Pure-Python logic verified locally |
| `docs/API_CONTRACT.md` + `frontend/mock/` + `scripts/mock_server.py` | Jesh | Mock server verified running |
| `demo/demo.py` — 5-phase narrated live demo | Jesh | Syntax-verified; ready to live-run |
| `backend/main.py` — FastAPI, all contract routes | Jesh | Compiles clean; live/degraded auto-switch |
| `frontend/` — Vite + React, 3 panels + graph viz | Jesh | Scaffold complete; runs against mock server |
| `README.md` — story-first submission front door | Jesh | Drafted; benchmark numbers are placeholders |
| `setup.sh` — one-command bootstrap | Jesh | Syntax-checked |
| **Alibi Break** — contradiction detection + red-line view | Jesh | Works on mock; live recall() confirm is TODO in main.py |

---

## 🔄 In progress / start NOW (parallel)
| Item | Owner | Why it's unblocked |
|---|---|---|
| Source public noise corpus into `data/raw/` | Sam | No dependency; makes benchmark credible |
| Frontend: stub 3 panels with mock JSON + polish | Benjy | Mock server ready — `python scripts/mock_server.py` + `npm run dev` |
| Live-run `demo/demo.py` end-to-end | Jesh | Priority 0 done — unblocked |

---

## ⬜ To be done (Day 3 → Day 7, priority order)
| # | Item | Owner | Blocked by |
|---|---|---|---|
| 1 | Source public noise corpus `data/raw/` (200–500 records) + `data/SOURCES.md` | Sam | — |
| 2 | Live-run `demo/demo.py --reset` + confirm SDK end-to-end | Jesh | — |
| 3 | Hero case authoring (tighten for Day 3) | Sam | — |
| 4 | `scripts/ingest.py` — load full corpus via `remember()`/`cognify()` | Sam | #1 |
| 5 | `memory_service` wrappers: recall modes, log_hunch, resolve_case, expunge | Jesh | — |
| 6 | FastAPI: `/recall`, `/hunch`, `/resolve`, `/expunge`, `/graph`, `/benchmark` | Sam | #5 |
| 7 | Benchmark: 25–30 queries, 3 retrievers, Recall@k + MRR, `results.json` + `chart.png` | Jesh | #1, #4 |
| 8 | 3-way compare UI (naive vs RAG vs Graph, highlight multi-hop win) | Benjy | #6 |
| 9 | Graph viz wired to real backend nodes/edges | Benjy | #6 |
| 10 | `improve()` live loop — metric climbs after confirmed lead | Jesh | #5 |
| 11 | Expungement flow — subgraph deletion demo | Sam | #5 |
| 12 | Timeline view + improve/expunge animations | Benjy | #10, #11 |
| 13 | Full integration run-through end-to-end; log bugs | All | #8, #9, #10, #11 |
| 14 | README: drop real benchmark numbers + chart | Jesh | #7 |
| 15 | 2-min demo video | Benjy | #12 |
| 16 | Blog post (side track → Keychron) | Sam | #14 |
| 17 | Social posts tagging @wemakedevs + Cognee | Benjy | — |
| 18 | Open-source PRs to Cognee repo ($100 each) | All | start anytime |
| 19 | Final QA on clean clone + submit | All | all above |

---

## 🚧 Blockers / risks
- Corpus not yet sourced (Sam) — blocks benchmark and real ingestion.
- `improve()` live metric jump not yet captured — Day 5 work.
- Need to verify `demo/demo.py` runs against live SDK (now unblocked).

---

## Team — three equal owners
- **Sam** (`samuelshine`) — Lead · AI / backend
- **Jesh** (`jeshlin-donna`) — AI / backend
- **Benjy** (`benjyguitar`) — frontend / product experience
