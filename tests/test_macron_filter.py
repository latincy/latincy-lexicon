"""Tests for macron morphological filter (Class 1) in Analyzer.

The filter takes a macronized form (e.g. "puellā"), looks it up in a
kaikki-derived index, intersects the UD feature sets across all candidates,
and uses the intersection to post-filter the WW parses returned by analyze().
"""

import json
import pytest
from pathlib import Path

from latincy_lexicon.analyzer import (
    Analyzer,
    Parse,
    _has_macrons,
    _strip_macrons,
    _parse_ud_morph,
)

ANALYZER_JSON = Path(__file__).parent.parent / "data" / "json" / "analyzer.json"
skip_no_data = pytest.mark.skipif(
    not ANALYZER_JSON.exists(),
    reason="analyzer.json not built; run: latincy-lexicon build",
)

# puellā  → unambiguous ABL sg F
# puellīs → ambiguous DAT pl F or ABL pl F; intersection: Number=Plur, Gender=Fem
# rēgēs   → not in mini index (fallback test)
_MINI_INDEX = {
    "puellā": [{"morph": "Case=Abl|Gender=Fem|Number=Sing"}],
    "puellīs": [
        {"morph": "Case=Dat|Gender=Fem|Number=Plur"},
        {"morph": "Case=Abl|Gender=Fem|Number=Plur"},
    ],
    "scrībit": [{"morph": "Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin|Voice=Act"}],
}


def _mini_analyzer(macron_index=None):
    a = Analyzer([], [], [], [], {}, {})
    a._macron_index = macron_index
    return a


def _parse(**kwargs):
    defaults = dict(form="x", lemma="puella", headword="puella", pos="N")
    defaults.update(kwargs)
    return Parse(**defaults)


# ── _has_macrons ──────────────────────────────────────────────────────────────

def test_has_macrons_plain():
    assert not _has_macrons("puella")
    assert not _has_macrons("scribit")


def test_has_macrons_macronized():
    assert _has_macrons("puellā")
    assert _has_macrons("puellīs")
    assert _has_macrons("scrībit")
    assert _has_macrons("rēgēs")


# ── _strip_macrons ────────────────────────────────────────────────────────────

def test_strip_macrons_basic():
    assert _strip_macrons("puellā") == "puella"
    assert _strip_macrons("puellīs") == "puellis"
    assert _strip_macrons("scrībit") == "scribit"


def test_strip_macrons_no_change():
    assert _strip_macrons("puella") == "puella"
    assert _strip_macrons("rex") == "rex"


def test_strip_macrons_uppercase():
    assert _strip_macrons("Puellā") == "Puella"


# ── _parse_ud_morph ───────────────────────────────────────────────────────────

def test_parse_ud_morph_basic():
    assert _parse_ud_morph("Case=Abl|Gender=Fem|Number=Sing") == {
        "Case": "Abl",
        "Gender": "Fem",
        "Number": "Sing",
    }


def test_parse_ud_morph_single():
    assert _parse_ud_morph("Number=Plur") == {"Number": "Plur"}


def test_parse_ud_morph_empty():
    assert _parse_ud_morph("") == {}


# ── _parse_matches_ud ─────────────────────────────────────────────────────────

def test_parse_matches_ud_case_match():
    a = _mini_analyzer()
    p = _parse(case="ABL", number="S", gender="F")
    assert a._parse_matches_ud(p, {"Case": "Abl"})


def test_parse_matches_ud_case_mismatch():
    a = _mini_analyzer()
    p = _parse(case="NOM", number="S", gender="F")
    assert not a._parse_matches_ud(p, {"Case": "Abl"})


def test_parse_matches_ud_x_is_wildcard():
    a = _mini_analyzer()
    # case=X means "don't care" — passes any Case filter
    p = _parse(case="X", number="S")
    assert a._parse_matches_ud(p, {"Case": "Abl"})
    assert a._parse_matches_ud(p, {"Case": "Nom"})


def test_parse_matches_ud_number_match():
    a = _mini_analyzer()
    p = _parse(case="DAT", number="P", gender="F")
    assert a._parse_matches_ud(p, {"Number": "Plur"})


def test_parse_matches_ud_number_mismatch():
    a = _mini_analyzer()
    p = _parse(case="DAT", number="S", gender="F")
    assert not a._parse_matches_ud(p, {"Number": "Plur"})


def test_parse_matches_ud_common_gender_passes_fem_filter():
    a = _mini_analyzer()
    # DICTLINE marks 1st-decl nouns as C (common); kaikki says Fem — must not reject
    p = _parse(case="ABL", number="S", gender="C")
    assert a._parse_matches_ud(p, {"Case": "Abl", "Gender": "Fem", "Number": "Sing"})


def test_parse_matches_ud_multiple_features():
    a = _mini_analyzer()
    p = _parse(case="ABL", number="S", gender="F")
    assert a._parse_matches_ud(p, {"Case": "Abl", "Number": "Sing", "Gender": "Fem"})
    assert not a._parse_matches_ud(p, {"Case": "Abl", "Number": "Plur"})


# ── _filter_by_macrons ────────────────────────────────────────────────────────

def test_filter_unambiguous():
    a = _mini_analyzer(_MINI_INDEX)
    nom = _parse(form="puellā", case="NOM", number="S", gender="F")
    abl = _parse(form="puellā", case="ABL", number="S", gender="F")
    result = a._filter_by_macrons([nom, abl], "puellā")
    assert len(result) == 1
    assert result[0].case == "ABL"


def test_filter_ambiguous_intersection_keeps_plural():
    a = _mini_analyzer(_MINI_INDEX)
    # puellīs: index has DAT pl and ABL pl → intersection = {Gender=Fem, Number=Plur}
    dat_sg = _parse(form="puellīs", case="DAT", number="S", gender="F")
    dat_pl = _parse(form="puellīs", case="DAT", number="P", gender="F")
    abl_pl = _parse(form="puellīs", case="ABL", number="P", gender="F")
    result = a._filter_by_macrons([dat_sg, dat_pl, abl_pl], "puellīs")
    # dat_sg fails Number=Plur → dropped; dat_pl and abl_pl pass
    assert len(result) == 2
    assert {p.case for p in result} == {"DAT", "ABL"}
    assert all(p.number == "P" for p in result)


def test_filter_form_not_in_index():
    a = _mini_analyzer(_MINI_INDEX)
    p = _parse(form="rēgēs", case="NOM", number="P", gender="M")
    result = a._filter_by_macrons([p], "rēgēs")
    assert result == [p]


def test_filter_fallback_when_all_killed():
    a = _mini_analyzer(_MINI_INDEX)
    # Index says puellā → ABL only, but we only have VOC → filter kills all → return all
    voc = _parse(form="puellā", case="VOC", number="S", gender="F")
    result = a._filter_by_macrons([voc], "puellā")
    assert result == [voc]


def test_filter_preserves_form_spelling():
    a = _mini_analyzer(_MINI_INDEX)
    abl = _parse(form="puellā", case="ABL", number="S", gender="F")
    nom = _parse(form="puellā", case="NOM", number="S", gender="F")
    result = a._filter_by_macrons([nom, abl], "puellā")
    assert result[0].form == "puellā"


# ── analyze() end-to-end ──────────────────────────────────────────────────────

@skip_no_data
def test_analyze_plain_form_returns_multiple(tmp_path):
    """Plain puella (no macrons) → multiple parses (NOM, ABL, VOC) even with index."""
    idx = tmp_path / "macron.json"
    idx.write_text(json.dumps(_MINI_INDEX))
    a = Analyzer.from_json(ANALYZER_JSON, macron_path=idx)
    parses = a.analyze("puella")
    assert len(parses) > 1


@skip_no_data
def test_analyze_macronized_no_index_returns_multiple():
    """Without index, macronized form strips macrons and returns all WW parses."""
    a = Analyzer.from_json(ANALYZER_JSON)
    parses = a.analyze("puellā")
    assert len(parses) > 1


@skip_no_data
def test_analyze_macronized_abl_filtered(tmp_path):
    """puellā with index → filtered to ABL only."""
    idx = tmp_path / "macron.json"
    idx.write_text(json.dumps(_MINI_INDEX))
    a = Analyzer.from_json(ANALYZER_JSON, macron_path=idx)
    parses = a.analyze("puellā")
    assert len(parses) >= 1
    assert all(p.case == "ABL" for p in parses)


@skip_no_data
def test_analyze_macronized_puellis_plural_only(tmp_path):
    """puellīs with index → only plural parses survive intersection."""
    idx = tmp_path / "macron.json"
    idx.write_text(json.dumps(_MINI_INDEX))
    a = Analyzer.from_json(ANALYZER_JSON, macron_path=idx)
    parses = a.analyze("puellīs")
    assert len(parses) >= 1
    assert all(p.number == "P" for p in parses)


@skip_no_data
def test_analyze_macronized_form_preserves_spelling(tmp_path):
    """Parse.form should carry the macronized input spelling."""
    idx = tmp_path / "macron.json"
    idx.write_text(json.dumps(_MINI_INDEX))
    a = Analyzer.from_json(ANALYZER_JSON, macron_path=idx)
    parses = a.analyze("puellā")
    assert all(p.form == "puellā" for p in parses)


@skip_no_data
def test_from_json_macron_path_none():
    """macron_path=None (default) → _macron_index is None, no filtering."""
    a = Analyzer.from_json(ANALYZER_JSON)
    assert a._macron_index is None
