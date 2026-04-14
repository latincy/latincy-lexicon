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

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "build": cmd_build,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
