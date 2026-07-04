# ColdCache — 2-Minute Demo Script

**Format:** screen recording + voiceover · target 1:50–2:00
**Presenter:** Benjy (or whoever records)
**Tone:** calm, precise, slightly dramatic — let the product speak

---

## OPEN (0:00–0:15) — The hook, no product yet

> *"Three burglaries. Two police departments. The same offender, the same MO, the same getaway vehicle — every time. And yet it took 23 months and a lucky doorbell camera to catch him. Not because the evidence wasn't there. Because nobody had shared memory across departments."*

*(Show the README hero quote on screen, or the GitHub repo — let it breathe for 5 seconds)*

> *"This is ColdCache. We built it to show what happens when you give an investigation team that shared memory — powered by Cognee's knowledge graph."*

---

## BEAT 1 (0:15–0:35) — Import Case Files and Data

*(Switch to the Upload tab)*

> *"An investigator drops a crime scene photo into Import Case Files and Data."*

*(Drag a photo onto the drop zone — show the "Analyzing image…" state)*

> *"Claude vision extracts a forensic description — the vehicle, the partial plate, the timestamp. That description flows straight into Cognee's knowledge graph via `remember()`. Same graph, same nodes, instantly queryable."*

*(Show the extracted description appearing in the ingested list)*

> *"You can drop a 911 call recording and it gets transcribed by Whisper. A scanned warrant — PyMuPDF extracts it, scanned pages go through vision. A phone records spreadsheet — parsed by pandas. Everything ends up in the same graph."*

---

## BEAT 2 (0:35–0:55) — The cross-jurisdiction link (Graph vs Vector)

*(Switch to the Graph vs Vector tab, type the multi-hop query: "Which suspect appears in both the Millbrook Heights and Riverside View burglaries?")*

> *"Now watch the difference between vector search and graph traversal on a multi-hop query."*

*(Show the 3 columns loading)*

> *"Naive vector — retrieves documents about one case or the other. No connection. Cognee RAG — slightly better. Cognee graph —"*

*(Point at the GRAPH WINS banner)*

> *"— follows the entity relationships across both case files. Same suspect, same MO, same vehicle. Two departments, one graph. This is what the benchmark proves: naive vector R@5 drops to 0.53 on multi-hop queries. The graph closes that gap."*

---

## BEAT 3 (0:55–1:15) — The alibi break (Evidence Board)

*(Switch to Case Graph tab — the force-directed graph is visible)*

> *"Every node in this graph is a real entity extracted from the case files by Cognee. People, locations, vehicles, evidence items."*

*(Zoom toward the red glowing edge between Marsh and the alibi)*

> *"That red edge is the alibi break. The suspect told officers he was 300 miles out of state. The motel receipt in the graph puts him 4.2 miles from the scene at 00:48 the same night."*

> *"Cognee built the unified graph. Our contradiction check found the conflict. The investigator sees it — no hallucination, no guessing, every fact is already in the evidence."*

---

## BEAT 4 (1:15–1:35) — Interrogation + What-If

*(Switch to Interrogation tab)*

> *"The Interrogation Co-Pilot reads the graph and generates trap questions — questions where the answer is already in the evidence so the suspect can't lie without contradiction."*

*(Click to expand one question, show the trap text and evidence-held-back chips)*

*(Switch to What-If tab, type: "What if the witness placed Marsh at the Riverside scene directly?")*

> *"The What-If sandbox recalculates confidence across the graph. Change a fact, see how the whole case shifts. This is graph reasoning — not just retrieval."*

---

## BEAT 5 (1:35–1:50) — Resolve & Expunge

*(Click the Improve button in the header)*

> *"During the investigation a detective logged hunches into session memory — things they suspected but couldn't prove yet. On case resolution, `improve()` merges those sessions into the permanent graph and re-weights the connections."*

*(Show the before/after MRR metric card)*

> *"And when a court orders a record sealed — `forget()` surgically removes that dataset's subgraph. The rest of the graph is untouched. Real legal use case, not a demo gimmick."*

*(Click expunge on a node in the graph, watch the 2-step fade animation)*

---

## CLOSE (1:50–2:00)

> *"ColdCache. All 4 Cognee lifecycle APIs — remember, recall, improve, forget — each mapped to a real investigative need. Multimodal ingestion. A live benchmark proving graph beats vector where it counts. And a story that's real: the evidence was always there. The graph just had to connect it."*

*(End on the GitHub repo URL or the force-graph visual)*

---

## Recording tips

- Record at 1920×1080, browser zoomed to 125% so text is readable
- Use the dark theme (default) — it looks cinematic on screen
- Pre-load the app with the hero case already ingested so panels respond instantly
- Have the demo image ready to drag-drop (a staged "crime scene" photo works well)
- Keep the narration pace slightly slower than feels natural — it reads faster on playback
- Cut silences between beats; total with cuts should land at ~1:50

## Pre-demo checklist

- [ ] `source .venv/bin/activate && uvicorn backend.main:app --port 8000 --reload`
- [ ] `cd frontend && npm run dev` → confirm http://localhost:5173 loads
- [ ] `GET /health` returns `{"mode": "live"}`
- [ ] Hero case already ingested (`python scripts/ingest.py`) — don't ingest live, too slow
- [ ] Drop-zone image ready on desktop
- [ ] All 8 tabs load without errors
- [ ] Benchmark chart.png is generated (shows in `/benchmark` tab)
