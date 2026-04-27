"""The whitakers_words component must enrich token._.lexicon with entries
reachable through the morphological analyzer's parses, not only entries
keyed by the spaCy-assigned lemma.

Concretely: the surface form ``cano`` is ambiguous between the verb
``cano`` (1sg pres ind) and the adjective ``canus`` (dat/abl m/n sg).
The lemmatizer assigns it to the verb, so a lemma-only lookup misses the
adj reading entirely. The analyzer's parses include the adj headword,
and this enrichment surfaces the corresponding lexicon entry.
"""

from __future__ import annotations

import pytest

spacy = pytest.importorskip("spacy")


@pytest.fixture(scope="module")
def nlp(tmp_path_factory):
    """Minimal pipeline with the whitakers_words component attached."""
    from latincy_lexicon.build import build

    out = tmp_path_factory.mktemp("lex")
    build(output_dir=out)

    nlp = spacy.blank("la")
    nlp.add_pipe(
        "whitakers_words",
        config={
            "lexicon_path": str(out / "lexicon.json"),
            "analyzer_path": str(out / "analyzer.json"),
        },
    )
    return nlp


def _entries_with_pos(token, pos: str) -> list[dict]:
    return [e for e in (token._.lexicon or []) if e.get("pos") == pos]


def _headwords(entries: list[dict]) -> set[str]:
    return {e["headword"] for e in entries}


def test_cano_form_surfaces_canus_adj_via_inflection(nlp):
    """Surface form `cano`, lemma=cano (verb): we still want canus (adj)
    to appear because the analyzer parses cano as dat/abl m/n sg of canus."""
    doc = nlp("cano")
    tok = doc[0]
    headwords = _headwords(tok._.lexicon or [])
    assert "cano" in headwords, "verb cano should still be present"
    assert "canus" in headwords, (
        f"adj canus should be enriched in via inflection; got {headwords}"
    )
    adj_canus = [
        e for e in (tok._.lexicon or [])
        if e["headword"] == "canus" and e["pos"] == "ADJ"
    ]
    assert adj_canus, "expected at least one canus ADJ entry"
    assert adj_canus[0].get("match_type") == "inflection"


def test_inflection_form_cani_still_resolves_canus(nlp):
    """Surface form `cani` (genitive of canus): the lemmatizer may assign
    lemma=canus, in which case lemma lookup already finds it. Either way,
    the user must see canus entries."""
    doc = nlp("cani")
    tok = doc[0]
    assert "canus" in _headwords(tok._.lexicon or [])


def test_same_pos_homographs_both_surface(nlp):
    """carmen has two NOUN entries (freq=A 'song' and freq=F 'card for
    wool/flax'). They share (headword, pos) but differ in glosses, so
    content-based dedup must keep both."""
    doc = nlp("carmen")
    tok = doc[0]
    noun_entries = [e for e in (tok._.lexicon or []) if e["pos"] == "N"]
    glosses_seen = {tuple(e.get("glosses") or ()) for e in noun_entries}
    assert len(glosses_seen) >= 2, (
        f"both carmen senses should surface; got glosses {glosses_seen}"
    )
    freqs = {e.get("freq") for e in noun_entries}
    assert {"A", "F"} <= freqs, (
        f"expected both freq=A (song) and freq=F (wool-card) entries; got {freqs}"
    )


def test_bonus_no_regression_on_lemma_match(nlp):
    """Surface form `bonus`, lemma=bonus: lemma-keyed lookup already
    surfaces both the ADJ and NOUN entries. Enrichment must not duplicate
    or drop them."""
    doc = nlp("bonus")
    tok = doc[0]
    headwords_pos = {(e["headword"], e["pos"]) for e in (tok._.lexicon or [])}
    assert ("bonus", "ADJ") in headwords_pos
    assert ("bonus", "N") in headwords_pos
    # No duplicates of (headword, pos)
    raw = [(e["headword"], e["pos"]) for e in (tok._.lexicon or [])]
    assert len(raw) == len(set(raw)), f"duplicate entries: {raw}"
