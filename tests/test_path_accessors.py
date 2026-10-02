"""Tests for the bundled L&S path accessors (senses_path, sense_index_path).

These accessors expose the lewis_short_senses.json and lewis_short_index.json
files that are shipped inside the wheel under data/json/.
"""

from __future__ import annotations

from pathlib import Path


def test_senses_path_returns_path_object():
    from latincy_lexicon.build import senses_path

    result = senses_path()
    assert isinstance(result, Path)


def test_senses_path_ends_with_expected_filename():
    from latincy_lexicon.build import senses_path

    # the wheel ships the gzip twin since 0.12; a dev checkout may hold the plain file
    assert senses_path().name in ("lewis_short_senses.json.gz", "lewis_short_senses.json")


def test_senses_path_file_exists():
    from latincy_lexicon.build import senses_path

    assert senses_path().exists(), (
        f"lewis_short_senses.json[.gz] not found at {senses_path()}. "
        "Run `latincy-lexicon build-ls` to regenerate."
    )


def test_load_senses_reads_bundled_store_with_citation_records():
    from latincy_lexicon.build import load_senses

    store = load_senses()
    narro = store["n30406"]
    assert narro["slug"] == "narro"
    one_I = next(s for s in narro["senses"] if s["level"] == "I")
    assert len(one_I["citation_records"]) >= 30
    assert one_I["citation_records"][0]["ordinal"] >= 1
    assert narro["entry_citations"][0]["location"] == "etym"


def test_load_senses_reads_a_plain_json_path(tmp_path):
    import json

    from latincy_lexicon.build import load_senses

    p = tmp_path / "s.json"
    p.write_text(json.dumps({"n1": {"key": "x", "slug": "x", "senses": []}}), encoding="utf-8")
    assert load_senses(p) == {"n1": {"key": "x", "slug": "x", "senses": []}}


def test_sense_index_path_returns_path_object():
    from latincy_lexicon.build import sense_index_path

    result = sense_index_path()
    assert isinstance(result, Path)


def test_sense_index_path_ends_with_expected_filename():
    from latincy_lexicon.build import sense_index_path

    assert sense_index_path().name == "lewis_short_index.json"


def test_sense_index_path_file_exists():
    from latincy_lexicon.build import sense_index_path

    assert sense_index_path().exists(), (
        f"lewis_short_index.json not found at {sense_index_path()}. "
        "Run `latincy-lexicon build-ls` to regenerate."
    )


def test_accessors_importable_from_package_root():
    from latincy_lexicon import load_senses, sense_index_path, senses_path  # noqa: F401

    assert callable(senses_path)
    assert callable(sense_index_path)
    assert callable(load_senses)


def test_load_senses_strips_provenance_header():
    from latincy_lexicon.build import load_senses

    assert "_meta" not in load_senses()


def test_load_senses_meta_carries_source_and_licence():
    from latincy_lexicon.build import load_senses_meta

    meta = load_senses_meta()
    assert meta["license"] == "CC-BY-SA-4.0"
    assert meta["modified"] is True
    assert meta["source"]["license_url"] == "https://creativecommons.org/licenses/by-sa/4.0/"
    assert meta["source"]["file"] == "lat.ls.perseus-eng2.xml"
