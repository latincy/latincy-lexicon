"""Shared fixtures for latincy-lexicon tests."""

import pytest
from pathlib import Path


VENDOR_DIR = Path(__file__).parent.parent / "vendor" / "whitakers-words"
TRICKS_ADB = VENDOR_DIR / "src" / "words_engine" / "words_engine-trick_tables.adb"


def vendor_available() -> bool:
    return VENDOR_DIR.exists() and (VENDOR_DIR / "DICTLINE.GEN").exists()


skip_no_vendor = pytest.mark.skipif(
    not vendor_available(),
    reason="Vendor data not available (run: git clone https://github.com/mk270/whitakers-words vendor/whitakers-words)",
)
