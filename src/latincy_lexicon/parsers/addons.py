"""Parser for ADDONS.LAT — prefixes, suffixes, tackons, and packons.

Format varies by addon type:

PREFIX:
  PREFIX fix [connect_char]
  from_pos to_pos
  meaning

SUFFIX:
  SUFFIX fix [connect_char]
  from_pos from_key to_pos to_decl to_var to_comparison/gender to_key
  meaning

TACKON:
  TACKON fix
  pos [decl_which decl_var kind] | X
  meaning

PACKON entries are listed under PREFIX with PACK PACK.
"""

from __future__ import annotations

from pathlib import Path

from latincy_lexicon.enums import AddonType, PartOfSpeech
from latincy_lexicon.models import Addon


def _safe_pos(s: str) -> PartOfSpeech:
    try:
        return PartOfSpeech(s)
    except ValueError:
        return PartOfSpeech.X


def parse_addons(path: str | Path) -> list[Addon]:
    """Parse ADDONS.LAT into a list of Addon objects."""
    path = Path(path)
    lines = path.read_text(encoding="latin-1").splitlines()
    entries: list[Addon] = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip comments and blank lines
        if not line or line.startswith("--"):
            i += 1
            continue

        if line.startswith("PREFIX"):
            entry, i = _parse_prefix(lines, i)
            if entry is not None:
                entries.append(entry)
        elif line.startswith("SUFFIX"):
            entry, i = _parse_suffix(lines, i)
            if entry is not None:
                entries.append(entry)
        elif line.startswith("TACKON"):
            entry, i = _parse_tackon(lines, i)
            if entry is not None:
                entries.append(entry)
        else:
            i += 1

    return entries


def _skip_comments(lines: list[str], i: int) -> int:
    """Skip blank lines and comment lines."""
    while i < len(lines):
        line = lines[i].strip()
        if line and not line.startswith("--"):
            return i
        i += 1
    return i


def _parse_prefix(lines: list[str], i: int) -> tuple[Addon | None, int]:
    """Parse a PREFIX or PACKON entry."""
    line = lines[i].strip()
    tokens = line.split()
    # PREFIX fix [connect]
    fix = tokens[1] if len(tokens) > 1 else ""
    connect = tokens[2] if len(tokens) > 2 else ""
    i += 1

    # Next non-comment line: from_pos to_pos
    i = _skip_comments(lines, i)
    if i >= len(lines):
        return None, i

    pos_line = lines[i].strip()
    pos_tokens = pos_line.split()
    i += 1

    # Determine if PACKON (PACK PACK)
    if len(pos_tokens) >= 2 and pos_tokens[0] == "PACK" and pos_tokens[1] == "PACK":
        addon_type = AddonType.PACKON
        from_pos = PartOfSpeech.PACK
        to_pos = PartOfSpeech.PACK
    else:
        addon_type = AddonType.PREFIX
        from_pos = _safe_pos(pos_tokens[0]) if pos_tokens else PartOfSpeech.X
        to_pos = _safe_pos(pos_tokens[1]) if len(pos_tokens) > 1 else from_pos

    # Next non-comment line: meaning
    i = _skip_comments(lines, i)
    if i >= len(lines):
        return Addon(addon_type=addon_type, fix=fix, connect=connect,
                     from_pos=from_pos, to_pos=to_pos), i

    meaning = lines[i].strip()
    # Don't consume if it's the start of another entry
    if meaning.startswith(("PREFIX", "SUFFIX", "TACKON")):
        return Addon(addon_type=addon_type, fix=fix, connect=connect,
                     from_pos=from_pos, to_pos=to_pos), i

    i += 1
    return Addon(
        addon_type=addon_type, fix=fix, connect=connect,
        from_pos=from_pos, to_pos=to_pos, meaning=meaning,
    ), i


def _parse_suffix(lines: list[str], i: int) -> tuple[Addon | None, int]:
    """Parse a SUFFIX entry."""
    line = lines[i].strip()
    tokens = line.split()
    fix = tokens[1] if len(tokens) > 1 else ""
    connect = tokens[2] if len(tokens) > 2 else ""
    i += 1

    # Next non-comment line: from_pos from_key to_pos to_decl to_var ...
    i = _skip_comments(lines, i)
    if i >= len(lines):
        return None, i

    spec_line = lines[i].strip()
    spec_tokens = spec_line.split()
    from_pos = _safe_pos(spec_tokens[0]) if spec_tokens else PartOfSpeech.X
    # to_pos is typically the 3rd token (index 2)
    to_pos = PartOfSpeech.X
    for j, tok in enumerate(spec_tokens[1:], 1):
        if tok.isalpha() and len(tok) >= 1:
            to_pos_candidate = _safe_pos(tok)
            if to_pos_candidate != PartOfSpeech.X:
                to_pos = to_pos_candidate
                break
    i += 1

    # Next non-comment line: meaning
    i = _skip_comments(lines, i)
    if i >= len(lines):
        return Addon(addon_type=AddonType.SUFFIX, fix=fix, connect=connect,
                     from_pos=from_pos, to_pos=to_pos), i

    meaning = lines[i].strip()
    if meaning.startswith(("PREFIX", "SUFFIX", "TACKON")):
        return Addon(addon_type=AddonType.SUFFIX, fix=fix, connect=connect,
                     from_pos=from_pos, to_pos=to_pos), i

    i += 1
    return Addon(
        addon_type=AddonType.SUFFIX, fix=fix, connect=connect,
        from_pos=from_pos, to_pos=to_pos, meaning=meaning,
    ), i


def _parse_tackon(lines: list[str], i: int) -> tuple[Addon | None, int]:
    """Parse a TACKON entry."""
    line = lines[i].strip()
    tokens = line.split()
    fix = tokens[1] if len(tokens) > 1 else ""

    # Check for inline meaning (TACKON fix \n spec \n TACKON meaning_continuation)
    # Some tackons have meaning on the same line as the TACKON keyword
    # e.g. "TACKON w/hic this?   (hic + ce + ne (enclitic));"
    if len(tokens) > 2 and not tokens[1].startswith(("PREFIX", "SUFFIX", "TACKON")):
        # Check if there's a meaning embedded after the fix on this line
        pass

    i += 1

    # Next non-comment line: POS spec or X
    i = _skip_comments(lines, i)
    if i >= len(lines):
        return None, i

    spec_line = lines[i].strip()

    # Check if this is actually a continuation/meaning line (starts with TACKON)
    if spec_line.startswith("TACKON"):
        # This was an inline entry — the meaning was on a following TACKON line
        # Return what we have and let the next iteration handle the new TACKON
        return Addon(addon_type=AddonType.TACKON, fix=fix), i

    from_pos = PartOfSpeech.X
    spec_tokens = spec_line.split()
    if spec_tokens and spec_tokens[0] != "X":
        from_pos = _safe_pos(spec_tokens[0])
    i += 1

    # Next non-comment line: meaning
    i = _skip_comments(lines, i)
    if i >= len(lines):
        return Addon(addon_type=AddonType.TACKON, fix=fix, from_pos=from_pos, to_pos=from_pos), i

    meaning = lines[i].strip()
    if meaning.startswith(("PREFIX", "SUFFIX", "TACKON")):
        return Addon(addon_type=AddonType.TACKON, fix=fix, from_pos=from_pos, to_pos=from_pos), i

    i += 1
    return Addon(
        addon_type=AddonType.TACKON, fix=fix,
        from_pos=from_pos, to_pos=from_pos, meaning=meaning,
    ), i
