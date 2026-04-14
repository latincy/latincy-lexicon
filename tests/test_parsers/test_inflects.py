"""Tests for INFLECTS parser."""

from tests.conftest import VENDOR_DIR, skip_no_vendor
from latincy_lexicon.parsers.inflects import parse_inflects


@skip_no_vendor
def test_parse_count():
    entries = parse_inflects(VENDOR_DIR / "INFLECTS.LAT")
    assert len(entries) > 1700


@skip_no_vendor
def test_noun_inflections():
    entries = parse_inflects(VENDOR_DIR / "INFLECTS.LAT")
    nouns = [e for e in entries if e.pos == "N"]
    assert len(nouns) > 200
    # First declension nominative singular
    nom_1_1 = [e for e in nouns if e.decl_which == 1 and e.decl_var == 1
                and e.case == "NOM" and e.number == "S"]
    assert any(e.ending == "a" for e in nom_1_1)


@skip_no_vendor
def test_verb_inflections():
    entries = parse_inflects(VENDOR_DIR / "INFLECTS.LAT")
    verbs = [e for e in entries if e.pos == "V"]
    assert len(verbs) > 600
    # First conjugation present active indicative 1st person singular
    v_1_1 = [e for e in verbs if e.decl_which == 1 and e.decl_var == 1
              and e.tense == "PRES" and e.voice == "ACTIVE" and e.mood == "IND"
              and e.person == "1" and e.number == "S"]
    assert any(e.ending == "o" for e in v_1_1)
