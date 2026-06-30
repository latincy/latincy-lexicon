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

    assert senses_path().name == "lewis_short_senses.json"


def test_senses_path_file_exists():
    from latincy_lexicon.build import senses_path

    assert senses_path().exists(), (
        f"lewis_short_senses.json not found at {senses_path()}. "
        "Run `latincy-lexicon build-ls` to regenerate."
    )


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
    from latincy_lexicon import sense_index_path, senses_path  # noqa: F401

    assert callable(senses_path)
    assert callable(sense_index_path)
