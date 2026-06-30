"""
benchmark.py — the moat. Proves Cognee's graph beats naive vector on MULTI-HOP queries.

Three retrievers, same corpus, same queries:
    1. naive_vector  — sentence-transformers + cosine top-k   (fully offline, always runs)
    2. cognee_vector — Cognee SearchType.CHUNKS                (vector retrieval inside Cognee)
    3. cognee_graph  — Cognee SearchType.INSIGHTS/GRAPH        (graph traversal — our edge)

Metrics: Recall@3, Recall@5, MRR, split by single_hop vs multi_hop.
Hypothesis: all three tie on single_hop; cognee_graph pulls ahead on multi_hop.

    python benchmark/benchmark.py            # full run (needs cognee + LLM_API_KEY)
    python benchmark/benchmark.py --naive    # naive baseline only (no SDK needed)

Doc-ID extraction (the one tricky part): every hero-case doc embeds a `DOC_ID: ...`
header, so we map ANY retriever's output to gold IDs by regex-scanning its stringified
result for known DOC_IDs, in order of appearance. Shape-agnostic — works whether Cognee
returns chunks, nodes, or a synthesized answer. # VERIFY against real output, then
tighten to use proper source metadata if available.
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / "data" / "hero_case"
RAW = ROOT / "data" / "raw"
QUERIES = ROOT / "benchmark" / "queries.json"
OUT_JSON = ROOT / "benchmark" / "results.json"
OUT_CHART = ROOT / "benchmark" / "chart.png"

DOC_ID_RE = re.compile(r"DOC_ID:\s*([A-Z0-9\-]+)")
K_VALUES = (3, 5)


# --------------------------- corpus ---------------------------
def load_docs() -> dict[str, str]:
    """Return {doc_id: text}. Hero case uses its DOC_ID header; raw files fall back to
    their filename stem as the id."""
    docs: dict[str, str] = {}
    for path in sorted(glob.glob(str(HERO / "*.md"))):
        text = Path(path).read_text()
        m = DOC_ID_RE.search(text)
        doc_id = m.group(1) if m else Path(path).stem
        if doc_id.startswith("00") or "README" in doc_id:  # skip the readme
            continue
        docs[doc_id] = text
    for path in sorted(glob.glob(str(RAW / "*"))):
        if Path(path).is_file() and not path.endswith(".gitkeep"):
            docs[Path(path).stem] = Path(path).read_text(errors="ignore")
    return docs


def known_ids(docs: dict[str, str]) -> list[str]:
    # longest first so e.g. MH-0312-FOR matches before MH-0312
    return sorted(docs.keys(), key=len, reverse=True)


def extract_ranked_ids(raw, ids: list[str]) -> list[str]:
    """Map a retriever's raw output to an ordered, de-duped list of gold doc IDs."""
    text = raw if isinstance(raw, str) else str(raw)
    seen, ranked = set(), []
    # find ids in order of first appearance
    positions = []
    for did in ids:
        idx = text.find(did)
        if idx >= 0:
            positions.append((idx, did))
    for _, did in sorted(positions):
        if did not in seen:
            seen.add(did)
            ranked.append(did)
    return ranked


# --------------------------- metrics ---------------------------
def recall_at_k(ranked: list[str], gold: list[str], k: int) -> float:
    if not gold:
        return 0.0
    topk = set(ranked[:k])
    return len(topk & set(gold)) / len(set(gold))


def mrr(ranked: list[str], gold: list[str]) -> float:
    gold_set = set(gold)
    for i, did in enumerate(ranked, start=1):
        if did in gold_set:
            return 1.0 / i
    return 0.0


# --------------------------- retrievers ---------------------------
class NaiveVector:
    """sentence-transformers + cosine. The honest baseline every judge expects."""
    name = "naive_vector"

    def __init__(self, docs: dict[str, str]):
        from sentence_transformers import SentenceTransformer
        import numpy as np
        self.np = np
        model_name = os.getenv("BASELINE_EMBED_MODEL",
                               "sentence-transformers/all-MiniLM-L6-v2")
        self.model = SentenceTransformer(model_name)
        self.ids = list(docs.keys())
        self.emb = self.model.encode(list(docs.values()), normalize_embeddings=True)

    async def retrieve(self, query: str) -> list[str]:
        q = self.model.encode([query], normalize_embeddings=True)[0]
        sims = self.emb @ q
        order = self.np.argsort(-sims)
        return [self.ids[i] for i in order]


class CogneeRetriever:
    """Wraps memory_service.recall in a given mode and maps results -> doc IDs."""
    def __init__(self, mode, ids: list[str], name: str):
        self.mode, self.ids, self.name = mode, ids, name

    async def retrieve(self, query: str) -> list[str]:
        import memory_service as mem
        res = await mem.recall(query, mode=self.mode)
        return extract_ranked_ids(res.raw, self.ids)


# --------------------------- run ---------------------------
async def evaluate(retriever, queries: list[dict]) -> dict:
    rows = []
    for q in queries:
        ranked = await retriever.retrieve(q["query"])
        rows.append({
            "id": q["id"], "type": q["type"],
            "recall@3": recall_at_k(ranked, q["gold"], 3),
            "recall@5": recall_at_k(ranked, q["gold"], 5),
            "mrr": mrr(ranked, q["gold"]),
            "ranked_top5": ranked[:5],
        })
    return aggregate(retriever.name, rows)


def aggregate(name: str, rows: list[dict]) -> dict:
    def avg(items, key):
        items = list(items)
        return round(sum(r[key] for r in items) / len(items), 3) if items else 0.0
    by = {}
    for t in ("single_hop", "multi_hop", "all"):
        sel = rows if t == "all" else [r for r in rows if r["type"] == t]
        by[t] = {"recall@3": avg(sel, "recall@3"),
                 "recall@5": avg(sel, "recall@5"),
                 "mrr": avg(sel, "mrr"),
                 "n": len(sel)}
    return {"retriever": name, "by_type": by, "rows": rows}


def print_table(results: list[dict]) -> None:
    print(f"\n{'retriever':<16} {'split':<11} {'R@3':>6} {'R@5':>6} {'MRR':>6} {'n':>4}")
    print("-" * 55)
    for res in results:
        for t in ("single_hop", "multi_hop", "all"):
            b = res["by_type"][t]
            print(f"{res['retriever']:<16} {t:<11} {b['recall@3']:>6} "
                  f"{b['recall@5']:>6} {b['mrr']:>6} {b['n']:>4}")
        print("-" * 55)


def plot(results: list[dict]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib not installed — skipping chart)")
        return
    names = [r["retriever"] for r in results]
    multi = [r["by_type"]["multi_hop"]["recall@3"] for r in results]
    single = [r["by_type"]["single_hop"]["recall@3"] for r in results]
    x = range(len(names))
    plt.figure(figsize=(7, 4))
    plt.bar([i - 0.2 for i in x], single, width=0.4, label="single-hop")
    plt.bar([i + 0.2 for i in x], multi, width=0.4, label="multi-hop")
    plt.xticks(list(x), names, rotation=10)
    plt.ylabel("Recall@3")
    plt.title("HungOver: graph vs vector retrieval (the multi-hop gap is the story)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_CHART, dpi=140)
    print(f"chart -> {OUT_CHART}")


async def main(naive_only: bool) -> None:
    docs = load_docs()
    ids = known_ids(docs)
    queries = json.loads(QUERIES.read_text())["queries"]
    print(f"corpus: {len(docs)} docs · queries: {len(queries)}")

    results = []
    results.append(await evaluate(NaiveVector(docs), queries))

    if not naive_only:
        # Ingest corpus into Cognee first (idempotent-ish; prune for a clean run).
        import memory_service as mem
        from memory_service import RecallMode
        for did, text in docs.items():
            await mem.remember(text, dataset=mem.DEFAULT_DATASET)
        results.append(await evaluate(
            CogneeRetriever(RecallMode.VECTOR, ids, "cognee_vector"), queries))
        results.append(await evaluate(
            CogneeRetriever(RecallMode.GRAPH, ids, "cognee_graph"), queries))

    print_table(results)
    OUT_JSON.write_text(json.dumps(results, indent=2))
    print(f"results -> {OUT_JSON}")
    plot(results)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "backend"))  # import memory_service
    ap = argparse.ArgumentParser()
    ap.add_argument("--naive", action="store_true",
                    help="run only the offline naive baseline (no Cognee/LLM needed)")
    args = ap.parse_args()
    asyncio.run(main(naive_only=args.naive))
