"""Tests for Whitaker's Words enum types."""

from latincy_lexicon.enums import (
    AddonType,
    Age,
    Area,
    Case,
    Comparison,
    Frequency,
    Gender,
    Geo,
    Mood,
    NounKind,
    Number,
    NumeralSort,
    PartOfSpeech,
    Person,
    PronounKind,
    Source,
    Tense,
    TrickClass,
    VerbKind,
    Voice,
)


def test_pos_values():
    assert PartOfSpeech.N == "N"
    assert PartOfSpeech.V == "V"
    assert PartOfSpeech.ADJ == "ADJ"
    assert PartOfSpeech.PREP == "PREP"
    assert PartOfSpeech.CONJ == "CONJ"
    assert PartOfSpeech.INTERJ == "INTERJ"


def test_pos_from_string():
    assert PartOfSpeech("N") == PartOfSpeech.N
    assert PartOfSpeech("V") == PartOfSpeech.V
    assert PartOfSpeech("ADJ") == PartOfSpeech.ADJ


def test_gender_values():
    assert Gender.M == "M"
    assert Gender.F == "F"
    assert Gender.N == "N"
    assert Gender.C == "C"
    assert Gender.X == "X"


def test_case_values():
    assert Case.NOM == "NOM"
    assert Case.GEN == "GEN"
    assert Case.ACC == "ACC"
    assert Case.ABL == "ABL"


def test_number_values():
    assert Number.S == "S"
    assert Number.P == "P"


def test_tense_values():
    assert Tense.PRES == "PRES"
    assert Tense.PERF == "PERF"
    assert Tense.FUTP == "FUTP"


def test_voice_values():
    assert Voice.ACTIVE == "ACTIVE"
    assert Voice.PASSIVE == "PASSIVE"


def test_mood_values():
    assert Mood.IND == "IND"
    assert Mood.SUB == "SUB"
    assert Mood.PPL == "PPL"


def test_person_values():
    assert Person.FIRST == "1"
    assert Person.THIRD == "3"
    assert Person.X == "0"


def test_comparison_values():
    assert Comparison.POS == "POS"
    assert Comparison.COMP == "COMP"
    assert Comparison.SUPER == "SUPER"


def test_noun_kind_values():
    assert NounKind.S == "S"
    assert NounKind.N == "N"
    assert NounKind.P == "P"


def test_verb_kind_values():
    assert VerbKind.TRANS == "TRANS"
    assert VerbKind.DEP == "DEP"
    assert VerbKind.TO_BE == "TO_BE"


def test_pronoun_kind_values():
    assert PronounKind.PERS == "PERS"
    assert PronounKind.REL == "REL"
    assert PronounKind.DEMONS == "DEMONS"


def test_numeral_sort_values():
    assert NumeralSort.CARD == "CARD"
    assert NumeralSort.ORD == "ORD"


def test_age_values():
    assert Age.A == "A"
    assert Age.C == "C"  # Classical
    assert Age.X == "X"


def test_frequency_values():
    assert Frequency.A == "A"
    assert Frequency.F == "F"
    assert Frequency.X == "X"


def test_area_values():
    assert Area.A == "A"
    assert Area.W == "W"  # War/military
    assert Area.E == "E"  # Church


def test_geo_values():
    assert Geo.H == "H"  # Greece
    assert Geo.I == "I"  # Italy


def test_source_values():
    assert Source.O == "O"  # OLD
    assert Source.G == "G"  # Lewis & Short


def test_addon_type_values():
    assert AddonType.PREFIX == "PREFIX"
    assert AddonType.SUFFIX == "SUFFIX"
    assert AddonType.TACKON == "TACKON"
    assert AddonType.PACKON == "PACKON"


def test_trick_class_values():
    assert TrickClass.ANY == "ANY"
    assert TrickClass.MEDIAEVAL == "MEDIAEVAL"
    assert TrickClass.SYNCOPE == "SYNCOPE"


def test_all_enums_are_str():
    """All enum values should be usable as strings."""
    assert f"POS: {PartOfSpeech.N}" == "POS: N"
    assert f"Age: {Age.C}" == "Age: C"
    assert f"Kind: {VerbKind.DEP}" == "Kind: DEP"
