"""Baseline benchmark for latincy-lexicon startup cost.

Measures:
  - import cost of latincy_lexicon.analyzer
  - Analyzer.from_json total
    - json.load subcomponent
    - _build_caches subcomponent
  - Lexicon.from_json total (separate, but on the hot path for the spaCy factory)

Run repeatedly; numbers are noisy. Report median of 5 runs.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZER_JSON = REPO_ROOT / "data" / "json" / "analyzer.json"
LEXICON_JSON = REPO_ROOT / "data" / "json" / "lexicon.json"

N_RUNS = 5


def time_import() -> float:
    t0 = time.perf_counter()
    # Must run in a fresh subprocess to get a cold import; done by caller.
    import latincy_lexicon.analyzer  # noqa: F401
    import latincy_lexicon.models  # noqa: F401
    return time.perf_counter() - t0


def time_from_json_instrumented(path: Path) -> tuple[float, float, float]:
    """Return (total, json_load, build_caches) seconds."""
    from latincy_lexicon.analyzer import Analyzer

    t0 = time.perf_counter()
    with open(path) as f:
        data = json.load(f)
    t1 = time.perf_counter()

    headwords = {int(k): v for k, v in data["headwords"].items()}
    Analyzer(
        inflections=data["inflections"],
        uniques=data["uniques"],
        tackons=data["tackons"],
        entries=data["entries"],
        headwords=headwords,
        plural_mappings=data["plural_mappings"],
    )
    t2 = time.perf_counter()

    return t2 - t0, t1 - t0, t2 - t1


def time_lexicon_load(path: Path) -> float:
    t0 = time.perf_counter()
    with open(path) as f:
        json.load(f)
    return time.perf_counter() - t0


def fmt(seconds: float) -> str:
    return f"{seconds * 1000:.1f}ms"


def main() -> int:
    if not ANALYZER_JSON.exists():
        print(f"missing: {ANALYZER_JSON}", file=sys.stderr)
        return 1
    if not LEXICON_JSON.exists():
        print(f"missing: {LEXICON_JSON}", file=sys.stderr)
        return 1

    # Measure import once (per-process cost; subsequent imports are cached).
    import_t = time_import()

    totals: list[float] = []
    json_loads: list[float] = []
    builds: list[float] = []
    for _ in range(N_RUNS):
        total, jl, build = time_from_json_instrumented(ANALYZER_JSON)
        totals.append(total)
        json_loads.append(jl)
        builds.append(build)

    lexicon_loads = [time_lexicon_load(LEXICON_JSON) for _ in range(N_RUNS)]

    def summarize(name: str, samples: list[float]) -> None:
        med = statistics.median(samples)
        lo = min(samples)
        hi = max(samples)
        print(f"  {name:30s} median={fmt(med)}  min={fmt(lo)}  max={fmt(hi)}")

    print(f"analyzer.json: {ANALYZER_JSON.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"lexicon.json:  {LEXICON_JSON.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"runs: {N_RUNS}")
    print()
    print(f"  import (one-shot)              {fmt(import_t)}")
    summarize("Analyzer.from_json total", totals)
    summarize("  json.load (analyzer)", json_loads)
    summarize("  _build_caches", builds)
    summarize("json.load (lexicon)", lexicon_loads)
    return 0


if __name__ == "__main__":
    sys.exit(main())
