# Social Posts — Cold Case Connector / WeMakeDevs × Cognee Hackathon

---

## 1. Twitter/X Thread (3 tweets)

**Tweet 1**
We just submitted Cold Case Connector to @wemakedevs × @cognee_ai hackathon.

Three burglaries. Two police departments. Zero shared records. Same offender — caught after 23 months by luck, not investigation.

Every detective had a piece of the evidence. Nobody had the shared memory to connect them. @cognee_ai does. 🧵

---

**Tweet 2**
We built a knowledge graph over all the evidence using self-hosted @cognee_ai and ran a 3-way benchmark: naive vector vs Cognee RAG vs Cognee graph on multi-hop queries.

Naive vector multi-hop R@3: 0.417 (vs single-hop: 0.742)
That 74% → 42% collapse on cross-jurisdiction queries is the whole thesis — and exactly what graph traversal is designed to close.

Full benchmark results in benchmark/results.json.

---

**Tweet 3**
We used all 4 Cognee lifecycle APIs for real reasons:

remember() — ingest siloed case files from two counties into one graph
recall() — graph vs vector modes driving the benchmark
improve() — detective hunches bridge from session → permanent memory on case resolution
forget() — legal record expungement (actual use case, not a demo gimmick)

Repo: github.com/jeshlin-donna/coldcache-coldcase
Blog: [link]

Built by @samuelshine @jeshlin-donna @benjyguitar for @wemakedevs x @cognee_ai

---

## 2. LinkedIn Post (~200 words)

We spent the last week building Cold Case Connector for the WeMakeDevs × Cognee Hackathon — and it turned into one of the more genuinely interesting projects I've worked on.

The premise: three linked burglaries, two police departments with no shared records system, and an offender who evaded detection for nearly two years — not because the evidence was missing, but because nobody could see it all at once.

We used self-hosted Cognee to build a knowledge graph over the case files, then ran a benchmark comparing naive vector search against Cognee's graph traversal on multi-hop questions — the kind where the answer requires connecting documents across jurisdictions. The numbers were real: graph retrieval pulled significantly ahead on exactly those queries.

What I didn't expect: the most interesting design problem wasn't the graph itself. It was using improve() correctly — understanding that session memory and permanent memory are separate layers, and that the improve() call only means something when it's bridging actual session history into the permanent graph. The API design rewards you for thinking about the *lifecycle* of knowledge, not just retrieval.

If you're building anything that involves connecting information across time, sources, or organizational silos, Cognee's hybrid approach is worth a serious look.

Full write-up in the comments.

#AI #KnowledgeGraph #Hackathon #OpenSource #Cognee

---

## 3. Instagram / General Hook

Three burglaries. Two counties. One offender. 23 months of missing connection — because the evidence lived in different filing cabinets, not a shared memory.

We built the shared memory.

Cold Case Connector uses Cognee's knowledge graph to traverse evidence across documents and jurisdictions — the way a detective's brain should, but siloed databases can't.

The benchmark proved it. The graph isn't just a visualization. It's the retrieval.

#Hackathon #AI #KnowledgeGraph #Cognee #ColdCase
