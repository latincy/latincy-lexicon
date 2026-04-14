"""Tests for ADDONS parser."""

from tests.conftest import VENDOR_DIR, skip_no_vendor
from latincy_lexicon.parsers.addons import parse_addons


@skip_no_vendor
def test_parse_count():
    entries = parse_addons(VENDOR_DIR / "ADDONS.LAT")
    assert len(entries) > 300


@skip_no_vendor
def test_prefix_entries():
    entries = parse_addons(VENDOR_DIR / "ADDONS.LAT")
    prefixes = [e for e in entries if e.addon_type == "PREFIX"]
    assert len(prefixes) > 100
    # Common prefixes
    prefix_names = {e.fix for e in prefixes}
    assert "ab" in prefix_names
    assert "ad" in prefix_names


@skip_no_vendor
def test_tackon_entries():
    entries = parse_addons(VENDOR_DIR / "ADDONS.LAT")
    tackons = [e for e in entries if e.addon_type == "TACKON"]
    assert len(tackons) > 5
    tackon_names = {e.fix for e in tackons}
    assert "que" in tackon_names
    assert "ne" in tackon_names


@skip_no_vendor
def test_suffix_entries():
    entries = parse_addons(VENDOR_DIR / "ADDONS.LAT")
    suffixes = [e for e in entries if e.addon_type == "SUFFIX"]
    assert len(suffixes) > 100


@skip_no_vendor
def test_packon_entries():
    entries = parse_addons(VENDOR_DIR / "ADDONS.LAT")
    packons = [e for e in entries if e.addon_type == "PACKON"]
    assert len(packons) >= 6
