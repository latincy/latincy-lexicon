"""Disk cache for ``build_lexicon()``.

The full build is ~5s for ~39k entries, so the result is cached to a user cache
dir keyed by package version + DICTLINE content hash. These tests stub the heavy
build with a call counter so they exercise the caching wrapper, not the parse.
The ``_isolate_lexicon_cache`` autouse fixture (conftest) redirects the cache to
a tmp dir.
"""

from __future__ import annotations

import pytest

from latincy_lexicon import build as build_mod


def _stub_build(monkeypatch):
    """Replace the heavy parse/build with a counter-tracked stub."""
    calls = {"n": 0}

    def fake_prepare(vendor=None):
        return {"entries": [], "addons": [], "headwords": {}, "plural_mappings": {}}

    def fake_dict(entries, addons, headwords, plural_mappings):
        calls["n"] += 1
        return {"fake": [{"headword": "fake"}]}

    monkeypatch.setattr(build_mod, "_prepare", fake_prepare)
    monkeypatch.setattr(build_mod, "_build_lexicon_dict", fake_dict)
    return calls


def _vendor_with(tmp_path, name: str, content: bytes):
    d = tmp_path / name
    d.mkdir()
    (d / "DICTLINE.GEN").write_bytes(content)
    return d


def test_writes_and_reads_cache(tmp_path, monkeypatch):
    calls = _stub_build(monkeypatch)
    vendor = _vendor_with(tmp_path, "v", b"DICTLINE-CONTENT")

    first = build_mod.build_lexicon(vendor=vendor)
    assert calls["n"] == 1
    cache_files = list(build_mod._cache_dir().glob("lexicon-*.json"))
    assert len(cache_files) == 1

    second = build_mod.build_lexicon(vendor=vendor)
    assert calls["n"] == 1  # served from cache; no rebuild
    assert second == first


def test_use_cache_false_always_rebuilds(tmp_path, monkeypatch):
    calls = _stub_build(monkeypatch)
    vendor = _vendor_with(tmp_path, "v", b"X")

    build_mod.build_lexicon(vendor=vendor, use_cache=False)
    build_mod.build_lexicon(vendor=vendor, use_cache=False)
    assert calls["n"] == 2


def test_hash_mismatch_rebuilds(tmp_path, monkeypatch):
    calls = _stub_build(monkeypatch)
    v1 = _vendor_with(tmp_path, "v1", b"AAA")
    v2 = _vendor_with(tmp_path, "v2", b"BBB")

    build_mod.build_lexicon(vendor=v1)
    build_mod.build_lexicon(vendor=v2)
    assert calls["n"] == 2  # different DICTLINE → different key → rebuild

    build_mod.build_lexicon(vendor=v1)
    assert calls["n"] == 2  # v1 still cached


def test_cache_key_depends_only_on_dictline_content(tmp_path):
    same_a = _vendor_with(tmp_path, "a", b"AAA")
    same_b = _vendor_with(tmp_path, "b", b"AAA")
    diff_c = _vendor_with(tmp_path, "c", b"CCC")

    assert build_mod._lexicon_cache_key(same_a) == build_mod._lexicon_cache_key(same_b)
    assert build_mod._lexicon_cache_key(same_a) != build_mod._lexicon_cache_key(diff_c)
