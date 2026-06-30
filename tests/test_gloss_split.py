"""Tests for bracket/paren-aware gloss splitting."""

from latincy_lexicon.glosses import (
    extract_sources,
    split_glosses,
    strip_usage_note,
)


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


# ---------------------------------------------------------------------------
# leading-artifact cleaning (WW pipe marker and dash-space prefix)
# ---------------------------------------------------------------------------


def test_strip_leading_pipe():
    assert split_glosses("|counting-board") == ["counting-board"]


def test_strip_leading_pipe_keeps_rest():
    assert split_glosses("|forswearing, denial under oath") == [
        "forswearing, denial under oath"
    ]


def test_strip_multiple_leading_pipes():
    # WW uses multi-pipe sense numbering across DICTLINE lines (||, |||).
    assert split_glosses("||double") == ["double"]
    assert split_glosses("|||doubtful/undecided/wavering") == [
        "doubtful/undecided/wavering"
    ]


def test_split_glosses_clean_false_preserves_artifacts():
    # clean=False is the raw original split used to capture gloss_orig.
    assert split_glosses("||double", clean=False) == ["||double"]
    assert split_glosses("- away, off", clean=False) == ["- away, off"]
    assert split_glosses("a; |b", clean=False) == ["a", "|b"]


def test_strip_leading_dash_space():
    assert split_glosses("- away, off") == ["away, off"]


def test_keep_suffix_gloss_dash():
    # Suffix glosses (dash immediately followed by a letter) are real content.
    assert split_glosses("-ing") == ["-ing"]
    assert split_glosses("-ate, -ship, the office of") == [
        "-ate, -ship, the office of"
    ]


def test_keep_trailing_dash():
    assert split_glosses("two-") == ["two-"]


def test_strip_leading_artifact_per_piece():
    assert split_glosses("foo; |bar") == ["foo", "bar"]


# ---------------------------------------------------------------------------
# _clean_glosses (build helper: cleaned glosses + source_refs + gloss_orig)
# ---------------------------------------------------------------------------


def test_clean_glosses_records_original_when_changed():
    from latincy_lexicon.build import _clean_glosses

    meaning = "fear, dread, be afraid (ne + SUB = lest; ut or ne non + SUB = that ... not)"
    glosses, sources, orig = _clean_glosses(meaning)
    assert glosses == ["fear, dread, be afraid"]
    assert sources == []
    assert orig == [meaning]  # verbatim original split, kept for reference


def test_clean_glosses_records_sources_and_original():
    from latincy_lexicon.build import _clean_glosses

    glosses, sources, orig = _clean_glosses("epitomize (Souter)")
    assert glosses == ["epitomize"]
    assert sources == ["Souter"]
    assert orig == ["epitomize (Souter)"]


def test_clean_glosses_no_original_when_unchanged():
    from latincy_lexicon.build import _clean_glosses

    glosses, sources, orig = _clean_glosses("god; divine being")
    assert glosses == ["god", "divine being"]
    assert sources == []
    assert orig is None  # nothing changed -> no gloss_orig needed


# ---------------------------------------------------------------------------
# extract_sources (bibliographic citations -> metadata)
# ---------------------------------------------------------------------------


def test_extract_sources_whole_paren():
    assert extract_sources("epitomize (Souter)") == ("epitomize", ["Souter"])


def test_extract_sources_whole_paren_ls():
    assert extract_sources("deny/refuse reproachfully (L+S)") == (
        "deny/refuse reproachfully",
        ["L+S"],
    )


def test_extract_sources_embedded_keeps_content():
    assert extract_sources("small song-bird (thistle/gold finch L+S)") == (
        "small song-bird (thistle/gold finch)",
        ["L+S"],
    )


def test_extract_sources_embedded_with_comma():
    assert extract_sources("copious (L+S, Late Latin)") == (
        "copious (Late Latin)",
        ["L+S"],
    )


def test_extract_sources_embedded_with_question():
    assert extract_sources("(thrush or owl? L+S)") == ("(thrush or owl?)", ["L+S"])


def test_extract_sources_mid_gloss_paren():
    assert extract_sources("parable (L+S), allegory") == (
        "parable, allegory",
        ["L+S"],
    )


def test_extract_sources_nested_inner_paren():
    assert extract_sources(
        "(esp. those who brought grain from Ostia to Rome (L+S))"
    ) == ("(esp. those who brought grain from Ostia to Rome)", ["L+S"])


def test_extract_sources_bare_word_is_content():
    # "Pliny" as the gloss of the proper noun Plinius is content, not a
    # citation — only parenthesised source tokens are extracted.
    assert extract_sources("Pliny") == ("Pliny", [])


def test_extract_sources_none():
    assert extract_sources("nettle (plant)") == ("nettle (plant)", [])


def test_extract_sources_ecc_is_not_a_source():
    assert extract_sources("monastery (Ecc)") == ("monastery (Ecc)", [])


def test_extract_sources_no_paren():
    assert extract_sources("fear, dread") == ("fear, dread", [])


# ---------------------------------------------------------------------------
# strip_usage_note
# ---------------------------------------------------------------------------


def test_strip_usage_note_timeo():
    meaning = "fear, dread, be afraid (ne + SUB = lest; ut or ne non + SUB = that ... not)"
    assert strip_usage_note(meaning) == "fear, dread, be afraid"


def test_strip_usage_note_leaves_domain_paren():
    assert strip_usage_note("in front (of)") == "in front (of)"


def test_strip_usage_note_leaves_register_annotation():
    assert strip_usage_note("God (Christian text)") == "God (Christian text)"


def test_strip_usage_note_no_leading_text():
    assert strip_usage_note("(SUB for audeo-kludge)") == "(SUB for audeo-kludge)"


def test_strip_usage_note_no_paren():
    assert strip_usage_note("fear, dread") == "fear, dread"


def test_strip_usage_note_case_government():
    assert strip_usage_note("help (w/DAT)") == "help"
    assert strip_usage_note("relying on (w/ABL)") == "relying on"
    assert strip_usage_note("approach (w/DAT or ad+ACC)") == "approach"


def test_strip_usage_note_only_case_restriction():
    assert strip_usage_note("epic poem (only in NOM and ACC S)") == "epic poem"


def test_strip_usage_note_keeps_complement_marker():
    # "(of)" is an English-idiom complement marker, not a case code — keep it.
    assert strip_usage_note("in front (of)") == "in front (of)"


def test_strip_usage_note_arrow_xref():
    assert (
        strip_usage_note("to, towards, near, for, together (adeo => go to)")
        == "to, towards, near, for, together"
    )
    assert (
        strip_usage_note("away, off (aufero => make off with, carry away)")
        == "away, off"
    )


def test_strip_usage_note_leaves_whole_paren_xref():
    # No leading gloss content -> whole-paren note (category E), left as-is.
    assert (
        strip_usage_note("(M. Antonius -> Mark Antony, triumvir)")
        == "(M. Antonius -> Mark Antony, triumvir)"
    )
