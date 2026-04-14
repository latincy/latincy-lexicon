"""Parser for INFLECTS.LAT — inflection endings table.

Format (space-delimited, varies by POS):
  N     1 1 NOM S C  1 1 a         X A
  V     1 1 PRES  ACTIVE  IND  1 S  1 1 o    X A
  ADJ   1 1 NOM S M POS   1 2 us   X A

Fields:
  POS decl_which decl_var [grammatical attrs] stem_key ending_len ending age freq
  -- comments are stripped
"""

from __future__ import annotations

from pathlib import Path

from latincy_lexicon.enums import Age, Frequency, PartOfSpeech
from latincy_lexicon.models import Inflection


def parse_inflects(path: str | Path) -> list[Inflection]:
    """Parse INFLECTS.LAT into a list of Inflection objects."""
    path = Path(path)
    entries: list[Inflection] = []

    for line_num, line in enumerate(path.read_text(encoding="latin-1").splitlines(), 1):
        # Strip comments
        if "--" in line:
            line = line[:line.index("--")]
        line = line.strip()
        if not line:
            continue

        tokens = line.split()
        if len(tokens) < 4:
            continue

        pos_str = tokens[0]
        try:
            pos = PartOfSpeech(pos_str)
        except ValueError:
            continue

        entry = _parse_inflection(pos, tokens[1:], line_num)
        if entry is not None:
            entries.append(entry)

    return entries


def _safe_enum(cls, val, default):
    try:
        return cls(val)
    except ValueError:
        return default


def _parse_inflection(pos: PartOfSpeech, tokens: list[str], line_num: int) -> Inflection | None:
    """Parse tokens after POS into an Inflection."""
    kwargs: dict = {"pos": pos, "line_number": line_num}

    try:
        if pos == PartOfSpeech.N:
            # decl_which decl_var case number gender stem_key ending_len ending age freq
            kwargs["decl_which"] = int(tokens[0])
            kwargs["decl_var"] = int(tokens[1])
            kwargs["case"] = tokens[2]
            kwargs["number"] = tokens[3]
            kwargs["gender"] = tokens[4]
            kwargs["stem_key"] = int(tokens[5])
            ending_len = int(tokens[6])
            if ending_len > 0:
                kwargs["ending"] = tokens[7]
                age_idx = 8
            else:
                kwargs["ending"] = ""
                age_idx = 7
            kwargs["age"] = _safe_enum(Age, tokens[age_idx], Age.X)
            kwargs["freq"] = _safe_enum(Frequency, tokens[age_idx + 1], Frequency.X)

        elif pos == PartOfSpeech.ADJ:
            # decl_which decl_var case number gender comparison stem_key ending_len ending age freq
            kwargs["decl_which"] = int(tokens[0])
            kwargs["decl_var"] = int(tokens[1])
            kwargs["case"] = tokens[2]
            kwargs["number"] = tokens[3]
            kwargs["gender"] = tokens[4]
            kwargs["comparison"] = tokens[5]
            kwargs["stem_key"] = int(tokens[6])
            ending_len = int(tokens[7])
            if ending_len > 0:
                kwargs["ending"] = tokens[8]
                age_idx = 9
            else:
                kwargs["ending"] = ""
                age_idx = 8
            kwargs["age"] = _safe_enum(Age, tokens[age_idx], Age.X)
            kwargs["freq"] = _safe_enum(Frequency, tokens[age_idx + 1], Frequency.X)

        elif pos == PartOfSpeech.V:
            # conj_which conj_var tense voice mood person number stem_key ending_len ending age freq
            kwargs["decl_which"] = int(tokens[0])
            kwargs["decl_var"] = int(tokens[1])
            kwargs["tense"] = tokens[2]
            kwargs["voice"] = tokens[3]
            kwargs["mood"] = tokens[4]
            kwargs["person"] = tokens[5]
            kwargs["number"] = tokens[6]
            kwargs["stem_key"] = int(tokens[7])
            ending_len = int(tokens[8])
            if ending_len > 0:
                kwargs["ending"] = tokens[9]
                age_idx = 10
            else:
                kwargs["ending"] = ""
                age_idx = 9
            kwargs["age"] = _safe_enum(Age, tokens[age_idx], Age.X)
            kwargs["freq"] = _safe_enum(Frequency, tokens[age_idx + 1], Frequency.X)

        elif pos == PartOfSpeech.VPAR:
            # decl_which decl_var case number gender tense voice mood stem_key ending_len ending age freq
            kwargs["decl_which"] = int(tokens[0])
            kwargs["decl_var"] = int(tokens[1])
            kwargs["case"] = tokens[2]
            kwargs["number"] = tokens[3]
            kwargs["gender"] = tokens[4]
            kwargs["tense"] = tokens[5]
            kwargs["voice"] = tokens[6]
            kwargs["mood"] = tokens[7]
            kwargs["stem_key"] = int(tokens[8])
            ending_len = int(tokens[9])
            if ending_len > 0:
                kwargs["ending"] = tokens[10]
                age_idx = 11
            else:
                kwargs["ending"] = ""
                age_idx = 10
            kwargs["age"] = _safe_enum(Age, tokens[age_idx], Age.X)
            kwargs["freq"] = _safe_enum(Frequency, tokens[age_idx + 1], Frequency.X)

        elif pos == PartOfSpeech.SUPINE:
            # decl_which decl_var case number gender stem_key ending_len ending age freq
            kwargs["decl_which"] = int(tokens[0])
            kwargs["decl_var"] = int(tokens[1])
            kwargs["case"] = tokens[2]
            kwargs["number"] = tokens[3]
            kwargs["gender"] = tokens[4]
            kwargs["stem_key"] = int(tokens[5])
            ending_len = int(tokens[6])
            if ending_len > 0:
                kwargs["ending"] = tokens[7]
                age_idx = 8
            else:
                kwargs["ending"] = ""
                age_idx = 7
            kwargs["age"] = _safe_enum(Age, tokens[age_idx], Age.X)
            kwargs["freq"] = _safe_enum(Frequency, tokens[age_idx + 1], Frequency.X)

        elif pos == PartOfSpeech.PRON:
            # decl_which decl_var case number gender stem_key ending_len ending age freq
            kwargs["decl_which"] = int(tokens[0])
            kwargs["decl_var"] = int(tokens[1])
            kwargs["case"] = tokens[2]
            kwargs["number"] = tokens[3]
            kwargs["gender"] = tokens[4]
            kwargs["stem_key"] = int(tokens[5])
            ending_len = int(tokens[6])
            if ending_len > 0:
                kwargs["ending"] = tokens[7]
                age_idx = 8
            else:
                kwargs["ending"] = ""
                age_idx = 7
            kwargs["age"] = _safe_enum(Age, tokens[age_idx], Age.X)
            kwargs["freq"] = _safe_enum(Frequency, tokens[age_idx + 1], Frequency.X)

        elif pos == PartOfSpeech.NUM:
            # decl_which decl_var case number gender numeral_sort stem_key ending_len ending age freq
            kwargs["decl_which"] = int(tokens[0])
            kwargs["decl_var"] = int(tokens[1])
            kwargs["case"] = tokens[2]
            kwargs["number"] = tokens[3]
            kwargs["gender"] = tokens[4]
            kwargs["numeral_sort"] = tokens[5]
            kwargs["stem_key"] = int(tokens[6])
            ending_len = int(tokens[7])
            if ending_len > 0:
                kwargs["ending"] = tokens[8]
                age_idx = 9
            else:
                kwargs["ending"] = ""
                age_idx = 8
            kwargs["age"] = _safe_enum(Age, tokens[age_idx], Age.X)
            kwargs["freq"] = _safe_enum(Frequency, tokens[age_idx + 1], Frequency.X)

        elif pos in (PartOfSpeech.ADV, PartOfSpeech.PREP, PartOfSpeech.CONJ, PartOfSpeech.INTERJ):
            # Simpler: limited fields, just comparison/case + stem_key ending_len age freq
            # ADV  comparison stem_key ending_len  age freq
            # PREP case stem_key ending_len age freq
            # CONJ stem_key ending_len age freq
            # INTERJ stem_key ending_len age freq
            kwargs["decl_which"] = 0
            kwargs["decl_var"] = 0

            if pos == PartOfSpeech.ADV:
                kwargs["comparison"] = tokens[0]
                kwargs["stem_key"] = int(tokens[1])
                ending_len = int(tokens[2])
                if ending_len > 0:
                    kwargs["ending"] = tokens[3]
                    age_idx = 4
                else:
                    kwargs["ending"] = ""
                    age_idx = 3
            elif pos == PartOfSpeech.PREP:
                kwargs["case"] = tokens[0]
                kwargs["stem_key"] = int(tokens[1])
                ending_len = int(tokens[2])
                if ending_len > 0:
                    kwargs["ending"] = tokens[3]
                    age_idx = 4
                else:
                    kwargs["ending"] = ""
                    age_idx = 3
            else:
                # CONJ, INTERJ
                kwargs["stem_key"] = int(tokens[0])
                ending_len = int(tokens[1])
                if ending_len > 0:
                    kwargs["ending"] = tokens[2]
                    age_idx = 3
                else:
                    kwargs["ending"] = ""
                    age_idx = 2

            kwargs["age"] = _safe_enum(Age, tokens[age_idx], Age.X)
            kwargs["freq"] = _safe_enum(Frequency, tokens[age_idx + 1], Frequency.X)

        else:
            return None

    except (IndexError, ValueError):
        return None

    return Inflection(**kwargs)
