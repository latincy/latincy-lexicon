"""CLI for latincy-lexicon: build, extract, build-db, align, export, stats, all."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Default paths relative to project root
DEFAULT_VENDOR = "vendor/whitakers-words"
DEFAULT_DB = "data/db/whitakers.db"
DEFAULT_JSON = "data/json/lexicon.json"
DEFAULT_SUPPLEMENT = "data/json/lemma_supplement.json"
DEFAULT_ANALYZER = "data/json/analyzer.json"
DEFAULT_TRICKS_ADB = "src/words_engine/words_engine-trick_tables.adb"


def find_project_root() -> Path:
    """Find project root by looking for pyproject.toml."""
    p = Path.cwd()
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    return Path.cwd()


def cmd_build(args: argparse.Namespace) -> None:
    """Build JSON data files from bundled WW data (no SQLite, no vendor clone)."""
    from latincy_lexicon.build import build

    output_dir = Path(getattr(args, "output_dir", "data/json"))
    print(f"Building from bundled data → {output_dir}/")

    result = build(output_dir=output_dir)

    print(f"  Entries:     {result['entries']:,}")
    print(f"  Inflections: {result['inflections']:,}")
    print(f"  Headwords:   {result['headwords']:,}")
    print(f"  Lexicon keys: {result['lexicon_keys']:,}")
    print(f"  → {result['analyzer_path']}")
    print(f"  → {result['lexicon_path']}")
    print("Done.")


def cmd_extract(args: argparse.Namespace) -> None:
    """Parse all data files and report counts."""
    from latincy_lexicon.parsers.dictline import parse_dictline
    from latincy_lexicon.parsers.inflects import parse_inflects
    from latincy_lexicon.parsers.addons import parse_addons
    from latincy_lexicon.parsers.uniques import parse_uniques
    from latincy_lexicon.parsers.tricks import parse_tricks

    vendor = Path(args.vendor)
    print(f"Parsing data from {vendor}")

    entries = parse_dictline(vendor / "DICTLINE.GEN")
    print(f"  DICTLINE: {len(entries):,} entries")

    inflections = parse_inflects(vendor / "INFLECTS.LAT")
    print(f"  INFLECTS: {len(inflections):,} inflections")

    addons = parse_addons(vendor / "ADDONS.LAT")
    print(f"  ADDONS:   {len(addons):,} addons")

    uniques = parse_uniques(vendor / "UNIQUES.LAT")
    print(f"  UNIQUES:  {len(uniques):,} uniques")

    tricks_path = vendor / DEFAULT_TRICKS_ADB
    if tricks_path.exists():
        tricks = parse_tricks(tricks_path)
        print(f"  TRICKS:   {len(tricks):,} tricks")
    else:
        print("  TRICKS:   (source file not found)")


def cmd_build_db(args: argparse.Namespace) -> None:
    """Parse all data and load into SQLite."""
    from latincy_lexicon.parsers.dictline import parse_dictline
    from latincy_lexicon.parsers.inflects import parse_inflects
    from latincy_lexicon.parsers.addons import parse_addons
    from latincy_lexicon.parsers.uniques import parse_uniques
    from latincy_lexicon.parsers.tricks import parse_tricks
    from latincy_lexicon.db.schema import create_db
    from latincy_lexicon.db.loader import (
        load_dict_entries, load_inflections, load_addons,
        load_uniques, load_tricks,
    )
    from latincy_lexicon.align.headword import build_headwords
    from latincy_lexicon.db.queries import get_table_counts

    vendor = Path(args.vendor)
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing DB
    if db_path.exists():
        db_path.unlink()

    print(f"Building database at {db_path}")

    # Parse
    entries = parse_dictline(vendor / "DICTLINE.GEN")
    inflections = parse_inflects(vendor / "INFLECTS.LAT")
    addons = parse_addons(vendor / "ADDONS.LAT")
    uniques = parse_uniques(vendor / "UNIQUES.LAT")

    tricks_path = vendor / DEFAULT_TRICKS_ADB
    tricks = parse_tricks(tricks_path) if tricks_path.exists() else []

    # Create DB and load
    conn = create_db(db_path)
    load_dict_entries(conn, entries)
    load_inflections(conn, inflections)
    load_addons(conn, addons)
    load_uniques(conn, uniques)
    load_tricks(conn, tricks)

    # Apply patches for hardcoded entries missing from data files
    from latincy_lexicon.db.patches import apply_all_patches
    patch_stats = apply_all_patches(conn)
    if patch_stats.get("sum_entry"):
        print(f"  Patched: sum/esse added ({patch_stats['sum_inflections']} inflections)")

    # Build headwords
    hw_count = build_headwords(conn)
    print(f"  Built {hw_count:,} headwords")

    # Report
    counts = get_table_counts(conn)
    for table, count in counts.items():
        print(f"  {table}: {count:,}")

    conn.close()
    print("Done.")


def cmd_align(args: argparse.Namespace) -> None:
    """Run headword alignment against LatinCy lemma lookup."""
    import sqlite3
    from latincy_lexicon.align.headword import align_to_latincy
    from latincy_lexicon.align.report import alignment_report, print_report

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}. Run build-db first.", file=sys.stderr)
        sys.exit(1)

    lemma_path = Path(args.lemma_lookup)
    if not lemma_path.exists():
        print(f"Error: Lemma lookup not found at {lemma_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    print(f"Aligning headwords against {lemma_path}")
    stats = align_to_latincy(conn, lemma_path)
    print(f"  Match stats: {stats}")

    report = alignment_report(conn)
    print_report(report)

    conn.close()


def cmd_export(args: argparse.Namespace) -> None:
    """Export aligned data to lexicon.json."""
    import sqlite3
    from latincy_lexicon.export.json_export import export_lexicon

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    json_path = Path(args.output)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    count = export_lexicon(conn, json_path)
    print(f"Exported {count:,} lemma keys to {json_path}")

    conn.close()


def cmd_stats(args: argparse.Namespace) -> None:
    """Print coverage statistics."""
    from latincy_lexicon.export.stats import coverage_report, print_coverage

    json_path = Path(args.lexicon)
    if not json_path.exists():
        print(f"Error: Lexicon not found at {json_path}", file=sys.stderr)
        sys.exit(1)

    lemma_path = args.lemma_lookup
    stats = coverage_report(json_path, lemma_path)
    print_coverage(stats)


def cmd_supplement(args: argparse.Namespace) -> None:
    """Generate supplemental form→lemma mappings from Words inflections."""
    import sqlite3
    from latincy_lexicon.export.lemma_supplement import export_supplement

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    existing = getattr(args, "lemma_lookup", None)
    output = Path(getattr(args, "output", DEFAULT_SUPPLEMENT))

    stats = export_supplement(conn, output, existing)
    print(f"Supplemental lemma export:")
    print(f"  Total Words forms:     {stats['total_words_forms']:,}")
    print(f"  Existing lookup forms: {stats['existing_forms']:,}")
    print(f"  New forms:             {stats['new_forms']:,}")
    print(f"  New unique lemmas:     {stats['new_lemmas']:,}")
    print(f"  Written to:            {output}")

    conn.close()


def cmd_export_analyzer(args: argparse.Namespace) -> None:
    """Export analyzer data to JSON for runtime use (no sqlite3 dependency)."""
    import sqlite3
    from latincy_lexicon.export.json_export import export_analyzer_data

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    output = Path(getattr(args, "output", DEFAULT_ANALYZER))

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    count = export_analyzer_data(conn, output)
    print(f"Exported analyzer data: {count:,} entries to {output}")
    print(f"  Size: {output.stat().st_size / 1e6:.1f} MB")

    conn.close()


def cmd_all(args: argparse.Namespace) -> None:
    """Run full pipeline: build-db → export-analyzer → align → export → supplement → stats."""
    # Build DB
    cmd_build_db(args)

    # Export analyzer JSON (always — no alignment needed)
    args.output = DEFAULT_ANALYZER
    cmd_export_analyzer(args)

    # Align (if lemma lookup available)
    lemma_path = Path(args.lemma_lookup) if args.lemma_lookup else None
    if lemma_path and lemma_path.exists():
        cmd_align(args)

        args.output = DEFAULT_JSON
        cmd_export(args)

        # Generate supplement
        args.output = getattr(args, "supplement_output", DEFAULT_SUPPLEMENT)
        cmd_supplement(args)

        # Stats
        args.lexicon = getattr(args, "output", DEFAULT_JSON)
        if not hasattr(args, "lexicon") or args.lexicon == DEFAULT_SUPPLEMENT:
            args.lexicon = DEFAULT_JSON
        cmd_stats(args)
    else:
        print("Skipping alignment/export (no lemma lookup provided)")


def main(argv: list[str] | None = None) -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="latincy-lexicon",
        description="Whitaker's Words data pipeline for LatinCy",
    )
    parser.add_argument(
        "--vendor", default=DEFAULT_VENDOR,
        help="Path to whitakers-words clone",
    )
    parser.add_argument(
        "--db", default=DEFAULT_DB,
        help="Path to SQLite database",
    )

    sub = parser.add_subparsers(dest="command")

    # build (recommended — uses bundled data, no SQLite)
    p_build = sub.add_parser("build", help="Build JSON from bundled data (no DB needed)")
    p_build.add_argument(
        "--output-dir", default="data/json",
        help="Output directory for JSON files",
    )

    # extract
    sub.add_parser("extract", help="Parse data files and report counts")

    # build-db
    sub.add_parser("build-db", help="Parse data and load into SQLite")

    # align
    p_align = sub.add_parser("align", help="Align headwords to LatinCy lemmas")
    p_align.add_argument(
        "--lemma-lookup", required=True,
        help="Path to la_lemma_lookup.json",
    )

    # export
    p_export = sub.add_parser("export", help="Export to lexicon.json")
    p_export.add_argument(
        "--output", default=DEFAULT_JSON,
        help="Output path for lexicon.json",
    )

    # stats
    p_stats = sub.add_parser("stats", help="Print coverage statistics")
    p_stats.add_argument(
        "--lexicon", default=DEFAULT_JSON,
        help="Path to lexicon.json",
    )
    p_stats.add_argument(
        "--lemma-lookup",
        help="Path to la_lemma_lookup.json for comparison",
    )

    # export-analyzer
    p_ea = sub.add_parser("export-analyzer", help="Export analyzer data to JSON (runtime)")
    p_ea.add_argument(
        "--output", default=DEFAULT_ANALYZER,
        help="Output path for analyzer.json",
    )

    # supplement
    p_supp = sub.add_parser("supplement", help="Generate supplemental form→lemma mappings")
    p_supp.add_argument(
        "--lemma-lookup",
        help="Path to existing la_lemma_lookup.json (to exclude known forms)",
    )
    p_supp.add_argument(
        "--output", default=DEFAULT_SUPPLEMENT,
        help="Output path for supplement JSON",
    )

    # all
    p_all = sub.add_parser("all", help="Run full pipeline")
    p_all.add_argument(
        "--lemma-lookup",
        help="Path to la_lemma_lookup.json",
    )
    p_all.add_argument(
        "--output", default=DEFAULT_JSON,
        help="Output path for lexicon.json",
    )

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "build": cmd_build,
        "extract": cmd_extract,
        "build-db": cmd_build_db,
        "align": cmd_align,
        "export": cmd_export,
        "export-analyzer": cmd_export_analyzer,
        "supplement": cmd_supplement,
        "stats": cmd_stats,
        "all": cmd_all,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
