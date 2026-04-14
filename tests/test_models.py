"""Tests for Whitaker's Words data models."""

import pytest

from latincy_lexicon.enums import (
    AddonType,
    Age,
    Area,
    Frequency,
    Gender,
    Geo,
    NounKind,
    PartOfSpeech,
    Source,
    TrickClass,
    VerbKind,
)
from latincy_lexicon.models import (
    Addon,
    DictEntry,
    Inflection,
    LexiconEntry,
    Trick,
    Unique,
)


def test_dict_entry_creation():
    entry = DictEntry(
        stem1="am",
        stem2="am",
        stem3="amav",
        stem4="amat",
        pos=PartOfSpeech.V,
        decl_which=1,
        decl_var=1,
        verb_kind=VerbKind.TRANS,
        age=Age.X,
        freq=Frequency.A,
        meaning="love, like; fall in love with",
        line_number=1,
    )
    assert entry.stem1 == "am"
    assert entry.pos == PartOfSpeech.V
    assert entry.verb_kind == VerbKind.TRANS
    assert entry.freq == Frequency.A
    assert "love" in entry.meaning


def test_dict_entry_frozen():
    entry = DictEntry(
        stem1="bell",
        stem2="bell",
        stem3="",
        stem4="",
        pos=PartOfSpeech.N,
        decl_which=2,
        decl_var=1,
        gender=Gender.N,
        noun_kind=NounKind.T,
        meaning="war",
    )
    with pytest.raises(AttributeError):
        entry.stem1 = "other"


def test_dict_entry_defaults():
    entry = DictEntry(
        stem1="a", stem2="", stem3="", stem4="",
        pos=PartOfSpeech.X, decl_which=0, decl_var=0,
    )
    assert entry.gender is None
    assert entry.verb_kind is None
    assert entry.age == Age.X
    assert entry.meaning == ""
    assert entry.line_number == 0


def test_inflection_creation():
    infl = Inflection(
        pos=PartOfSpeech.N,
        decl_which=1,
        decl_var=1,
        case="NOM",
        number="S",
        gender="F",
        stem_key=1,
        ending="a",
        age=Age.X,
        freq=Frequency.A,
    )
    assert infl.ending == "a"
    assert infl.stem_key == 1
    assert infl.case == "NOM"


def test_addon_creation():
    addon = Addon(
        addon_type=AddonType.PREFIX,
        fix="ab",
        meaning="away from",
    )
    assert addon.addon_type == AddonType.PREFIX
    assert addon.fix == "ab"


def test_unique_creation():
    uniq = Unique(
        form="quoque",
        pos=PartOfSpeech.CONJ,
        meaning="also, too",
    )
    assert uniq.form == "quoque"
    assert uniq.pos == PartOfSpeech.CONJ


def test_trick_creation():
    trick = Trick(
        trick_class=TrickClass.ANY,
        from_text="ae",
        to_text="e",
        explanation="ae => e (Caesar => Cesar)",
    )
    assert trick.trick_class == TrickClass.ANY
    assert trick.from_text == "ae"


def test_lexicon_entry_mutable():
    lex = LexiconEntry(
        headword="amo",
        normalized_headword="amo",
        pos="V",
        glosses=["love", "like"],
        principal_parts=["amo", "amare", "amavi", "amatus"],
        verb_kind="TRANS",
        age="X",
        freq="A",
    )
    assert lex.headword == "amo"
    assert len(lex.glosses) == 2
    assert len(lex.principal_parts) == 4
    # LexiconEntry is mutable (runtime use)
    lex.glosses.append("cherish")
    assert len(lex.glosses) == 3


def test_dict_entry_noun():
    entry = DictEntry(
        stem1="ros",
        stem2="ros",
        stem3="",
        stem4="",
        pos=PartOfSpeech.N,
        decl_which=3,
        decl_var=1,
        gender=Gender.F,
        noun_kind=NounKind.X,
        age=Age.C,
        area=Area.X,
        geo=Geo.X,
        freq=Frequency.C,
        source=Source.O,
        meaning="dew; spray, splash",
    )
    assert entry.gender == Gender.F
    assert entry.age == Age.C
    assert entry.source == Source.O
