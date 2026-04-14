"""Parser for trick tables from the Ada source code.

Extracts flip/flip_flop/slur/internal tricks from both:
  - words_engine-trick_tables.adb (letter-specific tricks, slur tricks)
  - words_engine-trick_tables.ads (Any_Tricks, Mediaeval_Tricks — TC_Internal)
"""

from __future__ import annotations

import re
from pathlib import Path

from latincy_lexicon.enums import TrickClass
from latincy_lexicon.models import Trick

# Regex patterns for Ada trick entries
FLIP_FLOP_RE = re.compile(
    r'FF1\s*=>\s*\+"([^"]*)",\s*FF2\s*=>\s*\+"([^"]*)"'
)
FLIP_RE = re.compile(
    r'FF3\s*=>\s*\+"([^"]*)",\s*FF4\s*=>\s*\+"([^"]*)"'
)
SLUR_RE = re.compile(
    r'S1\s*=>\s*\+"([^"]*)"'
)
INTERNAL_RE = re.compile(
    r'I1\s*=>\s*\+"([^"]*)",\s*I2\s*=>\s*\+"([^"]*)"'
)

# Map variable name prefixes to trick classes
TRICK_CLASS_MAP = {
    "A_Tricks": TrickClass.ANY,
    "D_Tricks": TrickClass.ANY,
    "E_Tricks": TrickClass.ANY,
    "F_Tricks": TrickClass.ANY,
    "G_Tricks": TrickClass.ANY,
    "H_Tricks": TrickClass.ANY,
    "K_Tricks": TrickClass.ANY,
    "L_Tricks": TrickClass.ANY,
    "M_Tricks": TrickClass.ANY,
    "N_Tricks": TrickClass.ANY,
    "O_Tricks": TrickClass.ANY,
    "P_Tricks": TrickClass.ANY,
    "S_Tricks": TrickClass.ANY,
    "T_Tricks": TrickClass.ANY,
    "U_Tricks": TrickClass.ANY,
    "Y_Tricks": TrickClass.ANY,
    "Z_Tricks": TrickClass.ANY,
    "A_Slur_Tricks": TrickClass.SLUR,
    "C_Slur_Tricks": TrickClass.SLUR,
    "I_Slur_Tricks": TrickClass.SLUR,
    "N_Slur_Tricks": TrickClass.SLUR,
    "O_Slur_Tricks": TrickClass.SLUR,
    "Q_Slur_Tricks": TrickClass.SLUR,
    "S_Slur_Tricks": TrickClass.SLUR,
    "Any_Tricks": TrickClass.ANY,
    "Mediaeval_Tricks": TrickClass.MEDIAEVAL,
}

# Regex to identify which trick table a line belongs to
TABLE_DEF_RE = re.compile(r'(\w+_(?:Slur_)?Tricks|Any_Tricks|Mediaeval_Tricks)\s*:\s*constant')


def parse_tricks(path: str | Path) -> list[Trick]:
    """Parse trick tables from Ada source files.

    Parses both the .adb file (letter-specific and slur tricks) and the
    corresponding .ads file (Any_Tricks, Mediaeval_Tricks with TC_Internal).

    Args:
        path: Path to words_engine-trick_tables.adb (will also read .ads)

    Returns:
        List of Trick objects.
    """
    path = Path(path)
    tricks: list[Trick] = []

    # Parse both .adb and .ads files
    files = [path]
    ads_path = path.with_suffix(".ads")
    if ads_path.exists():
        files.append(ads_path)

    for source_file in files:
        tricks.extend(_parse_single_file(source_file))

    return tricks


def _parse_single_file(path: Path) -> list[Trick]:
    """Parse tricks from a single Ada source file."""
    text = path.read_text(encoding="latin-1")
    tricks: list[Trick] = []

    current_class = TrickClass.ANY

    for line in text.splitlines():
        # Check for table definition
        table_match = TABLE_DEF_RE.search(line)
        if table_match:
            current_table = table_match.group(1)
            current_class = TRICK_CLASS_MAP.get(current_table, TrickClass.ANY)
            continue

        # Check for flip_flop entries (bidirectional)
        ff_match = FLIP_FLOP_RE.search(line)
        if ff_match:
            from_text, to_text = ff_match.group(1), ff_match.group(2)
            tricks.append(Trick(
                trick_class=current_class,
                from_text=from_text,
                to_text=to_text,
                explanation=f"{from_text} <=> {to_text} (flip-flop)",
            ))
            continue

        # Check for flip entries (one-direction try)
        flip_match = FLIP_RE.search(line)
        if flip_match:
            from_text, to_text = flip_match.group(1), flip_match.group(2)
            tricks.append(Trick(
                trick_class=current_class,
                from_text=from_text,
                to_text=to_text,
                explanation=f"{from_text} => {to_text} (flip)",
            ))
            continue

        # Check for internal entries (TC_Internal — substring replacements)
        internal_match = INTERNAL_RE.search(line)
        if internal_match:
            from_text, to_text = internal_match.group(1), internal_match.group(2)
            tricks.append(Trick(
                trick_class=current_class,
                from_text=from_text,
                to_text=to_text,
                explanation=f"{from_text} => {to_text} (internal)",
            ))
            continue

        # Check for slur entries
        slur_match = SLUR_RE.search(line)
        if slur_match:
            prefix = slur_match.group(1)
            tricks.append(Trick(
                trick_class=current_class,
                from_text=prefix,
                to_text="",
                explanation=f"{prefix} (slur — assimilation prefix)",
            ))

    return tricks
