"""Parser for DICTLINE.GEN — the main dictionary file.

Each line is fixed-width:
- Columns 0-18:   stem1 (19 chars)
- Columns 19-37:  stem2 (19 chars)
- Columns 38-56:  stem3 (19 chars)
- Columns 57-75:  stem4 (19 chars)
- Columns 76+:    POS-specific fields, translation record, meaning

The POS section and translation record are space-delimited after the stems.
"""

from __future__ import annotations

from pathlib import Path

from latincy_lexicon.enums import (
    Age,
    Area,
    Comparison,
    Frequency,
    Gender,
    Geo,
    NounKind,
    NumeralSort,
    PartOfSpeech,
    PronounKind,
    Source,
    VerbKind,
)
from latincy_lexicon.models import DictEntry

STEM_WIDTH = 19


def _safe_enum(enum_cls, value: str, default=None):
    """Try to parse an enum value, returning default on failure."""
    value = value.strip()
    if not value:
        return default
    try:
        return enum_cls(value)
    except ValueError:
        return default


def _parse_verb_kind(s: str) -> VerbKind | None:
    """Parse verb kind, handling multi-word values like TO_BE."""
    s = s.strip()
    if not s or s == "X":
        return VerbKind.X
    # Handle space-separated compound kinds
    s = s.replace(" ", "_")
    return _safe_enum(VerbKind, s, VerbKind.X)


def parse_dictline(path: str | Path) -> list[DictEntry]:
    """Parse DICTLINE.GEN into a list of DictEntry objects.

    Args:
        path: Path to DICTLINE.GEN file.

    Returns:
        List of DictEntry objects, one per line (excluding continuation lines).
    """
    path = Path(path)
    entries: list[DictEntry] = []

    for line_num, line in enumerate(path.read_text(encoding="latin-1").splitlines(), 1):
        if not line.strip():
            continue

        # Extract 4 stems (fixed-width 19 chars each)
        stem1 = line[0:STEM_WIDTH].strip()
        stem2 = line[STEM_WIDTH:STEM_WIDTH * 2].strip()
        stem3 = line[STEM_WIDTH * 2:STEM_WIDTH * 3].strip()
        stem4 = line[STEM_WIDTH * 3:STEM_WIDTH * 4].strip()

        # Everything after stems
        rest = line[STEM_WIDTH * 4:].strip()

        # Parse POS and remaining fields
        entry = _parse_rest(stem1, stem2, stem3, stem4, rest, line_num)
        if entry is not None:
            entries.append(entry)

    return entries


def _parse_rest(
    stem1: str, stem2: str, stem3: str, stem4: str,
    rest: str, line_num: int
) -> DictEntry | None:
    """Parse the portion after the 4 stems."""
    # Split into tokens
    tokens = rest.split()
    if not tokens:
        return None

    pos_str = tokens[0]
    pos = _safe_enum(PartOfSpeech, pos_str)
    if pos is None:
        return None

    # Index past POS
    idx = 1
    kwargs: dict = {}

    if pos in (PartOfSpeech.N,):
        # N  decl_which decl_var gender noun_kind
        if len(tokens) < idx + 4:
            return None
        decl_which = int(tokens[idx])
        decl_var = int(tokens[idx + 1])
        gender = _safe_enum(Gender, tokens[idx + 2], Gender.X)
        noun_kind = _safe_enum(NounKind, tokens[idx + 3], NounKind.X)
        idx += 4
        kwargs.update(gender=gender, noun_kind=noun_kind)

    elif pos in (PartOfSpeech.ADJ,):
        # ADJ  decl_which decl_var comparison
        if len(tokens) < idx + 3:
            return None
        decl_which = int(tokens[idx])
        decl_var = int(tokens[idx + 1])
        comp = _safe_enum(Comparison, tokens[idx + 2], Comparison.X)
        idx += 3
        kwargs.update(comparison=comp)

    elif pos in (PartOfSpeech.V, PartOfSpeech.VPAR, PartOfSpeech.SUPINE):
        # V  conj_which conj_var verb_kind
        if len(tokens) < idx + 3:
            return None
        decl_which = int(tokens[idx])
        decl_var = int(tokens[idx + 1])
        # verb_kind may be two words like "TO BE"
        vk_str = tokens[idx + 2]
        idx += 3
        # Check if next token is part of verb_kind (TO_BE, TO_BEING)
        if vk_str == "TO" and idx < len(tokens) and tokens[idx] in ("BE", "BEING"):
            vk_str = vk_str + "_" + tokens[idx]
            idx += 1
        verb_kind = _safe_enum(VerbKind, vk_str, VerbKind.X)
        kwargs.update(verb_kind=verb_kind)

    elif pos in (PartOfSpeech.PRON, PartOfSpeech.PACK):
        # PRON  decl_which decl_var pronoun_kind
        if len(tokens) < idx + 3:
            return None
        decl_which = int(tokens[idx])
        decl_var = int(tokens[idx + 1])
        pk = _safe_enum(PronounKind, tokens[idx + 2], PronounKind.X)
        idx += 3
        kwargs.update(pronoun_kind=pk)

    elif pos in (PartOfSpeech.NUM,):
        # NUM  decl_which decl_var numeral_sort numeric_value
        # NB: numeric_value is the actual cardinal/ordinal value (e.g. 3 for
        # tres, 5 for quinque). Without consuming it, the value gets read as
        # the age code, the rest of the metadata shifts by one, and the source
        # code 'X' ends up as the first word of the gloss ("X three;").
        if len(tokens) < idx + 3:
            return None
        decl_which = int(tokens[idx])
        decl_var = int(tokens[idx + 1])
        ns = _safe_enum(NumeralSort, tokens[idx + 2], NumeralSort.X)
        idx += 3
        # numeric_value is integer-valued; guard so we don't accidentally
        # consume the age code if a NUM entry omits the value field.
        if idx < len(tokens) and tokens[idx].lstrip("-").isdigit():
            idx += 1
        kwargs.update(numeral_sort=ns)

    elif pos in (PartOfSpeech.ADV,):
        # ADV  comparison
        if len(tokens) < idx + 1:
            return None
        comp = _safe_enum(Comparison, tokens[idx], Comparison.X)
        decl_which = 0
        decl_var = 0
        idx += 1
        kwargs.update(comparison=comp)

    elif pos in (PartOfSpeech.PREP,):
        # PREP  case
        if len(tokens) < idx + 1:
            return None
        # case field — skip it, not stored in DictEntry
        decl_which = 0
        decl_var = 0
        idx += 1

    elif pos in (PartOfSpeech.CONJ, PartOfSpeech.INTERJ):
        decl_which = 0
        decl_var = 0

    elif pos in (PartOfSpeech.PREFIX, PartOfSpeech.SUFFIX, PartOfSpeech.TACKON):
        decl_which = 0
        decl_var = 0

    else:
        decl_which = 0
        decl_var = 0

    # Now parse the translation record (5 single-char codes) and meaning
    # The remaining tokens before the meaning are: age area geo freq source
    # These are single characters
    remaining = tokens[idx:]

    # Find the translation record — 5 consecutive single-char tokens
    age = Age.X
    area = Area.X
    geo = Geo.X
    freq = Frequency.X
    source = Source.X
    meaning = ""

    if len(remaining) >= 5:
        # Try to parse 5 single-char translation codes
        tr_candidates = remaining[:5]
        if all(len(t) == 1 for t in tr_candidates):
            age = _safe_enum(Age, tr_candidates[0], Age.X)
            area = _safe_enum(Area, tr_candidates[1], Area.X)
            geo = _safe_enum(Geo, tr_candidates[2], Geo.X)
            freq = _safe_enum(Frequency, tr_candidates[3], Frequency.X)
            source = _safe_enum(Source, tr_candidates[4], Source.X)
            meaning = " ".join(remaining[5:])
        else:
            meaning = " ".join(remaining)
    else:
        meaning = " ".join(remaining)

    return DictEntry(
        stem1=stem1,
        stem2=stem2,
        stem3=stem3,
        stem4=stem4,
        pos=pos,
        decl_which=decl_which,
        decl_var=decl_var,
        age=age,
        area=area,
        geo=geo,
        freq=freq,
        source=source,
        meaning=meaning,
        line_number=line_num,
        **kwargs,
    )
