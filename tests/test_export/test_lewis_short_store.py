"""Tests for the Lewis & Short JSON store builder."""

import json

from latincy_lexicon.export.lewis_short import build_lewis_short_store
from tests.test_parsers.test_lewis_short import SAMPLE_TEI


def _build(tmp_path):
    tei = tmp_path / "ls.xml"
    tei.write_text(SAMPLE_TEI, encoding="utf-8")
    stats = build_lewis_short_store(tei, tmp_path)
    store = json.loads((tmp_path / "lewis_short.json").read_text(encoding="utf-8"))
    index = json.loads((tmp_path / "lewis_short_index.json").read_text(encoding="utf-8"))
    return stats, store, index


def test_store_keyed_by_id(tmp_path):
    _, store, _ = _build(tmp_path)
    assert set(store) == {"n1605", "n42", "n43"}
    assert store["n1605"]["key"] == "ago"
    assert store["n1605"]["orth"] == "ăgo"
    assert store["n1605"]["pos"] == "v. a."


def test_index_groups_homographs_under_normalized_key(tmp_path):
    _, _, index = _build(tmp_path)
    # Both abactus homographs collapse to one normalized headword key.
    assert sorted(index["abactus"]) == ["n42", "n43"]
    assert index["ago"] == ["n1605"]


def test_index_is_normalized(tmp_path):
    # A j/v headword should be findable under its u/i-normalized form.
    tei = tmp_path / "ls.xml"
    tei.write_text(
        '<TEI.2><body><entryFree key="jam" id="n99">'
        '<orth>jam</orth><pos>adv.</pos> now</entryFree></body></TEI.2>',
        encoding="utf-8",
    )
    build_lewis_short_store(tei, tmp_path)
    index = json.loads((tmp_path / "lewis_short_index.json").read_text(encoding="utf-8"))
    assert "iam" in index
    assert index["iam"] == ["n99"]


def test_stats(tmp_path):
    stats, _, _ = _build(tmp_path)
    assert stats["entries"] == 3
    assert stats["index_keys"] == 2  # "ago" + "abactus"
