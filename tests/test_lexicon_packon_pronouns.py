"""Regression test: lemmas formed via PACKON (pronoun + tackon) must be
present in the exported lexicon so `token._.lexicon` lookups succeed.

Bug: analyzing the surface form ``quicquam`` through the spaCy pipeline
correctly produced ``lemma=quisquam`` via the upstream lemmatizer, but
``lex.get("quisquam")`` returned ``None`` because ``quisquam`` has no
entry in DICTLINE.GEN -- its paradigm is assembled at runtime from
``qu``/``quis`` + the ``-quam`` TACKON. The site rendered
``No dictionary entries for quicquam.`` as a result.

The same gap affects every PACKON pronoun (``quisque``, ``quidam``,
``quispiam``, ``quilibet``, ``quivis``, ``quicumque``, ``quisquam``).

Fix: synthesize dictionary entries for the PACKON-formed indefinite
pronouns as a post-parse patch, parallel to the existing ``sum/esse``
patch in ``build.py::_patch_sum_esse``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


LEXICON_JSON = Path(__file__).parent.parent / "data" / "json" / "lexicon.json"

skip_no_data = pytest.mark.skipif(
    not LEXICON_JSON.exists(),
    reason="lexicon.json not available (run: latincy-lexicon build)",
)


@pytest.fixture(scope="module")
def lexicon() -> dict:
    with open(LEXICON_JSON) as f:
        return json.load(f)


# Each PACKON lemma paired with a substring we expect to appear (case-
# insensitive) somewhere in its glosses. The substrings come from the
# canonical PACKON comment in ADDONS.LAT.
PACKON_LEMMAS: list[tuple[str, str]] = [
    ("quisquam",  "any"),
    ("quisque",   "each"),
    ("quidam",    "certain"),
    ("quispiam",  "some"),
    ("quilibet",  "anyone"),
    ("quivis",    "whoever"),
    ("quicumque", "whoever"),
]


@skip_no_data
@pytest.mark.parametrize("lemma,expected_substr", PACKON_LEMMAS)
def test_packon_pronoun_has_lexicon_entry(
    lexicon: dict, lemma: str, expected_substr: str
) -> None:
    """Every PACKON-formed pronoun lemma must have a PRON lexicon entry
    with a non-empty gloss, so `token._.lexicon` is non-empty for every
    form of the paradigm.
    """
    entries = lexicon.get(lemma)
    assert entries, (
        f"lexicon[{lemma!r}] is missing -- PACKON pronouns formed via "
        f"pronoun + TACKON have no DICTLINE entry and were dropped from "
        f"the lexicon export."
    )
    pron_entries = [e for e in entries if e.get("pos") == "PRON"]
    assert pron_entries, (
        f"lexicon[{lemma!r}] has no PRON entry; got: {entries}"
    )
    top = pron_entries[0]
    glosses = " ".join(top.get("glosses") or []).lower()
    assert glosses, f"lexicon[{lemma!r}] PRON entry has empty glosses: {top}"
    assert expected_substr in glosses, (
        f"lexicon[{lemma!r}] PRON entry glosses do not contain "
        f"{expected_substr!r}; got: {top}"
    )


ANALYZER_JSON = Path(__file__).parent.parent / "data" / "json" / "analyzer.json"

skip_no_analyzer = pytest.mark.skipif(
    not ANALYZER_JSON.exists(),
    reason="analyzer.json not available (run: latincy-lexicon build)",
)


@skip_no_analyzer
def test_quicquam_analyzer_parses_via_uniques() -> None:
    """The analyzer should produce at least one PRON parse for `quicquam`
    with a proper gloss. This is already handled by the UNIQUES lookup;
    the test guards against future regressions in the analyzer path.
    """
    from latincy_lexicon.analyzer import Analyzer

    analyzer = Analyzer.from_json(ANALYZER_JSON)
    parses = analyzer.analyze("quicquam")
    assert parses, "analyzer produced no parses for 'quicquam'"
    pron_parses = [p for p in parses if p.pos == "PRON"]
    assert pron_parses, f"no PRON parse for 'quicquam'; got: {parses}"
    top = pron_parses[0]
    assert top.meaning, f"parse has no meaning: {top}"
    assert "any" in top.meaning.lower(), (
        f"parse meaning doesn't convey 'any': {top.meaning!r}"
    )
