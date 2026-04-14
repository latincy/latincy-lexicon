"""Tests for TRICKS parser."""

from tests.conftest import TRICKS_ADB, skip_no_vendor
from latincy_lexicon.parsers.tricks import parse_tricks


@skip_no_vendor
def test_parse_count():
    tricks = parse_tricks(TRICKS_ADB)
    assert len(tricks) > 100


@skip_no_vendor
def test_trick_classes():
    tricks = parse_tricks(TRICKS_ADB)
    classes = {t.trick_class for t in tricks}
    assert "ANY" in classes
    assert "MEDIAEVAL" in classes
    assert "SLUR" in classes


@skip_no_vendor
def test_any_tricks():
    tricks = parse_tricks(TRICKS_ADB)
    any_tricks = [t for t in tricks if t.trick_class == "ANY"]
    assert len(any_tricks) > 50


@skip_no_vendor
def test_mediaeval_tricks():
    tricks = parse_tricks(TRICKS_ADB)
    med = [t for t in tricks if t.trick_class == "MEDIAEVAL"]
    assert len(med) > 20
