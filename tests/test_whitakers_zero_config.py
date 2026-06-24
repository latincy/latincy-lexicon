"""``whitakers_words`` works with zero configuration.

`nlp.add_pipe("whitakers_words")` with no config must set ``token._.lexicon``
and ``token._.gloss`` by defaulting to the bundled in-memory ``build_lexicon()``
— so a pip-installed consumer (latincy-vocab) gets glosses + citation forms with
no prebuilt ``lexicon.json`` on disk. Passing ``use_bundled_lexicon=False`` opts
out (analyzer-only / empty component).
"""

from __future__ import annotations

import spacy
from spacy.tokens import Doc

import latincy_lexicon.spacy  # noqa: F401 — ensure factory is registered


def _doc_with_lemma(nlp, word: str, lemma: str, pos: str) -> Doc:
    doc = Doc(nlp.vocab, words=[word])
    doc[0].lemma_ = lemma
    doc[0].pos_ = pos
    return doc


def test_zero_config_sets_lexicon_and_gloss():
    nlp = spacy.blank("la")
    pipe = nlp.add_pipe("whitakers_words")  # no config at all
    doc = pipe(_doc_with_lemma(nlp, "amo", "amo", "VERB"))
    assert doc[0]._.lexicon is not None
    assert doc[0]._.gloss  # non-empty gloss


def test_use_bundled_lexicon_false_is_noop():
    nlp = spacy.blank("la")
    pipe = nlp.add_pipe("whitakers_words", config={"use_bundled_lexicon": False})
    doc = pipe(_doc_with_lemma(nlp, "amo", "amo", "VERB"))
    assert doc[0]._.lexicon is None
    assert doc[0]._.gloss is None
