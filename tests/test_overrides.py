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


def test_apply_overrides_multi_change(tmp_path: Path) -> None:
    """An override with an array-of-tables `[[change]]` applies every field
    change as one attributable record (e.g. backfilling both stem3 and stem4
    of a truncated stub), recording one provenance entry per change."""
    entries = [
        _entry("intellig", "V", "understand;", id=1,
               decl_which=3, decl_var=1, stem2="intellig", stem3="zzz", stem4="zzz"),
        _entry("intelleg", "V", "understand;", id=2,
               decl_which=3, decl_var=1, stem2="intelleg",
               stem3="intellex", stem4="intellect"),
    ]
    ovr_dir = tmp_path / "overrides"
    ovr_dir.mkdir()
    (ovr_dir / "OVR-003-multi.toml").write_text(
        """
id = "OVR-003"
date = 2026-07-11
author = "test"
status = "active"

[target]
lemma = "intellig"
pos = "V"
decl_which = 3
decl_var = 1

[[change]]
field = "stem3"
borrow_from = { lemma = "intelleg", pos = "V", decl_which = 3, decl_var = 1, field = "stem3" }

[[change]]
field = "stem4"
borrow_from = { lemma = "intelleg", pos = "V", decl_which = 3, decl_var = 1, field = "stem4" }

reason = "test"
reason_short = "test"
""".strip()
    )

    _apply_overrides(entries, ovr_dir)

    stub = next(e for e in entries if e["stem1"] == "intellig")
    assert stub["stem3"] == "intellex"
    assert stub["stem4"] == "intellect"
    ovrs = stub["_overrides"]
    assert [o["field"] for o in ovrs] == ["stem3", "stem4"]
    assert all(o["id"] == "OVR-003" for o in ovrs)
    assert ovrs[0]["original_value"] == "zzz"
    # source entry untouched
    src = next(e for e in entries if e["stem1"] == "intelleg")
    assert "_overrides" not in src


def test_apply_overrides_homograph_disambiguation(tmp_path: Path) -> None:
    """`decl_which`/`decl_var` in the target pick one of several homographs
    sharing (stem1, pos); without them `_find_entry` returns the first."""
    entries = [
        _entry("pari", "V", "acquire;", id=1, decl_which=1, decl_var=1, freq="D"),
        _entry("pari", "V", "give birth;", id=2, decl_which=3, decl_var=1, freq="A"),
    ]
    ovr_dir = tmp_path / "overrides"
    ovr_dir.mkdir()
    (ovr_dir / "OVR-x.toml").write_text(
        """
id = "OVR-X"
date = 2026-07-11
author = "test"
status = "active"

[target]
lemma = "pari"
pos = "V"
decl_which = 3
decl_var = 1

[change]
field = "freq"
to = "B"

reason = "test"
""".strip()
    )

    _apply_overrides(entries, ovr_dir)

    denominal = next(e for e in entries if e["decl_which"] == 1)
    give_birth = next(e for e in entries if e["decl_which"] == 3)
    assert give_birth["freq"] == "B"          # targeted homograph changed
    assert denominal["freq"] == "D"           # other homograph untouched
    assert "_overrides" not in denominal


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


def test_apply_overrides_gender_literal(tmp_path: Path) -> None:
    """OVR-002 pattern: literal replacement of a non-meaning field (gender)."""
    entries = [_entry("nepos", "N", "grandson;", id=1, gender="C")]
    ovr_dir = tmp_path / "overrides"
    ovr_dir.mkdir()
    (ovr_dir / "OVR-002-nepos-noun-gender.toml").write_text(
        """
id = "OVR-002"
date = 2026-06-22
author = "test"
status = "active"

[target]
lemma = "nepos"
pos = "N"

[change]
field = "gender"
to = "M"

reason = "WW marks nepos as C; L&S/OLD give m. only."
reason_short = "WW marks nepos as C (common), but L&S/OLD both give m. only."
""".strip()
    )

    _apply_overrides(entries, ovr_dir)

    nepos = entries[0]
    assert nepos["gender"] == "M"
    ovrs = nepos.get("_overrides") or []
    assert len(ovrs) == 1
    ovr = ovrs[0]
    assert ovr["id"] == "OVR-002"
    assert ovr["field"] == "gender"
    assert ovr["original_value"] == "C"
    assert ovr["source"] == {"kind": "literal"}


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


@skip_no_data
def test_ovr_002_nepos_noun_gender_in_lexicon(lexicon: dict) -> None:
    """After build, nepos N entry has gender=M (not C) and carries OVR-002 provenance."""
    entries = lexicon.get("nepos") or []
    noun_entries = [e for e in entries if e.get("pos") == "N"]
    assert noun_entries, "nepos has no N entry in lexicon"

    noun = noun_entries[0]
    assert noun.get("gender") == "M", (
        f"nepos N gender should be M after OVR-002; got {noun.get('gender')!r}"
    )

    ovrs = noun.get("_overrides") or []
    ovr_ids = [o.get("id") for o in ovrs]
    assert "OVR-002" in ovr_ids, (
        f"OVR-002 provenance missing from nepos N; got: {ovr_ids}"
    )
    ovr_002 = next(o for o in ovrs if o["id"] == "OVR-002")
    assert ovr_002.get("original_value") == "C", (
        "OVR-002 should record original WW value C in original_value"
    )


# ---------------------------------------------------------------------------
# Integration — OVR-003 against a fresh build (not the gitignored local export)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def built_lexicon(tmp_path_factory) -> dict:
    from latincy_lexicon.build import build

    out = tmp_path_factory.mktemp("lex")
    build(output_dir=out)
    return json.loads((out / "lexicon.json").read_text())


def test_ovr_003_intelligo_principal_parts(built_lexicon: dict) -> None:
    """The i-spelling `intelligo` stub gets its perfect + supine stems
    backfilled from canonical `intellego`, so its citation is the complete
    `intelligo, intelligere, intellexi, intellectum` — carrying OVR-003
    provenance on both stem fields — while `intellego` is untouched."""
    from latincy_lexicon.principal_parts import format_principal_parts

    entries = [e for e in built_lexicon.get("intelligo", []) if e.get("pos") == "V"]
    assert entries, "intelligo verb entry missing from lexicon"
    e = entries[0]
    assert e["principal_parts"] == ["intellig", "intellig", "intellex", "intellect"]
    assert format_principal_parts(e) == "intelligo, intelligere, intellexi, intellectum"

    ovr_fields = [o["field"] for o in e.get("_overrides", []) if o["id"] == "OVR-003"]
    assert set(ovr_fields) == {"stem3", "stem4"}, (
        f"expected OVR-003 provenance on stem3+stem4, got {ovr_fields}"
    )

    # Canonical e-spelling entry is the borrow source, not a target.
    intellego = [e for e in built_lexicon.get("intellego", []) if e.get("pos") == "V"]
    assert intellego and not intellego[0].get("_overrides")
