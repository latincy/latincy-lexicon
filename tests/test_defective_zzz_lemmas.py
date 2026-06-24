"""Regression: Whitaker's 'zzz' stem placeholder must never become a lemma.

Defective paradigms (PERFDEF/impersonal verbs like memini/odi/novi, the
comparative-only adjectives deterior/ulterior, comparative adverbs, the
reflexive pronoun, and a couple of pluralia tantum nouns) carry 'zzz' in
stem1 because they have no first principal part. Headword reconstruction used
to append a present ending to that placeholder, leaking junk lemmas like
``zzzo``/``zzzeo``/``zzz`` (and citation forms such as ``zzzo, osere``) all the
way downstream into latincy-vocab.

This test builds the bundled lexicon and asserts the placeholder is gone and
the affected entries get real Latin lemmas.
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture(scope="module")
def lexicon(tmp_path_factory) -> dict:
    from latincy_lexicon.build import build

    out = tmp_path_factory.mktemp("lex")
    build(output_dir=out)
    with open(out / "lexicon.json") as f:
        return json.load(f)


def test_no_lemma_key_contains_zzz(lexicon):
    leaked = [k for k in lexicon if "zzz" in k]
    assert leaked == [], f"placeholder lemmas leaked into the lexicon: {leaked}"


def test_no_headword_or_principal_part_contains_zzz(lexicon):
    bad = []
    for key, entries in lexicon.items():
        for e in entries:
            if "zzz" in (e.get("headword") or ""):
                bad.append((key, "headword", e["headword"]))
            for pp in e.get("principal_parts") or []:
                if "zzz" in pp:
                    bad.append((key, "principal_part", pp))
    assert bad == [], f"placeholder leaked into entry fields: {bad[:10]}"


def _verb_entry(lexicon: dict, headword: str, gloss_substr: str) -> dict | None:
    # Keys are normalized (v→u, j→i), so search by the entry's headword field.
    for entries in lexicon.values():
        for e in entries:
            if (e.get("pos") == "V" and e.get("headword") == headword
                    and any(gloss_substr in g for g in (e.get("glosses") or []))):
                return e
    return None


@pytest.mark.parametrize(
    "lemma,gloss",
    [
        ("odi", "hate"),
        ("perodi", "hate greatly"),
        ("memini", "remember"),
        ("novi", "know"),
    ],
)
def test_defective_verbs_relemmatized(lexicon, lemma, gloss):
    assert _verb_entry(lexicon, lemma, gloss) is not None, (
        f"expected defective verb '{lemma}' ({gloss}) in lexicon"
    )


def test_comparative_only_adjectives_present(lexicon):
    assert any(e.get("pos") == "ADJ" for e in lexicon.get("deterior", []))
    assert any(e.get("pos") == "ADJ" for e in lexicon.get("ulterior", []))
