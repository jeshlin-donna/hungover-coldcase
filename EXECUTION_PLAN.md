# HungOver — Cold Case Connector

**The memory layer that connects the evidence humans already had.**

> Three burglaries. Two police departments. Zero shared memory. Caught after 23 months by luck — not investigation. Cognee would have connected them in one query.

- **Team:** HungOver (3) — **Sam (lead · AI/backend)**, Jesh (AI/backend), Benjy (frontend / product). Three equal owners — backend depth, retrieval rigor, and product experience each independently decide whether we win.
- **Track:** Best Use of **Open Source** (self-hosted Cognee) → MacBook per member
- **Window:** Jun 29 – Jul 5, 2026. We're on **Day 2 (Jun 30)**. Submission target: **Jul 5 EOD**, with Jul 5 as buffer.
- **AI assistant disclosure:** We use Claude/ChatGPT for code + docs. **This MUST be declared in the submission** (non-disclosure = DQ).

> **📊 Build status (2026-06-30, Day 2) — live tracker: [`PROGRESS.md`](./PROGRESS.md)**
> **Built:** repo + `memory_service` (4 APIs) · hero case (9 docs) · benchmark harness + queries · `demo.py` · FastAPI backend (live/degraded) · React frontend scaffold (3 panels) · mock server · README draft.
> **🔑 The one gate:** Priority 0 (run `smoke_test.py` on a personal machine) — nothing runs live until this pins the `# VERIFY` SDK spots.
> **Start now in parallel:** Jesh/Sam → Priority 0 · Benjy → build out frontend on mock server · Sam → source `data/raw/` corpus.

---

## 0. The North Star — how we actually win

The judges are **Cognee's own engineers**. They've seen 50 "chatbot-with-memory" submissions. We win by being the one submission that:

1. **Earns the graph win empirically.** Not a 3-file scripted trick — a real, scaled corpus where Cognee's graph traversal beats naive vector search on *multi-hop* queries, with numbers (Recall@k, MRR). A credible benchmark is one half of the moat; the other half is a product that makes the win *obvious* on screen in 30 seconds. Both halves are decisive — neither wins alone.
2. **Uses all four lifecycle APIs for real reasons** — `remember` (ingest at scale), `recall` (graph vs vector modes), `improve()` (a metric that climbs *live* when a lead is confirmed), `forget()` (record **expungement** — a genuine legal use case, not a throwaway).
3. **Tells one gripping, specific story on top** — the Daniel Marsh burglary series — so the demo lands emotionally in 30 seconds.
4. **Looks polished** — a real UI with a live graph, 3-way side-by-side retrieval, and a clean before/after.

### Scoring map (every criterion → the concrete thing that earns it)

| Judging criterion | What earns it for us | Owner |
|---|---|---|
| Potential Impact | Cross-jurisdiction siloed evidence is a real, serious problem; expungement framing shows civic responsibility | Jesh (narrative) |
| Creativity & Innovation | Not on their sample list; graph-over-time investigation + self-improving leads | Sam |
| Technical Excellence | Real corpus, 3-way benchmark, async status polling, clean architecture | Jesh |
| **Best Use of Cognee** (heaviest) | All 4 APIs used *correctly* per docs; graph modes (`GRAPH_COMPLETION`/`INSIGHTS`); `improve()` with `session_ids`; `forget()` for expungement | Jesh + Sam |
| User Experience | Live graph viz, split-screen comparison, one-click demo flow | Benjy |
| Presentation Quality | README opens with the human story; tight 2-min demo video; benchmark chart | All |

### Guardrails (don't lose points)
- **Framing:** always *"shared memory connects evidence humans already had"* — **never** "AI predicts who's guilty." No predictive-policing language anywhere.
- **Disclaimer prominent:** all data is synthetic/public; demo is illustrative, not operational.
- **It must RUN.** A demo that crashes loses instantly. Priority 0 below de-risks this on Day 2.

---

## 1. What we're shipping (architecture)

```
                ┌─────────────────────────────────────────────┐
   data/  ──►   │  ingestion pipeline (Sam)                   │
  (corpus +     │  remember() / add() + cognify()  + status   │
   hero case)   └───────────────┬─────────────────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │  memory_service.py      │  ← Jesh (core abstraction over Cognee)
                    │  remember/recall/        │
                    │  improve/forget          │
                    └───────┬─────────┬────────┘
                            │         │
              ┌─────────────▼──┐   ┌──▼───────────────┐
              │ FastAPI (Sam)  │   │ benchmark/ (Jesh)│  ← 3-way: naive vs RAG vs GRAPH
              │ /recall /hunch │   │ recall@k, MRR    │
              │ /improve /forget│  └──────────────────┘
              └───────┬─────────┘
                      │ REST/JSON
              ┌───────▼──────────────────────────────┐
              │ React frontend (Benjy)                │
              │ • live force-graph of the case web    │
              │ • 3-way split-screen retrieval        │
              │ • timeline view + expungement toggle  │
              └───────────────────────────────────────┘
```

**Stack:** Python 3.11 + Cognee (self-hosted OSS) + FastAPI · React + Vite + a force-graph lib (react-force-graph or Cytoscape.js) · sentence-transformers for the naive baseline · self-hosted graph/vector backends per Cognee defaults (Kuzu/LanceDB or Neo4j+Qdrant if time).

---

## 2. Roles & ownership

**Three equal owners.** Each pillar independently decides the outcome — there is no "support" role here. A flawless benchmark behind a clumsy UI loses; a beautiful UI with no real Cognee depth loses. We need all three at full strength.

- **Sam (lead · AI/backend):** corpus sourcing + cleaning, hero case authoring, ingestion pipeline (async status polling), FastAPI endpoints, `forget()`/expungement flow, demo orchestration, blog post (side track). Runs standups and keeps the plan on track.
- **Jesh (AI/backend):** Cognee core integration, `memory_service` abstraction, the benchmark (methodology + harness + chart), the `improve()` self-learning loop, README technical sections, submission form. Owns Priority 0.
- **Benjy (frontend / product):** the entire user-facing experience — React app, live graph visualization, 3-way comparison UI, timeline + expungement/improve animations, and the 2-min demo video the judges actually watch. Owns how the whole project *reads* (UX + Presentation = 2 of the 6 scoring criteria). Social posts (side track).
- **Shared:** daily 15-min standup (async on WhatsApp ok), README, final QA.

---

## 3. Day-by-day plan (minute-level, with owners)

> Tags: **[JESH] [SAM] [BENJY] [ALL]**. Each task has an estimate. Evenings + big weekend push (everyone's working/college).
> `[ ]` = todo. Check off in this file as you go (commit it to the repo).

### DAY 2 — Tue Jun 30 (TODAY): De-risk + foundations  🎯 *Goal: Cognee provably runs, repo stands up, corpus identified*

**Priority 0 — prove the SDK works before anything else [JESH] (~30 min, one command)**
- [ ] Run **`./setup.sh`** — auto: Python≥3.10 check, venv, `pip install -r requirements.txt`, `.env` scaffold (5 min)
- [ ] Add `LLM_API_KEY` to `.env` (OpenAI key, or a local/cheaper provider per Cognee setup docs), then `./setup.sh --smoke` (10 min)
- [ ] Smoke test runs `remember → recall → improve → forget` against the **live** SDK (auto via setup.sh)
- [ ] **Record the real return shapes** of `recall()` for each search type into `docs/API_NOTES.md` — this is what the old scaffold guessed at; we verify it for real (15 min)
- [ ] Confirm `improve(session_ids=...)` and `forget(dataset=...)` signatures actually run (12 min)

**Repo + skeleton [JESH] (~30 min)**
- [x] `git init`, push to a **private** GitHub repo `hungover-coldcase`. Add `.gitignore` ✅ pushed to github.com/jeshlin-donna/hungover-coldcase
- [x] Commit `memory_service.py` skeleton with the 4 APIs + `wait_for_indexing()` status-polling helper ✅

**Corpus sourcing [SAM] (~90 min)**
- [ ] Identify 1–2 **public** datasets for the noise corpus: e.g. public police-blotter / incident logs, Crime Data Explorer (FBI), court-record samples, NamUs-style public case summaries. Document license/source in `data/SOURCES.md` (45 min)
- [ ] Download ~200–500 records into `data/raw/` (30 min)
- [ ] Sanity-check format; note the fields we'll ingest (date, location, MO, tool marks, vehicle, narrative) (15 min)

**Frontend bootstrap [BENJY] (~60 min)**
- [x] Vite + React scaffold with `react-force-graph-2d` + fetch client ✅ (done — `frontend/`; Benjy now builds out the panels)
- [ ] Stub 3 panels (Graph / Retrieval compare / Timeline) with mock JSON so UI dev isn't blocked on backend (45 min)

**EOD Day 2 deliverables:** Cognee verified ✓ · repo live ✓ · corpus chosen + downloaded ✓ · UI skeleton renders ✓

---

### DAY 3 — Wed Jul 1: Data + memory core  🎯 *Goal: full corpus ingested and queryable*

**Hero case [SAM] (~75 min)**
- [ ] Author the Daniel Marsh 3-burglary case files + forensic reports + witness statements (reuse from old scaffold, tighten). Plant them so they're *connectable but not obvious* — same tool-mark dims, vehicle, MO across 2 jurisdictions (60 min)
- [ ] Add the killer detail: a forensic line *"recommend regional database check — not actioned"* (15 min)

**Ingestion pipeline [SAM] (~90 min)**
- [ ] `scripts/ingest.py`: load `data/raw/*` + hero case → `remember()`/`add()`+`cognify()` with `run_in_background=True` (60 min)
- [ ] Poll `datasets.get_status()` until indexed (no blind `sleep`) (30 min)

**memory_service [JESH] (~120 min)**
- [ ] `recall(query, mode)` wrapper exposing `RAG_COMPLETION`, `GRAPH_COMPLETION`, `INSIGHTS`, `CHUNKS` (45 min)
- [ ] `log_hunch(text, session_id)` → session memory (`self_improvement=False`) (20 min)
- [ ] `resolve_case(dataset, session_ids)` → `improve()` bridging session → permanent (25 min)
- [ ] `expunge(dataset)` → `forget()` (15 min)
- [ ] Unit-smoke each against live SDK; update `API_NOTES.md` (15 min)

**Graph viz wiring [BENJY] (~120 min)**
- [ ] Endpoint contract agreed with Jesh/Sam (nodes = entities, edges = relations) (15 min)
- [ ] Render the live case graph from real ingested data; node click → details panel (105 min)

**EOD Day 3:** corpus + hero case ingested ✓ · all 4 APIs callable via `memory_service` ✓ · graph renders real nodes ✓

---

### DAY 4 — Thu Jul 2: The benchmark (our moat) + endpoints  🎯 *Goal: numbers that prove graph > vector*

**Benchmark [JESH] (~180 min) — THE differentiator, do it right**
- [ ] Query set: 25–30 queries in `benchmark/queries.json`, labeled `single_hop` vs `multi_hop`, each with gold relevant doc IDs (60 min)
- [ ] 3 retrievers: (a) naive cosine (sentence-transformers `all-MiniLM-L6-v2` top-k), (b) Cognee `RAG_COMPLETION`, (c) Cognee `GRAPH_COMPLETION`/`INSIGHTS` (45 min)
- [ ] Metrics: Recall@3, Recall@5, MRR; + LLM-judged answer correctness for completion modes (45 min)
- [ ] Output `benchmark/results.json` + a matplotlib chart `benchmark/chart.png` (graph ≈ vector on single-hop, graph **>>** vector on multi-hop) (30 min)

**FastAPI [SAM] (~120 min)**
- [ ] `/recall` (mode param), `/hunch`, `/resolve`, `/expunge`, `/graph` (nodes+edges), `/benchmark` (serves results) (90 min)
- [ ] CORS + error handling so the demo never hard-crashes; fallback canned response if a call times out (30 min)

**3-way compare UI [BENJY] (~150 min)**
- [ ] Split-screen: same query → Naive vector | Cognee RAG | Cognee Graph, side by side (90 min)
- [ ] Highlight the multi-hop query where only Graph connects the 3 cases (60 min)

**EOD Day 4:** benchmark chart exists with real numbers ✓ · all endpoints live ✓ · 3-way compare works ✓

---

### DAY 5 — Fri Jul 3: improve() + forget() live moments + integration  🎯 *Goal: the two "wow" interactions work end-to-end*

- [ ] **[JESH]** `improve()` live loop: query → confirm lead → `improve(session_ids)` → re-query → **show recall/score jump**. Capture the before/after numbers (90 min)
- [ ] **[SAM]** Expungement flow: seal Marsh's record → `forget(dataset)` → show connected subgraph vanish, unrelated cases intact (75 min)
- [ ] **[BENJY]** Timeline view (3 incidents across months) + the "improve" and "expunge" buttons wired to endpoints; animate the graph update (150 min)
- [ ] **[ALL]** First full integration run-through end-to-end; log every bug to `ISSUES.md` (60 min)

**EOD Day 5:** improve() metric visibly climbs ✓ · expungement visibly prunes ✓ · full happy-path runs ✓

---

### DAY 6 — Sat Jul 4 (big push): polish + demo video + README + blog  🎯 *Goal: submission-ready*

- [ ] **[JESH]** README: open with the Marsh story → problem → architecture → benchmark chart+table → API usage → setup. Add **AI-assistant disclosure** section (120 min)
- [ ] **[JESH]** Reproducibility: `make demo` / one-command setup script; test on a clean clone (60 min)
- [ ] **[SAM]** `demo/demo.py` — the exact 5-phase narrated CLI run (ingest → hunch → multi-hop recall → resolve/improve → expunge) (75 min)
- [ ] **[SAM]** Blog post draft (side track → Keychron): "How we taught an investigation to remember" — include the benchmark numbers (120 min)
- [ ] **[BENJY]** UX polish pass (loading states, empty states, the 30-sec hero flow), record **2-min demo video** (screen + voiceover) (180 min)
- [ ] **[BENJY]** 2–3 social posts tagging @wemakedevs + Cognee (side track → swag) (45 min)
- [ ] **[ALL]** Dry-run the live demo twice; cut anything that flakes (60 min)

**EOD Day 6:** README done · video recorded · demo bulletproof · blog drafted

---

### DAY 7 — Sun Jul 5: final QA + submit  🎯 *Goal: submitted with buffer*

- [ ] **[ALL]** Clean-clone test: fresh machine/container, follow README, confirm `make demo` works (60 min)
- [ ] **[JESH]** Make repo public, final commit, tag `v1.0` (20 min)
- [ ] **[JESH]** Fill submission form: links (repo, video, blog), 4-API usage writeup, **AI disclosure**, team members (45 min)
- [ ] **[SAM]** Publish blog; **[BENJY]** publish social posts (30 min)
- [ ] **[ALL]** Submit **early** (don't wait for the deadline) (15 min)
- [ ] Buffer for anything broken.

---

## 4. Definition of Done / submission checklist
- [ ] Public GitHub repo, clean README opening with the story + benchmark chart
- [ ] All 4 Cognee APIs used and *documented* where each is used
- [ ] Real corpus + benchmark showing graph > vector on multi-hop (chart + table)
- [ ] 2-min demo video + live demo that runs from a clean clone
- [ ] AI-assistant usage declared
- [ ] Disclaimer (synthetic/public data) prominent
- [ ] Blog published (side track), social posts up (side track)

---

## 5. Risk register
| Risk | Mitigation | Owner |
|---|---|---|
| SDK behaves differently than docs | Priority 0 on Day 2 verifies real return shapes first | Jesh |
| Benchmark shows graph ≈ vector | Design multi-hop queries that *structurally* need traversal; if still weak, lead with `INSIGHTS`/relationship extraction | Jesh |
| Live demo crashes | Canned-fallback responses + pre-recorded video backup | Sam/Benjy |
| Corpus licensing | Only public/synthetic; document sources | Sam |
| "Predictive policing" optics | Strict "connect existing evidence" framing + disclaimer | All |
| Time slips (everyone busy) | Weekend (Jul 4) is the load-bearing day; protect it | All |

---

## 6. Parallel track — Open Source PRs ($100 each, top 20) — START NOW
Stacks on top of the main prize. **Max 5 PRs/person**, no spam, no typo-only PRs (instant reject + ban risk).
- [ ] **[ALL]** Each: browse `github.com/topoteretes/cognee` issues, comment to claim, **wait for assignment** before coding
- [ ] **[JESH/SAM]** Target Python core / SDK / docs-with-code issues (our strength)
- [ ] **[BENJY]** Target JS integrations / docs / examples issues
- [ ] Aim 1–2 *real* PRs each this week around the build work (things we touch anyway → natural fixes)

---

## 7. Naming / submission copy
- **Team:** HungOver
- **Product:** Cold Case Connector *(working name — alt: "Throughline", "Coldwire")*
- **One-liner:** "Every detective had a piece of the evidence. Nobody had the shared memory to connect it. Cognee does."
- **Tagline:** Built on self-hosted, open-source Cognee — the memory layer that doesn't wake up in Vegas with no memory of last night.
