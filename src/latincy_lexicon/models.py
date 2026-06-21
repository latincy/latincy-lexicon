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


@dataclass(frozen=True)
class LewisShortEntry:
    """A single Lewis & Short ``<entryFree>`` from the Perseus TEI.

    Source: PerseusDL/lexica ``lat.ls.perseus-eng2.xml`` (CC BY-SA 4.0).
    """
    id: str                      # stable TEI id, e.g. "n1605"
    key: str                     # headword, homograph-numbered: "ago", "abactus1"
    orth: str = ""               # macron-bearing orthography, e.g. "ăgo"
    pos: str = ""                # L&S part-of-speech abbreviation, e.g. "v. a."
    gen: str = ""                # gender for nouns (often L&S's only POS signal): "m.", "f.", "n."
    itype: str = ""              # inflection info / principal parts, e.g. "ēgi, actum, 3"
    text: str = ""               # plain-text rendering of the entry body

    @property
    def headword(self) -> str:
        """The ``key`` with any trailing homograph digits removed ("abactus1" -> "abactus")."""
        return self.key.rstrip("0123456789")


@dataclass(frozen=True)
class LewisShortSense:
    """One reconstructed L&S sense node (see ``parsers.lewis_short_senses``).

    A typed view over the parser's sense dict. ``to_dict`` reproduces that dict
    shape exactly, so ``LewisShortSense.from_dict(d).to_dict() == d``.
    """
    id: str                      # minted sense IRI: w3id.org/latincy/lemma/{slug}/sense/{path}
    level: str                   # tree path label, e.g. "I", "I.A", "II.B"
    n: str = ""                  # original L&S @n label
    gloss: str = ""              # lead italic gloss (raw)
    display_gloss: str = ""      # resolved display gloss (own / inherited / entry-primary)
    perseus_ls_id: str = ""      # Perseus L&S sense xml:id, e.g. "n30406.0"
    perseus: Optional[str] = None        # resolvable Hopper entry URL
    lila: Optional[str] = None           # LiLa L&S sense-node IRI
    citations: tuple[str, ...] = ()      # CTS bibl URNs (evidence)
    citation_tr: tuple[tuple[str, str], ...] = ()  # (urn, per-citation gloss) pairs

    @classmethod
    def from_dict(cls, d: dict) -> "LewisShortSense":
        same = d.get("sameAs", {})
        return cls(
            id=d["id"],
            level=d["level"],
            n=d.get("n", ""),
            gloss=d.get("gloss", ""),
            display_gloss=d.get("display_gloss", ""),
            perseus_ls_id=same.get("perseus_ls_id", ""),
            perseus=same.get("perseus"),
            lila=same.get("lila"),
            citations=tuple(d.get("citations", ())),
            citation_tr=tuple(d.get("citation_tr", {}).items()),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "level": self.level,
            "n": self.n,
            "gloss": self.gloss,
            "display_gloss": self.display_gloss,
            "sameAs": {
                "perseus_ls_id": self.perseus_ls_id,
                "perseus": self.perseus,
                "lila": self.lila,
            },
            "citations": list(self.citations),
            "citation_tr": dict(self.citation_tr),
        }


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
