"""The public in-memory ``build_lexicon()`` API.

``build_lexicon()`` returns the same lexicon dict that ``build()`` writes to
``lexicon.json``, but without touching disk — the path downstream consumers
(latincy-vocab, the ``whitakers_words`` component) use to get glosses + citation
forms from the *bundled* DICTLINE, with the defective-verb (zzz) fix already
applied. See [[project_latincy_vocab_design]] for why this exists.
"""

from __future__ import annotations

import json


def test_build_lexicon_returns_dict():
    from latincy_lexicon import build_lexicon

    lex = build_lexicon()
    assert isinstance(lex, dict)
    assert len(lex) > 30_000  # ~36.5k keys from bundled DICTLINE


def test_build_lexicon_matches_file_build(tmp_path):
    """In-memory build is byte-for-byte the same data as the file build."""
    from latincy_lexicon import build_lexicon
    from latincy_lexicon.build import build

    build(output_dir=tmp_path)
    with open(tmp_path / "lexicon.json") as f:
        from_file = json.load(f)

    assert build_lexicon() == from_file


def test_build_lexicon_has_no_zzz_keys():
    from latincy_lexicon import build_lexicon

    leaked = [k for k in build_lexicon() if "zzz" in k]
    assert leaked == [], f"placeholder lemmas leaked: {leaked}"


def test_build_lexicon_odi_citation():
    """odi must render the fixed defective citation, never 'zzzo, osere'."""
    from latincy_lexicon import build_lexicon, format_principal_parts

    lex = build_lexicon()
    odi = next(
        e
        for entries in lex.values()
        for e in entries
        if e.get("pos") == "V"
        and e.get("headword") == "odi"
        and any("hate" in g for g in (e.get("glosses") or []))
    )
    assert format_principal_parts(odi) == "odi, odisse, osus sum"
