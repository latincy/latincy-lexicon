"""Shared fixtures for latincy-lexicon tests."""

import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def _isolate_lexicon_cache(tmp_path, monkeypatch):
    """Point the build_lexicon disk cache at a throwaway dir.

    Keeps tests from reading or polluting the real user cache (and from leaking
    cache state between tests)."""
    monkeypatch.setenv("LATINCY_LEXICON_CACHE_DIR", str(tmp_path / "lexicon-cache"))


VENDOR_DIR = Path(__file__).parent.parent / "vendor" / "whitakers-words"
TRICKS_ADB = VENDOR_DIR / "src" / "words_engine" / "words_engine-trick_tables.adb"


def vendor_available() -> bool:
    return VENDOR_DIR.exists() and (VENDOR_DIR / "DICTLINE.GEN").exists()


skip_no_vendor = pytest.mark.skipif(
    not vendor_available(),
    reason="Vendor data not available (run: git clone https://github.com/mk270/whitakers-words vendor/whitakers-words)",
)


LS_TEI = (
    Path(__file__).parent.parent
    / "data" / "raw" / "lewis-short" / "lat.ls.perseus-eng2.xml"
)

skip_no_ls = pytest.mark.skipif(
    not LS_TEI.exists(),
    reason="Lewis & Short TEI not available (data/raw/lewis-short/lat.ls.perseus-eng2.xml)",
)
