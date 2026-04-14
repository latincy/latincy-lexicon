"""Alignment statistics and reporting."""

from __future__ import annotations

import sqlite3


def alignment_report(conn: sqlite3.Connection) -> dict:
    """Generate alignment statistics.

    Returns:
        Dict with total, matched, unmatched, match type distribution.
    """
    total_headwords = conn.execute("SELECT COUNT(DISTINCT normalized) FROM headwords").fetchone()[0]
    total_aligned = conn.execute("SELECT COUNT(DISTINCT words_headword) FROM alignment").fetchone()[0]

    by_type = {}
    rows = conn.execute(
        "SELECT match_type, COUNT(*) as cnt FROM alignment GROUP BY match_type"
    ).fetchall()
    for r in rows:
        by_type[r["match_type"]] = r["cnt"]

    return {
        "total_headwords": total_headwords,
        "aligned": total_aligned,
        "unaligned": total_headwords - total_aligned,
        "alignment_rate": total_aligned / total_headwords if total_headwords > 0 else 0,
        "by_match_type": by_type,
    }


def print_report(stats: dict) -> None:
    """Print alignment report to stdout."""
    print(f"\nAlignment Report")
    print(f"  Total unique headwords: {stats['total_headwords']:,}")
    print(f"  Aligned:               {stats['aligned']:,}")
    print(f"  Unaligned:             {stats['unaligned']:,}")
    print(f"  Alignment rate:        {stats['alignment_rate']:.1%}")
    if stats["by_match_type"]:
        print(f"  By match type:")
        for mt, cnt in sorted(stats["by_match_type"].items()):
            print(f"    {mt}: {cnt:,}")
