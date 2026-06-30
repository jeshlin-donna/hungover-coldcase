# HungOver — Progress Tracker

> Living status doc. Updated as we go. Detailed plan lives in `EXECUTION_PLAN.md`.
> **Last updated:** 2026-06-30 (Day 2) — added the **Alibi Break** (contradiction view); multi-modal + drag-drop logged as stretch

Legend: ✅ done · 🔄 in progress · ⬜ todo · 🚧 blocked

---

## ✅ Done
| Item | Owner | Notes |
|---|---|---|
| Concept locked: Cold Case Connector (Open Source track) | All | Cross-jurisdiction siloed-evidence story |
| `EXECUTION_PLAN.md` — plan, owners, timelines, scoring map | Jesh | |
| Repo created + pushed (private) | Jesh | github.com/jeshlin-donna/hungover-coldcase, branch `main` |
| `backend/memory_service.py` — abstraction over all 4 Cognee APIs | Jesh | ✅ **signatures verified against cognee source** — `# VERIFY` resolved; caught `INSIGHTS`→`TRIPLET_COMPLETION` + sync-cognify |
| `backend/smoke_test.py` — Priority 0 live-SDK check | Jesh | Run on a personal machine |
| `data/hero_case/` — 9 synthetic case docs + README | Sam/Jesh | Tool/vehicle/MO split across 2 jurisdictions |
| `benchmark/` — 3-way harness + 16 queries | Jesh | Pure-Python logic verified locally (docs load, ID extract, metrics) |
| `docs/API_CONTRACT.md` + `frontend/mock/` + `scripts/mock_server.py` | Jesh | Mock server verified running (stdlib, no pip) |
| `demo/demo.py` — 5-phase narrated live demo | Jesh | Syntax-verified; runs once Priority 0 pins the SDK (`# VERIFY`) |
| `backend/main.py` — FastAPI, all contract routes | Jesh | Compiles clean; auto **live/degraded** (serves mock if no SDK) so it runs today |
| `frontend/` — Vite + React, 3 panels + graph viz | Jesh | Scaffold complete (graph / 3-way compare / timeline); runs against mock server now |
| `README.md` — story-first submission front door | Jesh | Drafted; benchmark numbers are placeholders until live run |
| `setup.sh` — one-command Priority-0 bootstrap | Jesh | Syntax-checked; picks Python ≥3.10, venv+deps+env+smoke test |
| **Alibi Break** — 2nd wow beat (contradiction detection) | Jesh | Alibi+receipt docs, `/contradictions` endpoint, red-line graph view, demo + benchmark queries. Works on mock today |

---

## 🔄 In progress / start NOW (parallel, no waiting)
| Item | Owner | Why it's unblocked |
|---|---|---|
| **Priority 0** — `smoke_test.py` on a personal machine → fill `API_NOTES.md` → pin `# VERIFY` | Jesh/Sam | The gate for everything live. ~20 min. |
| Build out the frontend panels (polish, then `improve()`/expunge animations) | Benjy | Scaffold + mock server ready — `python scripts/mock_server.py` + `npm run dev` |
| Source the public noise corpus into `data/raw/` | Sam | No dependency; makes the benchmark credible |

---

## ⬜ To be done (priority order)
| # | Item | Owner | Blocked by |
|---|---|---|---|
| 1 | **Priority 0 — mostly DONE via source:** signatures verified + pinned, `API_NOTES.md` filled. **Remaining:** run `./setup.sh --smoke` once with a key to confirm the `RecallResponse` runtime shape (for benchmark id-extraction) | Jesh/Sam | — |
| 2 | Source public noise corpus into `data/raw/` (200–500 records) + `data/SOURCES.md` | Sam | — |
| 3 | ✅ `demo/demo.py` built — **live-run it once Priority 0 lands** to confirm against the real SDK | Jesh | #1 |
| 4 | ✅ FastAPI scaffolded — **verify live-wiring** once SDK pinned; real `/graph` from Cognee `INSIGHTS` still TODO | Sam/Jesh | #1 |
| 5 | ✅ Frontend scaffolded (3 panels + graph viz) — **Benjy: build out + polish** | Benjy | — |
| 6 | Frontend: wire to real backend; expungement + `improve()` animations | Benjy | #4 |
| 7 | `improve()` live loop — metric climbs after a confirmed lead (capture before/after) | Jesh | #1 |
| 8 | `forget()` expungement flow — subgraph deletion demo | Sam | #1 |
| 9 | Full benchmark run on real corpus → `results.json` + `chart.png` | Jesh | #1, #2 |
| 10 | ✅ README drafted — **drop real benchmark numbers + chart** after #9 | Jesh | #9 |
| 11 | 2-min demo video | Benjy | #6 |
| 12 | Blog post (side track → Keychron) | Sam | #10 |
| 13 | Social posts tagging @wemakedevs + Cognee (side track → swag) | Benjy | — |
| 14 | Open-source PRs to Cognee repo ($100 each, max 5/person) | All | — (start anytime) |
| 15 | Final QA on clean clone + submit (with AI disclosure) | All | all above |

### Stretch goals (only after Tier 0 core is live — do not let these block Priority 0)
| Tier | Item | Owner | Notes |
|---|---|---|---|
| ✅ T1 | **Alibi Break** contradiction view | Jesh | DONE (works on mock; live contradiction-confirm via `recall()` is a TODO in `main.py`) |
| T2 | Multi-modal ingestion: evidence photo → vision LLM (gpt-4o) → text → `remember()` | Sam | **Pre-bake, never live on stage** (vision calls slow/flaky). High wow if core is done |
| T3 | Drag-and-drop ingestion drop-zone UI | Benjy | Nice UX; not core |

---

## 🚧 Blockers / risks
- Cognee SDK return shapes unverified until Priority 0 (#1) — single biggest unknown.
- Benchmark must show graph > vector on multi-hop; if weak, lean on `INSIGHTS`/relationship extraction.
- Corp pod can't `pip install` — all live-SDK work happens on personal machines.

---

## Team — three equal owners
Backend depth, retrieval rigor, and product experience are each decisive; no piece is "support work." We win or lose on all three together.
- **Sam** (`samuelshine`) — Lead · AI / backend
- **Jesh** (`jeshlin-donna`) — AI / backend
- **Benjy** (`benjyguitar`) — frontend / product experience
