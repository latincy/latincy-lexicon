"""In-memory analyzer builder ``build_analyzer()``.

Mirrors ``build_lexicon``: builds the WW morphological analyzer from the bundled
raw data (no 15 MB ``analyzer.json`` on disk) and caches the payload to a user
cache dir keyed by package version + DICTLINE content hash. The cache tests stub
the heavy parse with a call counter so they exercise the caching wrapper, not the
parse; the ``_isolate_lexicon_cache`` autouse fixture (conftest) redirects the
cache to a tmp dir. One functional test does the real build end-to-end.
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
