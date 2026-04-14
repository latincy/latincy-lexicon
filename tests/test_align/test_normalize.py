"""Tests for Latin normalization."""

from latincy_lexicon.align.normalize import normalize_latin, normalize_vj


def test_normalize_latin_basic():
    assert normalize_latin("verbum") == "uerbum"
    assert normalize_latin("Juno") == "iuno"
    assert normalize_latin("VENUS") == "uenus"


def test_normalize_latin_empty():
    assert normalize_latin("") == ""
    assert normalize_latin(None) is None


def test_normalize_latin_no_change():
    assert normalize_latin("amor") == "amor"
    assert normalize_latin("bellum") == "bellum"


def test_normalize_vj_preserves_case():
    assert normalize_vj("verbum") == "uerbum"
    assert normalize_vj("Verbum") == "Uerbum"
    assert normalize_vj("VERBUM") == "UERBUM"
    assert normalize_vj("Jerusalem") == "Ierusalem"


def test_normalize_vj_empty():
    assert normalize_vj("") == ""
