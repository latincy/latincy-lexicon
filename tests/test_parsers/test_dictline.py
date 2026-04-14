"""Tests for DICTLINE parser."""

from tests.conftest import VENDOR_DIR, skip_no_vendor
from latincy_lexicon.parsers.dictline import parse_dictline


@skip_no_vendor
def test_parse_count():
    entries = parse_dictline(VENDOR_DIR / "DICTLINE.GEN")
    assert len(entries) > 39000


@skip_no_vendor
def test_first_entry():
    entries = parse_dictline(VENDOR_DIR / "DICTLINE.GEN")
    e = entries[0]
    assert e.stem1 == "A"
    assert e.pos == "N"


@skip_no_vendor
def test_verb_entry():
    entries = parse_dictline(VENDOR_DIR / "DICTLINE.GEN")
    amo = [e for e in entries if e.stem1 == "am" and e.pos == "V" and "love" in e.meaning]
    assert len(amo) >= 1
    assert amo[0].stem3 in ("amav", "amass")


@skip_no_vendor
def test_adj_entry():
    entries = parse_dictline(VENDOR_DIR / "DICTLINE.GEN")
    bonus = [e for e in entries if e.stem1 == "bon" and e.pos == "ADJ"]
    assert len(bonus) >= 1


@skip_no_vendor
def test_prep_entry():
    entries = parse_dictline(VENDOR_DIR / "DICTLINE.GEN")
    preps = [e for e in entries if e.pos == "PREP"]
    assert len(preps) > 50


@skip_no_vendor
def test_num_entry_no_x_prefix():
    """NUM entries must not have a stray ``X`` prefix in their gloss.

    Regression test for the bug where _parse_dictline didn't consume the
    NUM ``numeric_value`` field, causing the source code 'X' to bleed into
    the gloss as e.g. ``"X three;"`` instead of ``"three;"``.
    """
    entries = parse_dictline(VENDOR_DIR / "DICTLINE.GEN")
    nums = [e for e in entries if e.pos == "NUM"]
    assert len(nums) > 0
    leaks = [e for e in nums if e.meaning.startswith("X ")]
    assert not leaks, (
        f"NUM entries with leaked 'X ' gloss prefix: "
        f"{[(e.stem1, e.meaning[:30]) for e in leaks[:5]]}"
    )

    # Spot-check that ``tres`` parses cleanly
    tres = [e for e in nums if e.stem1 == "tr" and "three" in e.meaning]
    assert tres, "Expected to find 'tres' (NUM with stem 'tr' meaning 'three')"
    assert not tres[0].meaning.startswith("X "), (
        f"tres meaning leaked 'X' prefix: {tres[0].meaning!r}"
    )
