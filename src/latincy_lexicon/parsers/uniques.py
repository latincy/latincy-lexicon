"""Parser for UNIQUES.LAT — irregular/unique forms.

Format (3 lines per entry):
  form
  POS  decl_which decl_var [grammatical attrs] verb_kind/noun_kind  age area geo freq source
  meaning
"""

from __future__ import annotations

from pathlib import Path

from latincy_lexicon.enums import PartOfSpeech
from latincy_lexicon.models import Unique


def parse_uniques(path: str | Path) -> list[Unique]:
    """Parse UNIQUES.LAT into a list of Unique objects."""
    path = Path(path)
    lines = path.read_text(encoding="latin-1").splitlines()
    entries: list[Unique] = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip blank/comment lines
        if not line or line.startswith("--"):
            i += 1
            continue

        # Line 1: the unique form
        form = line
        i += 1

        # Line 2: POS + grammatical spec
        if i >= len(lines):
            break
        spec_line = lines[i].strip()
        i += 1

        # Line 3: meaning
        if i >= len(lines):
            meaning = ""
        else:
            meaning = lines[i].strip()
            i += 1

        entry = _parse_unique_entry(form, spec_line, meaning)
        if entry is not None:
            entries.append(entry)

    return entries


def _safe_pos(s: str) -> PartOfSpeech:
    try:
        return PartOfSpeech(s)
    except ValueError:
        return PartOfSpeech.X


def _parse_unique_entry(form: str, spec: str, meaning: str) -> Unique | None:
    """Parse a single unique entry from its spec line."""
    tokens = spec.split()
    if not tokens:
        return None

    pos = _safe_pos(tokens[0])
    kwargs: dict = {"form": form, "pos": pos, "meaning": meaning}

    try:
        if pos == PartOfSpeech.V:
            # V  conj_which conj_var tense voice mood person number verb_kind  age area geo freq source
            kwargs["decl_which"] = int(tokens[1])
            kwargs["decl_var"] = int(tokens[2])
            kwargs["tense"] = tokens[3]
            kwargs["voice"] = tokens[4]
            kwargs["mood"] = tokens[5]
            kwargs["person"] = tokens[6]
            kwargs["number"] = tokens[7]
            # verb_kind may be compound
            vk_idx = 8
            vk = tokens[vk_idx]
            if vk == "TO" and vk_idx + 1 < len(tokens) and tokens[vk_idx + 1] in ("BE", "BEING"):
                vk = vk + "_" + tokens[vk_idx + 1]
                vk_idx += 1
            # Skip remaining translation record codes

        elif pos in (PartOfSpeech.N, PartOfSpeech.PRON):
            kwargs["decl_which"] = int(tokens[1])
            kwargs["decl_var"] = int(tokens[2])
            if len(tokens) > 5:
                kwargs["case"] = tokens[3]
                kwargs["number"] = tokens[4]
                kwargs["gender"] = tokens[5]

        elif pos == PartOfSpeech.ADJ:
            kwargs["decl_which"] = int(tokens[1])
            kwargs["decl_var"] = int(tokens[2])
            if len(tokens) > 5:
                kwargs["case"] = tokens[3]
                kwargs["number"] = tokens[4]
                kwargs["gender"] = tokens[5]
                if len(tokens) > 6:
                    kwargs["comparison"] = tokens[6]

        else:
            if len(tokens) > 1:
                try:
                    kwargs["decl_which"] = int(tokens[1])
                except ValueError:
                    pass
            if len(tokens) > 2:
                try:
                    kwargs["decl_var"] = int(tokens[2])
                except ValueError:
                    pass

    except (IndexError, ValueError):
        pass

    return Unique(**kwargs)
