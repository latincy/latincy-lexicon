"""Tests for bracket/paren-aware gloss splitting."""

from latincy_lexicon.glosses import split_glosses


def test_plain_semicolon_splits():
    assert split_glosses("a; b; c") == ["a", "b", "c"]


def test_single_gloss():
    assert split_glosses("nor") == ["nor"]


def test_empty_string():
    assert split_glosses("") == []


def test_whitespace_only():
    assert split_glosses("   ") == []


def test_semicolon_inside_brackets_not_split_neque():
    meaning = "nor [neque..neque=>neither..nor; neque solum..sed etiam=>not only..but also]"
    assert split_glosses(meaning) == [
        "nor [neque..neque=>neither..nor; neque solum..sed etiam=>not only..but also]"
    ]


def test_semicolon_inside_parens_not_split_anagnosis():
    meaning = "lectionary; (book of lessons for divine service; list of appointed passages)"
    assert split_glosses(meaning) == [
        "lectionary",
        "(book of lessons for divine service; list of appointed passages)",
    ]


def test_parens_nested_inside_brackets():
    # Real DICTLINE shape: `[regnavit a(nnis). XLIIII => he reigned for 44 years]`
    meaning = "year; abb. ann./a.; [regnavit a(nnis). XLIIII => he reigned for 44 years]"
    assert split_glosses(meaning) == [
        "year",
        "abb. ann./a.",
        "[regnavit a(nnis). XLIIII => he reigned for 44 years]",
    ]


def test_trailing_semicolon_and_whitespace():
    assert split_glosses("  a ;  b ; ") == ["a", "b"]


def test_empty_chunks_dropped():
    assert split_glosses("a;;b") == ["a", "b"]
