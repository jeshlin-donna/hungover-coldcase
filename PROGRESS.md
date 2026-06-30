# HungOver — Progress Tracker

> Living status doc. Updated as we go. Detailed plan lives in `EXECUTION_PLAN.md`.
> **Last updated:** 2026-06-30 (Day 2) — added `demo/demo.py`; Sam set as lead

Legend: ✅ done · 🔄 in progress · ⬜ todo · 🚧 blocked

---

## ✅ Done
| Item | Owner | Notes |
|---|---|---|
| Concept locked: Cold Case Connector (Open Source track) | All | Cross-jurisdiction siloed-evidence story |
| `EXECUTION_PLAN.md` — plan, owners, timelines, scoring map | Jesh | |
| Repo created + pushed (private) | Jesh | github.com/jeshlin-donna/hungover-coldcase, branch `main` |
| `backend/memory_service.py` — abstraction over all 4 Cognee APIs | Jesh | ⚠️ has `# VERIFY` spots until Priority 0 runs |
| `backend/smoke_test.py` — Priority 0 live-SDK check | Jesh | Run on a personal machine |
| `data/hero_case/` — 9 synthetic case docs + README | Sam/Jesh | Tool/vehicle/MO split across 2 jurisdictions |
| `benchmark/` — 3-way harness + 16 queries | Jesh | Pure-Python logic verified locally (docs load, ID extract, metrics) |
| `docs/API_CONTRACT.md` + `frontend/mock/` + `scripts/mock_server.py` | Jesh | Mock server verified running (stdlib, no pip) |
| `demo/demo.py` — 5-phase narrated live demo | Jesh | Syntax-verified; runs once Priority 0 pins the SDK (`# VERIFY`) |

---

## 🔄 In progress
| Item | Owner | Notes |
|---|---|---|
| (nothing actively in progress — pick from TBD) | | |

---

## ⬜ To be done (priority order)
| # | Item | Owner | Blocked by |
|---|---|---|---|
| 1 | **Priority 0:** run `smoke_test.py` on a personal machine, fill `docs/API_NOTES.md`, pin every `# VERIFY` in `memory_service.py` | Jesh/Sam | — |
| 2 | Source public noise corpus into `data/raw/` (200–500 records) + `data/SOURCES.md` | Sam | — |
| 3 | ✅ `demo/demo.py` built — **live-run it once Priority 0 lands** to confirm against the real SDK | Jesh | #1 |
| 4 | FastAPI backend — real version of the mock, wired to `memory_service` | Sam | #1 |
| 5 | Frontend: Vite + 3 panels (graph / 3-way compare / timeline) against mock | Benjy | — (mock ready) |
| 6 | Frontend: wire to real backend; expungement + improve animations | Benjy | #4 |
| 7 | `improve()` live loop — metric climbs after a confirmed lead (capture before/after) | Jesh | #1 |
| 8 | `forget()` expungement flow — subgraph deletion demo | Sam | #1 |
| 9 | Full benchmark run on real corpus → `results.json` + `chart.png` | Jesh | #1, #2 |
| 10 | README — opens with Marsh story + benchmark chart + setup | Jesh | #9 |
| 11 | 2-min demo video | Benjy | #6 |
| 12 | Blog post (side track → Keychron) | Sam | #10 |
| 13 | Social posts tagging @wemakedevs + Cognee (side track → swag) | Benjy | — |
| 14 | Open-source PRs to Cognee repo ($100 each, max 5/person) | All | — (start anytime) |
| 15 | Final QA on clean clone + submit (with AI disclosure) | All | all above |

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
