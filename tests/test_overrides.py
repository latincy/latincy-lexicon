"""Tests for the WW override layer.

See `src/latincy_lexicon/data/overrides/README.md` for the schema.

The overrides system layers curated corrections on top of the canonical
Whitaker's Words data without mutating the raw files. Each active TOML
file under `data/overrides/OVR-*.toml` describes a single change with a
stable ID, target lemma+pos, and a provenance-bearing operation. This
test covers both the pure function (`_apply_overrides`) and the
end-to-end integration in the exported lexicon.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from latincy_lexicon.build import _apply_overrides


# ---------------------------------------------------------------------------
# Unit tests — _apply_overrides operates on in-memory entry dicts
# ---------------------------------------------------------------------------


def _entry(stem1: str, pos: str, meaning: str, **extra) -> dict:
    """Minimal DictEntry-shaped dict for tests."""
    base = {
        "id": 0,
        "stem1": stem1, "stem2": "", "stem3": "", "stem4": "",
        "pos": pos,
        "decl_which": 0, "decl_var": 0,
        "gender": None, "noun_kind": None, "verb_kind": None,
        "pronoun_kind": None, "comparison": None, "numeral_sort": None,
        "age": "X", "area": "X", "geo": "X", "freq": "X", "source": "X",
        "meaning": meaning,
        "line_number": None,
    }
    base.update(extra)
    return base


def test_apply_overrides_borrow_from(tmp_path: Path) -> None:
    """An active override with `borrow_from` copies the field from the
    source entry into the target entry and records provenance."""
    # Arrange — two entries, one override directory with a borrow
    entries = [
        _entry("neque", "CONJ", "nor [neque..neque=>neither..nor; foo];", id=1),
        _entry("nec",   "CONJ", "nor, and..not; not..either;",            id=2),
    ]
    ovr_dir = tmp_path / "overrides"
    ovr_dir.mkdir()
    (ovr_dir / "OVR-001-neque-conj.toml").write_text(
        """
id = "OVR-001"
date = 2026-04-21
author = "test"
status = "active"

[target]
lemma = "neque"
pos = "CONJ"

[change]
field = "meaning"

[change.borrow_from]
lemma = "nec"
pos = "CONJ"
field = "meaning"

reason = "test"
reason_short = "test"
""".strip()
    )

    # Act
    _apply_overrides(entries, ovr_dir)

    # Assert — target mutated, source untouched, provenance attached
    neque = next(e for e in entries if e["stem1"] == "neque")
    nec = next(e for e in entries if e["stem1"] == "nec")
    assert neque["meaning"] == "nor, and..not; not..either;"
    assert nec["meaning"] == "nor, and..not; not..either;"  # unchanged
    assert len(neque["_overrides"]) == 1
    ovr = neque["_overrides"][0]
    assert ovr["id"] == "OVR-001"
    assert ovr["field"] == "meaning"
    assert ovr["original_value"] == "nor [neque..neque=>neither..nor; foo];"
    assert ovr["source"] == {
        "kind": "borrow", "lemma": "nec", "pos": "CONJ", "field": "meaning",
    }


def test_apply_overrides_literal_replacement(tmp_path: Path) -> None:
    """An override with `change.to` replaces the field with a literal
    value and records provenance (no `source` borrow)."""
    entries = [_entry("foo", "N", "original;", id=1)]
    ovr_dir = tmp_path / "overrides"
    ovr_dir.mkdir()
    (ovr_dir / "OVR-002-foo.toml").write_text(
        """
id = "OVR-002"
date = 2026-04-21
author = "test"
status = "active"

[target]
lemma = "foo"
pos = "N"

[change]
field = "meaning"
to = "replaced;"

reason = "test"
""".strip()
    )

    _apply_overrides(entries, ovr_dir)

    foo = entries[0]
    assert foo["meaning"] == "replaced;"
    assert foo["_overrides"][0]["source"] == {"kind": "literal"}
    assert foo["_overrides"][0]["original_value"] == "original;"


def test_apply_overrides_skips_non_active(tmp_path: Path) -> None:
    """Overrides with status != "active" (reverted, superseded) must not
    affect entries."""
    entries = [_entry("foo", "N", "canonical;", id=1)]
    ovr_dir = tmp_path / "overrides"
    ovr_dir.mkdir()
    for status in ("reverted", "superseded"):
        (ovr_dir / f"OVR-{status}.toml").write_text(
            f"""
id = "OVR-{status}"
date = 2026-04-21
author = "test"
status = "{status}"

[target]
lemma = "foo"
pos = "N"

[change]
field = "meaning"
to = "should not be applied"

reason = "test"
""".strip()
        )

    _apply_overrides(entries, ovr_dir)

    assert entries[0]["meaning"] == "canonical;"
    assert "_overrides" not in entries[0]


def test_apply_overrides_missing_target_raises(tmp_path: Path) -> None:
    """An active override whose target doesn't exist must raise — silent
    no-op would make stale overrides invisible."""
    entries = [_entry("foo", "N", "x;", id=1)]
    ovr_dir = tmp_path / "overrides"
    ovr_dir.mkdir()
    (ovr_dir / "OVR-003-missing.toml").write_text(
        """
id = "OVR-003"
date = 2026-04-21
author = "test"
status = "active"

[target]
lemma = "does-not-exist"
pos = "N"

[change]
field = "meaning"
to = "x"

reason = "test"
""".strip()
    )
    with pytest.raises(ValueError, match="OVR-003"):
        _apply_overrides(entries, ovr_dir)


def test_apply_overrides_missing_dir_is_noop(tmp_path: Path) -> None:
    """If the overrides directory doesn't exist, build proceeds normally
    (for forks/repos that haven't adopted the layer yet)."""
    entries = [_entry("foo", "N", "x;", id=1)]
    missing = tmp_path / "does-not-exist"
    _apply_overrides(entries, missing)
    assert entries[0]["meaning"] == "x;"


# ---------------------------------------------------------------------------
# Integration — the exported lexicon.json carries OVR-001 for neque CONJ
# ---------------------------------------------------------------------------

LEXICON_JSON = Path(__file__).parent.parent / "data" / "json" / "lexicon.json"
skip_no_data = pytest.mark.skipif(
    not LEXICON_JSON.exists(),
    reason="lexicon.json not available (run: latincy-lexicon build)",
)


@pytest.fixture(scope="module")
def lexicon() -> dict:
    with open(LEXICON_JSON) as f:
        return json.load(f)


@skip_no_data
def test_ovr_001_neque_conj_in_lexicon(lexicon: dict) -> None:
    """After build, neque's CONJ entry carries the borrowed clean gloss
    and a provenance record pointing back to the canonical value."""
    entries = lexicon.get("neque") or []
    conj_entries = [e for e in entries if e.get("pos") == "CONJ"]
    assert conj_entries, "neque has no CONJ entry in lexicon"

    conj = conj_entries[0]
    glosses_text = " ".join(conj.get("glosses") or [])
    assert "neque..neque" not in glosses_text, (
        "neque CONJ still carries the polluted canonical gloss; "
        "OVR-001 was not applied"
    )
    assert "nor" in glosses_text.lower()

    ovrs = conj.get("_overrides") or []
    ovr_ids = [o.get("id") for o in ovrs]
    assert "OVR-001" in ovr_ids, (
        f"OVR-001 provenance missing from neque CONJ; got: {ovr_ids}"
    )
    ovr_001 = next(o for o in ovrs if o["id"] == "OVR-001")
    assert "neque..neque" in (ovr_001.get("original_value") or ""), (
        "OVR-001 should preserve the canonical value in original_value"
    )


@skip_no_data
def test_ovr_001_does_not_touch_neque_adv(lexicon: dict) -> None:
    """neque ADV is intentionally NOT part of OVR-001 — its canonical
    gloss is already clean. No provenance should be attached."""
    adv_entries = [e for e in lexicon.get("neque") or [] if e.get("pos") == "ADV"]
    assert adv_entries, "neque has no ADV entry in lexicon"
    for e in adv_entries:
        assert not e.get("_overrides"), (
            f"neque ADV should have no overrides, got: {e.get('_overrides')}"
        )
