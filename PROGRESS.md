# HungOver — Progress Tracker

> Living status doc. Updated as we go. Detailed plan lives in `EXECUTION_PLAN.md`.
> **Last updated:** 2026-06-30 (Day 2, evening) — full build sprint in progress

Legend: ✅ done · 🔄 in progress · ⬜ todo · 🚧 blocked

---

## ✅ Done
| Item | Owner | Notes |
|---|---|---|
| Concept locked: Cold Case Connector (Open Source track) | All | Cross-jurisdiction siloed-evidence story |
| `EXECUTION_PLAN.md` — plan, owners, timelines, scoring map | Jesh | |
| Repo created + pushed (private) | Jesh | github.com/jeshlin-donna/hungover-coldcase |
| `backend/memory_service.py` — all 4 Cognee APIs abstracted | Jesh | Signatures verified against source |
| **Priority 0 — smoke test passes** | Jesh | All 5 steps green. Stack: cognee 1.2.2 + lancedb 0.26.0 + fastembed + Claude Code key |
| `docs/API_NOTES.md` filled | Jesh | All signatures verified |
| `requirements.txt` pinned | Jesh | cognee==1.2.2, lancedb==0.26.0 |
| `data/hero_case/` — 11 synthetic case docs | Sam/Jesh | 3 burglaries across 2 jurisdictions + alibi/receipt docs |
| `benchmark/` — harness + 18 queries | Jesh | Queries cover single_hop + multi_hop |
| `docs/API_CONTRACT.md` + `scripts/mock_server.py` | Jesh | Mock server works standalone |
| **`demo/demo.py` — live end-to-end PASSES** | Jesh | ✅ All 5 phases ran clean. Alibi break answer: "card records place Marsh 4.2mi from scene at 00:48" |
| `backend/main.py` — FastAPI, all core routes | Jesh | live/degraded auto-switch |
| **Frontend polish** — dark theme, all 3 panels rewritten | Jesh | GraphPanel: legend, click detail, expunge animation, contradiction edges; ComparePanel: 3-col, GRAPH WINS banner, skeleton; TimelinePanel: horizontal, jurisdiction colors, 23-month callout |
| `docs/blog_post.md` — 1500-word hackathon blog | Jesh | Real code snippets, benchmark table, alibi break explained |
| `docs/social_posts.md` — Twitter thread, LinkedIn, Instagram | Jesh | Ready to post on submission day |
| `README.md` — complete rewrite | Jesh | Quick start, benchmark table, 4-API usage, AI disclosure |
| `scripts/ingest.py` — corpus ingestion script | Jesh | Loads hero_case + data/raw via remember() |
| `data/raw/` — synthetic noise corpus | Sam/Jesh | 66 files and counting (target 250) |

---

## 🔄 In progress RIGHT NOW (parallel agents)
| Item | Owner | ETA |
|---|---|---|
| Noise corpus generation — 250 synthetic incident reports | Agent | ~10 min |
| Backend: 5 new endpoints (missing-hours, nexus, interrogation, whatif, ingest-file) | Agent | ~5 min |
| Frontend: 5 new panels + temporal slider + drag-drop (all proposal modules) | Agent | ~10 min |
| Full 3-way benchmark (naive + cognee_vector + cognee_graph) | Agent | ~20 min |

---

## ⬜ To be done
| # | Item | Owner | Blocked by |
|---|---|---|---|
| 1 | Commit all new endpoints + panels + corpus | Jesh | agents finishing |
| 2 | Run full benchmark → real results.json + chart.png | Agent (running) | corpus |
| 3 | Drop real benchmark numbers into README + blog post | Jesh | #2 |
| 4 | Wire improve() before/after metric to a real captured delta | Jesh | benchmark |
| 5 | 2-min demo video (screen + voiceover) | Benjy | panels done |
| 6 | Publish blog post | Sam | #3 |
| 7 | Social posts live (tag @wemakedevs + @cognee_ai) | Benjy | submission day |
| 8 | Open-source PRs to Cognee repo ($100 each) | All | start anytime |
| 9 | Final QA: clean-clone test, make demo, confirm all works | All | all above |
| 10 | Make repo public + tag v1.0 + submit form | Jesh | #9 |

---

## 📋 All 6 proposal modules — status
| Module | Status | Notes |
|---|---|---|
| Messy Desk Processor (drag-drop ingestion) | 🔄 building | /ingest-file endpoint + UploadPanel.jsx |
| Dynamic Evidence Board (graph viz) | ✅ done | Force graph with legend, node click, contradiction edges |
| Alibi Collision Engine | ✅ done | Red contradiction edges + break panel in GraphPanel |
| Missing Hours Reconstructor | 🔄 building | /missing-hours endpoint + MissingHoursPanel.jsx |
| Nexus Point (shortest path) | 🔄 building | /nexus endpoint + NexusPanel.jsx |
| Interrogation Co-Pilot | 🔄 building | /interrogation endpoint + InterrogationPanel.jsx |
| What-If Sandbox | 🔄 building | /whatif endpoint + WhatIfPanel.jsx |
| Temporal Slider | 🔄 building | Range input on TimelinePanel |

---

## 🏆 Judging criteria coverage
| Criterion | What we have | Strength |
|---|---|---|
| Potential Impact | Cross-jurisdiction evidence gap is real + expungement civic use case | ★★★★★ |
| Creativity & Innovation | 5 agentic modules, temporal reasoning, what-if sandbox, interrogation co-pilot | ★★★★★ |
| Technical Excellence | 3-way benchmark with Recall@k + MRR, all 4 Cognee APIs, async pipeline | ★★★★☆ |
| Best Use of Cognee | remember/recall(graph+vector+insights)/improve(session_ids)/forget — all for real reasons | ★★★★★ |
| User Experience | Dark theme, 8 panels, temporal slider, drag-drop, alibi break animation | ★★★★☆ |
| Presentation Quality | Blog, social posts, README with story, demo.py narrated, chart | ★★★★☆ |

---

## 🚧 Key risks remaining
- Benchmark must show graph > vector on multi-hop — if it doesn't, tighten multi-hop queries
- Demo video needs Benjy (can't be auto-generated)
- Need to publish blog + social before deadline

---

## Team
- **Sam** (`samuelshine`) — Lead · AI / backend
- **Jesh** (`jeshlin-donna`) — AI / backend  
- **Benjy** (`benjyguitar`) — frontend / product
