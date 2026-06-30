"""
ingest.py — load data/raw/* and data/hero_case/* into Cognee via memory_service.

Usage:
    python scripts/ingest.py              # ingest all
    python scripts/ingest.py --reset      # prune first, then ingest
    python scripts/ingest.py --hero-only  # only hero case docs
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import memory_service as mem


HERO = ROOT / "data" / "hero_case"
RAW = ROOT / "data" / "raw"


async def ingest_docs(paths: list[Path], label: str) -> None:
    total = len(paths)
    ok = 0
    fail = 0
    for i, path in enumerate(paths, start=1):
        try:
            text = path.read_text(errors="ignore")
            if not text.strip():
                print(f"  [{i}/{total}] SKIP (empty): {path.name}")
                continue
            await mem.remember(text, dataset=mem.DEFAULT_DATASET)
            ok += 1
            print(f"  [{i}/{total}] OK  {path.name}")
        except Exception as exc:
            fail += 1
            print(f"  [{i}/{total}] ERR {path.name}: {exc}")
    print(f"\n{label}: {ok} ingested, {fail} failed out of {total} files.\n")


async def main(hero_only: bool, reset: bool) -> None:
    if reset:
        print("Resetting Cognee memory...")
        try:
            await mem.reset_all()
            print("Reset complete.")
        except Exception as exc:
            print(f"Warning: reset raised {exc} — continuing.")

    hero_paths = sorted(Path(p) for p in glob.glob(str(HERO / "*.md")))
    # Skip the README (00_*) — it has no DOC_ID and is not a case doc
    hero_paths = [p for p in hero_paths if not p.stem.startswith("00")]

    if hero_only:
        print(f"\nIngesting hero case docs ({len(hero_paths)} files)...\n")
        await ingest_docs(hero_paths, "Hero case")
    else:
        raw_paths = sorted(
            p for p in (Path(q) for q in glob.glob(str(RAW / "*")))
            if p.is_file() and not p.name.endswith(".gitkeep")
        )
        print(f"\nIngesting hero case docs ({len(hero_paths)} files)...\n")
        await ingest_docs(hero_paths, "Hero case")
        print(f"Ingesting raw corpus ({len(raw_paths)} files)...\n")
        await ingest_docs(raw_paths, "Raw corpus")

    print("Ingest complete. Knowledge graph is ready for recall().")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Ingest case files into Cognee knowledge graph.")
    ap.add_argument("--reset", action="store_true",
                    help="Prune existing memory before ingesting")
    ap.add_argument("--hero-only", action="store_true",
                    help="Only ingest the hero case documents (skip raw corpus)")
    args = ap.parse_args()
    asyncio.run(main(hero_only=args.hero_only, reset=args.reset))
