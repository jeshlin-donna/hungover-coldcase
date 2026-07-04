# ColdCache — 2-Minute Demo Script

**Format:** screen recording + voiceover · target 1:50–2:00

---

## OPEN (0:00–0:15) — The hook

> *"Three burglaries. Two departments. The evidence was there the whole time — but nobody had shared memory to connect it."*

> *"This is ColdCache: a durable case workspace backed by Cognee."*

---

## BEAT 1 (0:15–0:35) — Create a case + durable import

*(Open the app on the Case Home, create a new case, then land in Import Case Files and Data.)*

> *"The app no longer starts in a fake demo workspace. It starts on a real case home. Every upload, review, job, and graph belongs to a case and survives reloads."*

*(Drop a photo or PDF into the import panel.)*

> *"The file is saved durably before analysis starts. If Groq is available, we use it. If Groq is rate-limited, ColdCache can fall back to a local Ollama model instead of hard-failing."*

---

## BEAT 2 (0:35–0:55) — Review, confirm, ingest

*(Show extracted text in the review step, make a small edit, confirm.)*

> *"Every modality becomes reviewable text first. The investigator can correct it, then confirm it into the case graph. That confirmed text is what Cognee remembers."*

---

## BEAT 3 (0:55–1:15) — Evidence Board

*(Continue to the Evidence Board.)*

> *"This board is built from verified case evidence: people, locations, vehicles, and evidence items. Files stay attached as provenance instead of cluttering the graph as fake document nodes."*

*(If useful, click Rebuild knowledge.)*

> *"And if you want to rebuild from the confirmed record, reindexing is a durable background job — still safe across reloads."*

---

## BEAT 4 (1:15–1:35) — Timeline + interrogation / what-if

*(Switch to Timeline, then Interrogation or What-If.)*

> *"The same evidence powers a timeline, an interrogation assistant, and a what-if sandbox. If live LLM help is available, the answers are enriched. If not, the app still falls back to persisted case analysis instead of collapsing."*

---

## BEAT 5 (1:35–1:50) — Chat + reliability story

*(Ask a question in Case Chat.)*

> *"The case chat stays scoped to this case only. And the real differentiator is reliability: persistent jobs, per-case datasets, automatic fallback, and a backend that keeps working even when a browser tab disappears."*

---

## CLOSE (1:50–2:00)

> *"ColdCache turns evidence into durable shared memory: multimodal ingestion, per-case Cognee datasets, and a graph-backed case workspace that survives the real world."*

---

## Optional appendix for judges who ask about the older demo surface

If you also want to show the benchmark / narrated demo path, mention that the repo still keeps the older global routes and scripts for `/graph`, `/recall`, `/report`, `benchmark/benchmark.py`, and `demo/demo.py`. They are still useful, but they are no longer the primary frontend architecture.
