"""``whitakers_words`` works with zero configuration.

`nlp.add_pipe("whitakers_words")` with no config must set ``token._.lexicon``
and ``token._.gloss`` by defaulting to the bundled in-memory ``build_lexicon()``
— so a pip-installed consumer (latincy-vocab) gets glosses + citation forms with
no prebuilt ``lexicon.json`` on disk. It also defaults to the bundled in-memory
analyzer (``build_analyzer()``), which recovers a gloss when the upstream
lemmatizer misses a form. Passing ``use_bundled_lexicon=False`` +
``use_bundled_analyzer=False`` opts out entirely (empty component).
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


def test_both_bundled_false_is_noop():
    """Opting out of *both* bundled data sources yields an empty component."""
    nlp = spacy.blank("la")
    pipe = nlp.add_pipe(
        "whitakers_words",
        config={"use_bundled_lexicon": False, "use_bundled_analyzer": False},
    )
    doc = pipe(_doc_with_lemma(nlp, "amo", "amo", "VERB"))
    assert doc[0]._.lexicon is None
    assert doc[0]._.gloss is None
    assert doc[0]._.ww is None


def test_bundled_analyzer_recovers_gloss_on_lemmatizer_miss():
    """Default config recovers a gloss even when the upstream lemma is wrong.

    ``contemplemur`` (pres. pass. subj. of deponent ``contemplor``) is a form the
    LatinCy lemmatizer can leave as its own surface form. Lemma-keyed lexicon
    lookup then misses, but the bundled analyzer segments the surface form and
    the component looks the entry up by headword. ``token.lemma_`` is left
    untouched (the lemmatizer owns it); the correction surfaces via
    ``token._.lexicon`` / ``token._.ww``.
    """
    nlp = spacy.blank("la")
    pipe = nlp.add_pipe("whitakers_words")  # default: analyzer ON
    doc = pipe(_doc_with_lemma(nlp, "contemplemur", "contemplemur", "VERB"))
    tok = doc[0]
    assert tok._.gloss  # non-empty gloss recovered
    assert "observe" in tok._.gloss
    assert tok.lemma_ == "contemplemur"  # lemma NOT overwritten
    assert tok._.ww  # analyzer parses present


def test_analyzer_off_drops_gloss_on_lemmatizer_miss():
    """With the analyzer opted out, the mis-lemmatized form has no gloss —
    the exact regression the bundled-analyzer default fixes."""
    nlp = spacy.blank("la")
    pipe = nlp.add_pipe("whitakers_words", config={"use_bundled_analyzer": False})
    doc = pipe(_doc_with_lemma(nlp, "contemplemur", "contemplemur", "VERB"))
    assert doc[0]._.gloss is None
