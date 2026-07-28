"""In-memory analyzer builder ``build_analyzer()`` and the combined
``build_lexicon_and_analyzer()``.

Mirrors ``build_lexicon``: builds the WW morphological analyzer from the bundled
raw data (no 15 MB ``analyzer.json`` on disk) and caches the payload to a user
cache dir keyed by package version + DICTLINE content hash. The cache tests stub
the heavy parse with a call counter so they exercise the caching wrapper, not the
parse; the ``_isolate_lexicon_cache`` autouse fixture (conftest) redirects the
cache to a tmp dir. One functional test does the real build end-to-end.

``build_lexicon_and_analyzer()`` shares a single ``_prepare()`` parse between
both builders when neither has a warm cache — the fix for the ~10s doubled
cold-start cost the review found once ``whitakers_words`` defaulted both
bundled sources on.
"""

from __future__ import annotations

from latincy_lexicon import build as build_mod
from latincy_lexicon.analyzer import Analyzer


def _stub_build(monkeypatch):
    """Replace the heavy parse + payload with counter-tracked stubs."""
    calls = {"n": 0}

    def fake_prepare(vendor=None):
        calls["n"] += 1
        return {"entries": [], "inflections": [], "uniques": [], "addons": [],
                "headwords": {}, "plural_mappings": {}}

    def fake_payload(entries, inflections, uniques, addons, headwords, plural_mappings):
        return {"inflections": [], "uniques": [], "tackons": [],
                "entries": [], "headwords": {}, "plural_mappings": {}}

    monkeypatch.setattr(build_mod, "_prepare", fake_prepare)
    monkeypatch.setattr(build_mod, "_analyzer_payload", fake_payload)
    return calls


def _vendor_with(tmp_path, name: str, content: bytes):
    d = tmp_path / name
    d.mkdir()
    (d / "DICTLINE.GEN").write_bytes(content)
    return d


def test_writes_and_reads_cache(tmp_path, monkeypatch):
    calls = _stub_build(monkeypatch)
    vendor = _vendor_with(tmp_path, "v", b"DICTLINE-CONTENT")

    first = build_mod.build_analyzer(vendor=vendor)
    assert isinstance(first, Analyzer)
    assert calls["n"] == 1
    cache_files = list(build_mod._cache_dir().glob("analyzer-*.json"))
    assert len(cache_files) == 1

    second = build_mod.build_analyzer(vendor=vendor)
    assert isinstance(second, Analyzer)
    assert calls["n"] == 1  # payload served from cache; no re-parse


def test_use_cache_false_always_rebuilds(tmp_path, monkeypatch):
    calls = _stub_build(monkeypatch)
    vendor = _vendor_with(tmp_path, "v", b"X")

    build_mod.build_analyzer(vendor=vendor, use_cache=False)
    build_mod.build_analyzer(vendor=vendor, use_cache=False)
    assert calls["n"] == 2


def test_hash_mismatch_rebuilds(tmp_path, monkeypatch):
    calls = _stub_build(monkeypatch)
    v1 = _vendor_with(tmp_path, "v1", b"AAA")
    v2 = _vendor_with(tmp_path, "v2", b"BBB")

    build_mod.build_analyzer(vendor=v1)
    build_mod.build_analyzer(vendor=v2)
    assert calls["n"] == 2  # different DICTLINE → different key → rebuild

    build_mod.build_analyzer(vendor=v1)
    assert calls["n"] == 2  # v1 still cached


def test_real_build_parses_deponent_subjunctive():
    """End-to-end: the real bundled build parses ``contemplemur`` (a form the
    lemmatizer commonly misses) to the ``contemplor`` headword with its gloss."""
    az = build_mod.build_analyzer(use_cache=False)
    parses = az.analyze("contemplemur")
    assert parses, "contemplemur should parse"
    top = parses[0]
    assert top.headword == "contemplo"  # deponent citation-form quirk (dataset)
    assert top.pos == "V"
    assert "observe" in top.meaning


def test_macron_path_forwarded_to_bundled_analyzer(tmp_path):
    """build_analyzer(macron_path=...) must reach the constructed Analyzer —
    previously build_analyzer() had no macron_path parameter at all, so a
    macron filter configured on whitakers_words silently never engaged unless
    an explicit analyzer_path was also given."""
    import json

    macra = tmp_path / "macra.json"
    macra.write_text(json.dumps({}), encoding="utf-8")

    az = build_mod.build_analyzer(use_cache=False, macron_path=str(macra))
    assert az._macron_index is not None


def _stub_build_lexicon_and_analyzer(monkeypatch):
    """Like _stub_build, but also stubs _build_lexicon_dict so both halves of
    build_lexicon_and_analyzer are counter-tracked."""
    calls = {"prepare": 0, "lexicon": 0, "analyzer": 0}

    def fake_prepare(vendor=None):
        calls["prepare"] += 1
        return {"entries": [], "inflections": [], "uniques": [], "addons": [],
                "headwords": {}, "plural_mappings": {}}

    def fake_lexicon_dict(entries, addons, headwords, plural_mappings):
        calls["lexicon"] += 1
        return {"fake": [{"headword": "fake"}]}

    def fake_payload(entries, inflections, uniques, addons, headwords, plural_mappings):
        calls["analyzer"] += 1
        return {"inflections": [], "uniques": [], "tackons": [],
                "entries": [], "headwords": {}, "plural_mappings": {}}

    monkeypatch.setattr(build_mod, "_prepare", fake_prepare)
    monkeypatch.setattr(build_mod, "_build_lexicon_dict", fake_lexicon_dict)
    monkeypatch.setattr(build_mod, "_analyzer_payload", fake_payload)
    return calls


def test_build_lexicon_and_analyzer_shares_one_prepare_call(tmp_path, monkeypatch):
    """The whole point of build_lexicon_and_analyzer: on a cold cache for both
    resources, _prepare() must run exactly once, not twice (the cost this
    review found: standalone build_lexicon() + build_analyzer() each call it
    independently, ~doubling first-call latency)."""
    calls = _stub_build_lexicon_and_analyzer(monkeypatch)
    vendor = _vendor_with(tmp_path, "v", b"DICTLINE-CONTENT")

    lexicon, analyzer = build_mod.build_lexicon_and_analyzer(vendor=vendor)
    assert lexicon == {"fake": [{"headword": "fake"}]}
    assert isinstance(analyzer, Analyzer)
    assert calls["prepare"] == 1
    assert calls["lexicon"] == 1
    assert calls["analyzer"] == 1

    # Warm cache: neither the shared parse nor either payload builder reruns.
    build_mod.build_lexicon_and_analyzer(vendor=vendor)
    assert calls["prepare"] == 1


def test_build_lexicon_and_analyzer_only_builds_missing_half(tmp_path, monkeypatch):
    """If one resource is already cached (e.g. from a prior standalone
    build_lexicon() call) but the other is cold, only the missing half is
    built — still via a single shared _prepare() call."""
    calls = _stub_build_lexicon_and_analyzer(monkeypatch)
    vendor = _vendor_with(tmp_path, "v", b"DICTLINE-CONTENT")

    build_mod.build_lexicon(vendor=vendor)  # warms the lexicon cache only
    assert calls["prepare"] == 1
    assert calls["lexicon"] == 1
    assert calls["analyzer"] == 0

    lexicon, analyzer = build_mod.build_lexicon_and_analyzer(vendor=vendor)
    assert calls["prepare"] == 2  # analyzer was cold, so _prepare ran again
    assert calls["lexicon"] == 1  # but the lexicon payload builder did not rerun
    assert calls["analyzer"] == 1
    assert isinstance(analyzer, Analyzer)
