"""Tests for the Lewis & Short TEI parser."""

from tests.conftest import LS_TEI, skip_no_ls
from latincy_lexicon.parsers.lewis_short import iter_lewis_short, parse_lewis_short


# A trimmed TEI fragment exercising: macron/breve orth, pos, itype, a homograph
# pair, nested senses, and inline markup that must be flattened out of `text`.
SAMPLE_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE TEI.2 PUBLIC "-//TEI P4//DTD Main DTD Driver File//EN" "tei2.dtd" []>
<TEI.2><text><body>
<entryFree key="ago" type="main" id="n1605"><orth lang="la" extent="full">ăgo</orth>, <itype>ēgi, actum, 3</itype>, <pos>v. a.</pos> <sense level="1" n="I" id="n1605.0">to <hi rend="ital">put in motion</hi>, to move</sense></entryFree>
<entryFree key="abactus1" type="main" id="n42"><orth lang="la">ăbactus</orth>, <pos>Part.</pos>, from abigo.</entryFree>
<entryFree key="abactus2" type="main" id="n43"><orth lang="la">ăbactūs</orth>, <itype>ūs</itype>, <gen>m.</gen> a driving away.</entryFree>
</body></text></TEI.2>
"""


def _by_id(entries):
    return {e.id: e for e in entries}


def test_iter_parses_all_entries():
    entries = list(iter_lewis_short(SAMPLE_TEI))
    assert len(entries) == 3
    assert {e.id for e in entries} == {"n1605", "n42", "n43"}


def test_field_extraction():
    e = _by_id(iter_lewis_short(SAMPLE_TEI))["n1605"]
    assert e.key == "ago"
    assert e.orth == "ăgo"
    assert e.pos == "v. a."
    assert e.itype == "ēgi, actum, 3"


def test_text_flattens_inline_markup():
    e = _by_id(iter_lewis_short(SAMPLE_TEI))["n1605"]
    # No tags survive; the italicized run is preserved as plain text.
    assert "<" not in e.text
    assert "put in motion" in e.text
    assert "to move" in e.text


def test_homograph_key_and_headword():
    by_id = _by_id(iter_lewis_short(SAMPLE_TEI))
    assert by_id["n42"].key == "abactus1"
    assert by_id["n43"].key == "abactus2"
    # The bare headword strips the homograph digit for joining.
    assert by_id["n42"].headword == "abactus"
    assert by_id["n43"].headword == "abactus"


def test_orth_carries_length_marks():
    # Macron/breve marks must survive — they disambiguate homographs downstream.
    by_id = _by_id(iter_lewis_short(SAMPLE_TEI))
    assert by_id["n43"].orth == "ăbactūs"


def test_gen_extracted_for_nouns():
    # L&S often marks a noun only by gender (empty <pos>); capture it.
    by_id = _by_id(iter_lewis_short(SAMPLE_TEI))
    assert by_id["n43"].gen == "m."
    assert by_id["n43"].pos == ""


@skip_no_ls
def test_real_file_entry_count():
    entries = parse_lewis_short(LS_TEI)
    assert len(entries) == 51636


@skip_no_ls
def test_real_file_ago():
    by_key = {e.key: e for e in parse_lewis_short(LS_TEI)}
    ago = by_key["ago"]
    assert ago.id == "n1605"
    assert ago.orth == "ăgo"
    assert ago.pos == "v. a."
    assert ago.itype.startswith("ēgi")
