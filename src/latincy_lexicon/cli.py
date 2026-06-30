"""CLI for latincy-lexicon."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_build(args: argparse.Namespace) -> None:
    """Build JSON data files from bundled WW data."""
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


def cmd_build_ls(args: argparse.Namespace) -> None:
    """Build the Lewis & Short JSON stores from the Perseus TEI."""
    from latincy_lexicon.export.lewis_short import (
        build_lewis_short_senses,
        build_lewis_short_store,
    )

    tei_path = Path(args.tei)
    output_dir = Path(args.output_dir)
    if not tei_path.exists():
        print(f"error: TEI file not found: {tei_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Building Lewis & Short store from {tei_path} → {output_dir}/")
    result = build_lewis_short_store(tei_path, output_dir)
    print(f"  Entries:    {result['entries']:,}")
    print(f"  Index keys: {result['index_keys']:,}")

    if not args.no_senses:
        print("Building Lewis & Short sense store …")
        sense_result = build_lewis_short_senses(tei_path, output_dir)
        print(f"  Sense entries: {sense_result['entries']:,}")
        print(f"  Senses:        {sense_result['senses']:,}")
    print("Done.")


def main(argv: list[str] | None = None) -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="latincy-lexicon",
        description="Whitaker's Words data pipeline for LatinCy",
    )

    sub = parser.add_subparsers(dest="command")

    p_build = sub.add_parser("build", help="Build JSON from bundled data")
    p_build.add_argument(
        "--output-dir",
        default="data/json",
        help="Output directory for JSON files",
    )

    p_build_ls = sub.add_parser(
        "build-ls", help="Build the Lewis & Short store from the Perseus TEI"
    )
    p_build_ls.add_argument(
        "--tei",
        default="data/raw/lewis-short/lat.ls.perseus-eng2.xml",
        help="Path to the Lewis & Short TEI file",
    )
    p_build_ls.add_argument(
        "--output-dir",
        default="src/latincy_lexicon/data/json",
        help="Output directory for JSON files",
    )
    p_build_ls.add_argument(
        "--no-senses",
        action="store_true",
        help="Skip building the sense store (lewis_short_senses.json)",
    )

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "build": cmd_build,
        "build-ls": cmd_build_ls,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
