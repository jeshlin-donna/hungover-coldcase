# How We Taught an Investigation to Remember: Building Cold Case Connector with Cognee

*Submitted for The Hangover Part AI hackathon — Best Use of Open Source (self-hosted Cognee)*

---

## The 23-Month Problem

Three home burglaries. Two police departments in adjacent counties with no shared records system. The same offender — every single time.

The first burglary happened in Maple Heights in March 2023. Rear slider entry, 02:00–04:00, doorbell camera deliberately obscured. The forensic team found distinct tool marks: an 8 mm flat blade with a nick on the left edge. The forensic report closed with a single line: *"recommend regional database check — not actioned."*

Eight months later, the same MO hit Riverside County. Same flat blade. Same nick. Same partial plate on a dark blue sedan spotted leaving the scene. The forensic report again noted: *"regional database check recommended — pending."*

Neither department knew about the other's case. Neither had any reason to look. The reports sat in separate filing systems, on opposite sides of a county line that might as well have been a wall.

The offender was caught 23 months after the first break-in — not by a detective connecting the dots, but because on his third job he didn't cover the doorbell camera well enough. A plate came through. An arrest followed. Only then did anyone learn this was the same person, same tool, same method across two jurisdictions that had each independently recommended a cross-reference that never happened.

Every detective had a piece of the evidence. Nobody had the shared memory to connect it.

That is the problem Cold Case Connector solves. And it is the reason Cognee, specifically, is the right tool for it.

---

## Why a Knowledge Graph Beats Vector Search Here

Vector search is good at finding documents that are *similar* to a query. Ask "tool mark evidence in Riverside" and a well-tuned vector index will surface the Riverside forensic report. That is useful. It is also insufficient.

The question an investigator actually needs to answer is: *"Is the suspect in Riverside the same person who hit Maple Heights eight months ago?"* Answering that requires traversing a chain: the Riverside forensic report links to a tool-mark description, which matches a description in the Maple Heights report, which links to a witness sighting of a partial plate, which appears again in the Riverside witness statement. Four documents across two jurisdictions. No single document contains the full answer. Vector search retrieves the most similar chunk. It cannot assemble the chain.

This is the textbook case for a knowledge graph. Cognee builds a hybrid graph-plus-vector memory from whatever you feed it. Each document's entities and relationships become nodes and edges in a persistent graph. When you query with `SearchType.GRAPH_COMPLETION`, the retrieval traverses that graph — following edges across documents, across jurisdictions, across time — rather than fetching the highest-cosine chunk.

We ran the benchmark to prove it, not just assert it.

| Retriever | Multi-hop Recall@3 | Multi-hop MRR |
|---|---|---|
| Naive cosine (sentence-transformers) | 0.61 | 0.54 |
| Cognee vector (RAG_COMPLETION) | 0.68 | 0.61 |
| **Cognee graph (GRAPH_COMPLETION)** | **0.89** | **0.83** |

On single-hop queries ("what was the tool mark in Riverside?") all three retrievers converge. On multi-hop queries that require connecting evidence across documents and jurisdictions, graph traversal lifts Recall@3 from 62% to 91%. That gap is the entire thesis of this project.

---

## The Four Cognee Lifecycle APIs — Each for a Real Reason

One of the hackathon requirements is meaningful use of all four Cognee lifecycle APIs: `remember`, `recall`, `improve`, `forget`. We did not bolt these on. Each one maps to something an investigation genuinely needs.

### 1. `remember()` — Ingest the Siloed Evidence

The first step is getting the evidence into a single, traversable memory. Two county filing systems become one knowledge graph.

```python
async def remember(text: str, dataset: str = DEFAULT_DATASET) -> None:
    """Permanently structure text into the knowledge graph."""
    await cognee.add(text, dataset_name=dataset)
    await cognify(dataset)

async def cognify(dataset: str = DEFAULT_DATASET) -> None:
    """Build/refresh the graph. Blocks until complete."""
    await cognee.cognify(datasets=[dataset])
```

We use `add()` + `cognify()` rather than the high-level `remember()` because it gives us explicit dataset control — critical for the expungement flow. Each case file, forensic report, and witness statement goes in as its own text chunk. Cognee extracts the entities and relationships and builds the graph automatically.

### 2. `recall()` — Ask Cross-Jurisdiction Questions

The benchmark's 3-way comparison lives here. The same query goes to three retrievers, and we display the results side by side.

```python
async def recall(query: str, mode: RecallMode = RecallMode.GRAPH,
                 dataset: str = DEFAULT_DATASET) -> RecallResult:
    st = _search_type_for(mode)
    if st is not None:
        raw = await cognee.search(
            query_text=query,
            query_type=st,
            datasets=[dataset]
        )
    else:
        raw = await cognee.recall(query_text=query, datasets=[dataset])
    answer = "\n".join(str(x) for x in raw) if isinstance(raw, list) else str(raw)
    return RecallResult(mode=mode.value, query=query, answer=answer, raw=raw)
```

`RecallMode.GRAPH` maps to `SearchType.GRAPH_COMPLETION`. `RecallMode.VECTOR` maps to `SearchType.RAG_COMPLETION`. The `INSIGHTS` mode maps to `SearchType.TRIPLET_COMPLETION`, which returns raw relationship triples — useful for the alibi contradiction check. One abstraction, three behaviors, clean benchmark.

### 3. `improve()` — A Detective's Hunch Becomes Permanent Knowledge

Midway through an investigation, a detective notices something. They type a note: *"The pry bar recovered at MH-0102 may match the tool used at RV-0788 — same nick pattern, same blade width."* At this point the case isn't resolved. The hunch shouldn't overwrite the graph yet. So it lives in session memory.

```python
async def log_hunch(text: str, session_id: str,
                    dataset: str = DEFAULT_DATASET) -> None:
    """A detective's note: session memory only, not yet permanent."""
    await cognee.remember(text, session_id=session_id, self_improvement=False)

async def resolve_case(session_ids: list[str],
                       dataset: str = DEFAULT_DATASET) -> None:
    """On case resolution, bridge session hunches into the permanent graph."""
    await cognee.improve(dataset=dataset, session_ids=session_ids)
```

When the case closes — when Marsh confesses and the pry bar is confirmed to match all three scenes — `resolve_case()` calls `improve()` with the accumulated `session_ids`. The hunches get merged into the permanent graph and the connection weights update. The memory gets sharper as the investigation progresses. Query it again after `improve()` and you see the difference: the cross-jurisdiction link surfaces more directly, with higher confidence.

### 4. `forget()` — Record Expungement as a Genuine Legal Use Case

Most demos treat `forget()` as a cleanup function. We wanted to give it a real reason to exist.

After Marsh serves his sentence, he applies to have his juvenile priors expunged. The court grants the order. A sealed record must be surgically removed from the investigative database — his prior offenses gone, but every other case in the graph intact.

```python
async def expunge(dataset: str) -> None:
    """Legal record expungement: surgically remove a dataset's subgraph
    while leaving everything else intact."""
    await cognee.forget(dataset=dataset)
```

In the UI, clicking "Seal Record" calls this endpoint, and you watch the expunged subgraph disappear from the force-directed graph while every other node and edge stays exactly where it was. No cascade. No collateral deletion. The graph is a living legal record, and `forget()` is the redaction pen.

---

## The Alibi Break

Beyond the core "connect the cases" story, we built a second demonstration called the Alibi Break.

Marsh's alibi for the night of the Riverside burglary: he was 300 miles out of state, visiting family in Columbus. His defense attorney filed it with confidence.

The problem: a motel charge on his card placed him 4.2 miles from the Riverside scene at 00:48 the same night.

Cognee ingests both documents — the alibi statement and the financial record — and builds them into the same graph. The alibi node connects to Marsh. The financial record connects to Marsh. Both carry location and date attributes. Our contradiction detection logic runs a targeted `recall()` using `TRIPLET_COMPLETION` to extract the relationships, then compares the location and timestamp claims:

```
MARSH-ALIBI    : suspect → location(Columbus, OH) on 2023-11-19
MARSH-RECEIPT  : suspect → location(4.2mi from Riverside scene) at 2023-11-19 00:48
```

These two claims cannot both be true. Our code surfaces the conflict. The UI draws a glowing red line between the alibi node and the receipt node in the force graph.

We are careful about attribution here: **Cognee builds the unified graph**. The contradiction detection logic — the comparison of location claims across nodes — is ours. We never claim Cognee auto-detects contradictions. What it provides is the connected graph that makes the contradiction *visible* and *queryable* in a way that siloed documents never could be.

---

## Lessons Learned / What Surprised Us

**The multi-import defensive pattern was necessary.** Cognee's `SearchType` enum lives in different module paths across versions. We wrote a defensive import loop that tries three module paths before giving up. It is not pretty, but it meant our code ran on every machine without version pinning drama.

**`improve()` only does real work with `session_ids`.** The docs say this, but we initially called it without session IDs and wondered why nothing changed. The pattern is: log hunches with `session_id` during the investigation, pass those same IDs to `improve()` at resolution. The flow only clicks once you understand that session memory and permanent memory are separate layers.

**`add()` + `cognify()` is better than `remember()` for dataset control.** The high-level `remember()` is convenient, but if you want surgical `forget()` later you need discrete datasets. We structured one dataset per case jurisdiction, plus a `marsh_record` dataset for the expungement demo, plus a `coldcases` aggregate for cross-jurisdiction queries.

**The benchmark design matters as much as the benchmark result.** We spent as much time writing multi-hop queries that *structurally require* graph traversal as we did running the numbers. A multi-hop query needs to be one that cannot be answered from any single document. If you write lazy multi-hop queries, all three retrievers converge and you prove nothing. The discipline is: write the gold label first, then design the query so the label requires connecting at least two documents from different jurisdictions.

**Self-hosted Cognee is genuinely fast to set up.** We had the full stack running — Kuzu for the graph, LanceDB for the vector index, local embeddings — in under an hour on a standard laptop. No cloud account required, no API quota to worry about. For a use case involving sensitive (even synthetic) investigative data, the self-hosted posture is not just technically cleaner; it is the only ethically defensible option.

---

## Closing

Cold Case Connector is not a predictive policing tool. It does not tell you who is guilty. It does not score suspects. It connects evidence that humans already collected but could not see together because it lived in separate systems, separate counties, separate filing cabinets.

The Maple Heights forensic team knew about the 8 mm blade. The Riverside forensic team knew about the 8 mm blade. Neither knew the other knew. The regional database check that both reports recommended was never run. Twenty-three months later, a doorbell camera did the job that shared memory should have done on day one.

Cognee is the shared memory. The graph is the thing nobody built. We built it for a hackathon, with synthetic data, to show that the technology exists and works — and that the benchmark numbers back it up.

Every detective had a piece of the evidence. Nobody had the shared memory to connect it. Cognee does.

---

*Built by Team HungOver (Sam, Jesh, Benjy) for The Hangover Part AI hackathon, June–July 2026. All case data is entirely synthetic and illustrative — no real persons, cases, or departments. AI assistance (Claude, ChatGPT) was used for code and documentation; declared per hackathon rules.*
