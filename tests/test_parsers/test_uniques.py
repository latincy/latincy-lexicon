"""Tests for UNIQUES parser."""

from tests.conftest import VENDOR_DIR, skip_no_vendor
from latincy_lexicon.parsers.uniques import parse_uniques


@skip_no_vendor
def test_parse_count():
    entries = parse_uniques(VENDOR_DIR / "UNIQUES.LAT")
    assert len(entries) > 50


@skip_no_vendor
def test_sample_entries():
    entries = parse_uniques(VENDOR_DIR / "UNIQUES.LAT")
    forms = {e.form for e in entries}
    assert "memento" in forms or "aforem" in forms
