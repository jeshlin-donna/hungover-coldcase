"""
benchmark_improve.py — captures the real improve() before/after metric delta.

Runs a minimal experiment:
  1. Ingest 11 hero-case docs into a fresh dataset
  2. recall() 3 key multi-hop queries → record BEFORE metrics
  3. Log a detective hunch via log_hunch()
  4. resolve_case() → improve() merges session memory into graph
  5. recall() same queries → record AFTER metrics
  6. Print delta + write to benchmark/improve_results.json

Usage:
    source .venv/bin/activate
    python benchmark/benchmark_improve.py
"""
from __future__ import annotations

import asyncio
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / "data" / "hero_case"
OUT = ROOT / "benchmark" / "improve_results.json"
sys.path.insert(0, str(ROOT / "backend"))

DATASET = "improve_test"
SESSION_ID = "detective-001"

TEST_QUERIES = [
    {
        "id": "q07",
        "query": "Is there forensic evidence linking the Maple Heights and Riverside burglaries?",
        "gold": ["MH-0312-FOR", "RV-0788-FOR"],
    },
    {
        "id": "q17",
        "query": "Does Daniel Marsh's alibi for the night of the Riverside burglary hold up against the other evidence?",
        "gold": ["MARSH-ALIBI", "MARSH-RECEIPT"],
    },
    {
        "id": "q14",
        "query": "Why wasn't the serial pattern caught earlier across the two departments?",
        "gold": ["MH-0312-FOR", "RV-0788-FOR", "MH-0102-ARR", "RV-0788-NARR"],
    },
]

HUNCH = (
    "Detective hunch: the same 8mm left-nick pry blade signature appears in BOTH "
    "the Maple Heights and Riverside cases. This cross-jurisdiction tool match was "
    "never flagged because the two departments don't share a database. "
    "The motel receipt (Grand Stay Inn, 4.2 miles from 902 Riverside Lane at 00:48) "
    "directly contradicts Marsh's alibi claim of being 300 miles away. "
    "Recommend cross-reference of all pry-tool forensic reports across both jurisdictions."
)

DOC_ID_RE = re.compile(r"DOC_ID:\s*([A-Z0-9\-]+)")


def mrr(ranked, gold):
    gold_set = set(gold)
    for i, did in enumerate(ranked, start=1):
        if did in gold_set:
            return 1.0 / i
    return 0.0


def recall_at_k(ranked, gold, k):
    if not gold:
        return 0.0
    return len(set(ranked[:k]) & set(gold)) / len(set(gold))


def extract_ids(raw, known_ids):
    text = str(raw)
    positions = [(text.find(i), i) for i in known_ids if text.find(i) >= 0]
    seen, result = set(), []
    for _, did in sorted(positions):
        if did not in seen:
            seen.add(did)
            result.append(did)
    return result


async def run_queries(mem, known_ids):
    from memory_service import RecallMode
    rows = []
    for q in TEST_QUERIES:
        try:
            res = await asyncio.wait_for(
                mem.recall(q["query"], mode=RecallMode.GRAPH, dataset=DATASET),
                timeout=120,
            )
            ranked = extract_ids(res.raw, known_ids)
            rows.append({
                "id": q["id"],
                "recall@3": recall_at_k(ranked, q["gold"], 3),
                "recall@5": recall_at_k(ranked, q["gold"], 5),
                "mrr": mrr(ranked, q["gold"]),
                "ranked_top5": ranked[:5],
            })
            print(f"  {q['id']}: R@3={rows[-1]['recall@3']:.3f}  MRR={rows[-1]['mrr']:.3f}")
        except Exception as e:
            print(f"  {q['id']}: FAILED -> {type(e).__name__}: {e}")
            rows.append({"id": q["id"], "recall@3": 0.0, "recall@5": 0.0, "mrr": 0.0, "ranked_top5": []})
    avg = lambda k: round(sum(r[k] for r in rows) / len(rows), 3) if rows else 0.0
    return {
        "rows": rows,
        "avg_recall@3": avg("recall@3"),
        "avg_recall@5": avg("recall@5"),
        "avg_mrr": avg("mrr"),
    }


async def main():
    from dotenv import load_dotenv
    load_dotenv()

    import memory_service as mem

    known_ids = []
    for path in glob.glob(str(HERO / "*.md")):
        text = Path(path).read_text()
        m = DOC_ID_RE.search(text)
        if m and not m.group(1).startswith("00"):
            known_ids.append(m.group(1))
    known_ids = sorted(known_ids, key=len, reverse=True)
    print(f"Known doc IDs: {known_ids}")

    print("\n=== Step 1: Ingesting hero-case docs ===")
    hero_paths = sorted(
        p for p in (Path(q) for q in glob.glob(str(HERO / "*.md")))
        if not p.stem.startswith("00")
    )
    for i, path in enumerate(hero_paths, 1):
        try:
            text = path.read_text()
            await asyncio.wait_for(mem.remember(text, dataset=DATASET), timeout=300)
            print(f"  [{i}/{len(hero_paths)}] OK  {path.name}")
        except Exception as e:
            print(f"  [{i}/{len(hero_paths)}] ERR {path.name}: {type(e).__name__}: {str(e)[:200]}")

    print("\n=== Step 2: BEFORE recall (graph mode) ===")
    before = await run_queries(mem, known_ids)
    print(f"\n  BEFORE -> avg R@3={before['avg_recall@3']}  avg MRR={before['avg_mrr']}")

    print("\n=== Step 3: Logging detective hunch ===")
    try:
        await mem.log_hunch(HUNCH, session_id=SESSION_ID, dataset=DATASET)
        print("  log_hunch OK")
    except Exception as e:
        print(f"  log_hunch FAILED -> {type(e).__name__}: {e}")

    print("\n=== Step 4: resolve_case() -> improve() ===")
    try:
        await mem.resolve_case(session_ids=[SESSION_ID], dataset=DATASET)
        print("  improve OK")
    except Exception as e:
        print(f"  improve FAILED -> {type(e).__name__}: {e}")

    print("\n=== Step 5: AFTER recall (graph mode) ===")
    after = await run_queries(mem, known_ids)
    print(f"\n  AFTER  -> avg R@3={after['avg_recall@3']}  avg MRR={after['avg_mrr']}")

    delta_r3 = round(after["avg_recall@3"] - before["avg_recall@3"], 3)
    delta_mrr = round(after["avg_mrr"] - before["avg_mrr"], 3)
    print(f"\n=== DELTA ===")
    print(f"  Recall@3: {before['avg_recall@3']} -> {after['avg_recall@3']}  (Delta {delta_r3:+.3f})")
    print(f"  MRR:      {before['avg_mrr']} -> {after['avg_mrr']}  (Delta {delta_mrr:+.3f})")

    result = {
        "before": before,
        "after": after,
        "delta": {"recall@3": delta_r3, "mrr": delta_mrr},
        "hunch": HUNCH,
        "dataset": DATASET,
        "session_id": SESSION_ID,
    }
    OUT.write_text(json.dumps(result, indent=2))
    print(f"\nResults -> {OUT}")

    print("\n=== Cleanup: expunging test dataset ===")
    try:
        await mem.expunge(DATASET)
        print("  expunge OK")
    except Exception as e:
        print(f"  expunge FAILED -> {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
