"""Frozen dataclasses for Whitaker's Words data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from latincy_lexicon.enums import (
    AddonType,
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
    TrickClass,
    VerbKind,
)


@dataclass(frozen=True)
class DictEntry:
    """A single DICTLINE entry."""
    stem1: str
    stem2: str
    stem3: str
    stem4: str
    pos: PartOfSpeech
    decl_which: int  # declension/conjugation number
    decl_var: int    # variant within declension/conjugation
    # POS-specific fields
    gender: Optional[Gender] = None        # N, ADJ, PRON
    noun_kind: Optional[NounKind] = None   # N
    verb_kind: Optional[VerbKind] = None   # V
    pronoun_kind: Optional[PronounKind] = None  # PRON
    comparison: Optional[Comparison] = None     # ADJ, ADV
    numeral_sort: Optional[NumeralSort] = None  # NUM
    # Translation record
    age: Age = Age.X
    area: Area = Area.X
    geo: Geo = Geo.X
    freq: Frequency = Frequency.X
    source: Source = Source.X
    meaning: str = ""
    # Line number in source file (for debugging)
    line_number: int = 0


@dataclass(frozen=True)
class Inflection:
    """An INFLECTS entry defining an ending pattern."""
    pos: PartOfSpeech
    decl_which: int
    decl_var: int
    # Grammatical attributes vary by POS
    case: str = "X"
    number: str = "X"
    gender: str = "X"
    tense: str = "X"
    voice: str = "X"
    mood: str = "X"
    person: str = "0"
    comparison: str = "X"
    numeral_sort: str = "X"
    stem_key: int = 0     # which stem (1-4) this ending attaches to
    ending: str = ""
    age: Age = Age.X
    freq: Frequency = Frequency.X
    line_number: int = 0


@dataclass(frozen=True)
class Addon:
    """A PREFIX, SUFFIX, TACKON, or PACKON entry."""
    addon_type: AddonType
    fix: str              # the prefix/suffix/tackon text
    connect: str = ""     # connection character(s)
    from_pos: PartOfSpeech = PartOfSpeech.X
    to_pos: PartOfSpeech = PartOfSpeech.X
    meaning: str = ""
    line_number: int = 0


@dataclass(frozen=True)
class Unique:
    """A UNIQUES entry — irregular form with full spec."""
    form: str
    pos: PartOfSpeech = PartOfSpeech.X
    decl_which: int = 0
    decl_var: int = 0
    case: str = "X"
    number: str = "X"
    gender: str = "X"
    tense: str = "X"
    voice: str = "X"
    mood: str = "X"
    person: str = "0"
    comparison: str = "X"
    stem1: str = ""
    stem2: str = ""
    stem3: str = ""
    stem4: str = ""
    meaning: str = ""
    line_number: int = 0


@dataclass(frozen=True)
class Trick:
    """A morphological trick rule."""
    trick_class: TrickClass
    from_text: str
    to_text: str
    explanation: str = ""


@dataclass
class LexiconEntry:
    """Runtime lexicon entry for a single lemma, combining Words data."""
    headword: str
    normalized_headword: str
    pos: str
    glosses: list[str] = field(default_factory=list)
    principal_parts: list[str] = field(default_factory=list)
    gender: Optional[str] = None
    verb_kind: Optional[str] = None
    noun_kind: Optional[str] = None
    comparison: Optional[str] = None
    age: str = "X"
    freq: str = "X"
    area: str = "X"
    geo: str = "X"
    source: str = "X"
