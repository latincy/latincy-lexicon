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


def test_analyzer_only_mode_populates_ww_and_gloss():
    """use_bundled_lexicon=False with the analyzer left at its new default
    (True) is a meaningful, previously-untested shape: token._.lexicon stays
    None (no lemma-keyed lookup), but token._.ww / token._.gloss still populate
    purely from analyzer parses."""
    nlp = spacy.blank("la")
    pipe = nlp.add_pipe("whitakers_words", config={"use_bundled_lexicon": False})
    doc = pipe(_doc_with_lemma(nlp, "amo", "amo", "VERB"))
    tok = doc[0]
    assert tok._.lexicon is None
    assert tok._.ww  # analyzer parses present
    assert tok._.gloss  # gloss derived from the top parse, not the lexicon


def test_lexicon_path_suppresses_bundled_analyzer(tmp_path):
    """An explicit lexicon_path signals the caller is taking control of data
    sources — like use_bundled_lexicon, use_bundled_analyzer must also opt out,
    not just build the bundled WW analyzer anyway (regression: previously only
    an explicit analyzer_path suppressed it)."""
    import json

    custom_lex = tmp_path / "custom_lexicon.json"
    custom_lex.write_text(json.dumps({"amo": []}), encoding="utf-8")

    nlp = spacy.blank("la")
    pipe = nlp.add_pipe("whitakers_words", config={"lexicon_path": str(custom_lex)})
    assert pipe._use_bundled_analyzer is False


def test_use_bundled_analyzer_false_round_trips_through_bytes():
    """An explicit use_bundled_analyzer=False must survive to_bytes/from_bytes
    onto a freshly-constructed (default-config) receiving pipe — a bare
    truthy check on write previously made an explicit False indistinguishable
    from "key absent", silently reverting to the default True on load."""
    nlp = spacy.blank("la")
    nlp.add_pipe(
        "whitakers_words",
        config={"use_bundled_analyzer": False, "use_bundled_lexicon": True},
    )
    data = nlp.to_bytes()

    nlp2 = spacy.blank("la")
    nlp2.add_pipe("whitakers_words")  # default config: use_bundled_analyzer=True
    nlp2.from_bytes(data)
    assert nlp2.get_pipe("whitakers_words")._use_bundled_analyzer is False


def test_use_bundled_analyzer_false_round_trips_through_disk(tmp_path):
    nlp = spacy.blank("la")
    nlp.add_pipe(
        "whitakers_words",
        config={"use_bundled_analyzer": False, "use_bundled_lexicon": True},
    )
    nlp.to_disk(tmp_path)

    nlp2 = spacy.blank("la")
    nlp2.add_pipe("whitakers_words")  # default config: use_bundled_analyzer=True
    nlp2.from_disk(tmp_path)
    assert nlp2.get_pipe("whitakers_words")._use_bundled_analyzer is False


def test_macron_path_forwarded_to_bundled_analyzer(tmp_path):
    """macron_path must reach the analyzer even when it's built via the
    bundled default path (no explicit analyzer_path) — previously
    build_analyzer() had no macron_path parameter at all, so the documented
    macron filter silently never engaged under the default config."""
    import json

    macra = tmp_path / "macra.json"
    macra.write_text(json.dumps({}), encoding="utf-8")

    nlp = spacy.blank("la")
    pipe = nlp.add_pipe("whitakers_words", config={"macron_path": str(macra)})
    pipe._ensure_loaded()
    assert pipe._analyzer._macron_index is not None
