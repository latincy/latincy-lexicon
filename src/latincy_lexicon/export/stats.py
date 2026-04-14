"""Coverage statistics for the exported lexicon."""

from __future__ import annotations

import json
from pathlib import Path


def coverage_report(
    lexicon_path: str | Path,
    lemma_lookup_path: str | Path | None = None,
) -> dict:
    """Generate coverage statistics for the exported lexicon.

    Args:
        lexicon_path: Path to lexicon.json.
        lemma_lookup_path: Optional path to la_lemma_lookup.json for comparison.

    Returns:
        Dict with coverage statistics.
    """
    with open(lexicon_path) as f:
        lexicon = json.load(f)

    stats: dict = {
        "lexicon_lemmas": len(lexicon),
        "lexicon_entries": sum(len(v) for v in lexicon.values()),
        "avg_entries_per_lemma": (
            sum(len(v) for v in lexicon.values()) / len(lexicon)
            if lexicon else 0
        ),
    }

    # POS distribution
    pos_dist: dict[str, int] = {}
    for entries in lexicon.values():
        for e in entries:
            pos = e.get("pos", "X")
            pos_dist[pos] = pos_dist.get(pos, 0) + 1
    stats["pos_distribution"] = dict(sorted(pos_dist.items()))

    # Frequency distribution
    freq_dist: dict[str, int] = {}
    for entries in lexicon.values():
        for e in entries:
            freq = e.get("freq", "X")
            freq_dist[freq] = freq_dist.get(freq, 0) + 1
    stats["freq_distribution"] = dict(sorted(freq_dist.items()))

    # Compare with LatinCy lemma lookup if provided
    if lemma_lookup_path:
        lemma_lookup_path = Path(lemma_lookup_path)
        if lemma_lookup_path.exists():
            with open(lemma_lookup_path) as f:
                lemma_lookup = json.load(f)
            latincy_lemmas = set(v.lower() for v in lemma_lookup.values())
            lexicon_lemmas = set(lexicon.keys())
            overlap = latincy_lemmas & lexicon_lemmas
            stats["latincy_lemmas"] = len(latincy_lemmas)
            stats["overlap"] = len(overlap)
            stats["coverage_of_latincy"] = (
                len(overlap) / len(latincy_lemmas) if latincy_lemmas else 0
            )

    return stats


def print_coverage(stats: dict) -> None:
    """Print coverage report to stdout."""
    print(f"\nLexicon Coverage Report")
    print(f"  Lexicon lemmas:        {stats['lexicon_lemmas']:,}")
    print(f"  Total entries:         {stats['lexicon_entries']:,}")
    print(f"  Avg entries/lemma:     {stats['avg_entries_per_lemma']:.1f}")

    if "pos_distribution" in stats:
        print(f"\n  POS distribution:")
        for pos, cnt in stats["pos_distribution"].items():
            print(f"    {pos:8s} {cnt:,}")

    if "latincy_lemmas" in stats:
        print(f"\n  LatinCy comparison:")
        print(f"    LatinCy lemmas:      {stats['latincy_lemmas']:,}")
        print(f"    Overlap:             {stats['overlap']:,}")
        print(f"    Coverage:            {stats['coverage_of_latincy']:.1%}")
