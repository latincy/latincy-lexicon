"""Perseus L&S TEI → structured sense-tree parser (``parsers/lewis_short_senses``).

Flat ``<sense>`` siblings whose hierarchy lives in ``level``/``n`` attributes are
reconstructed into a tree; purely-syntactic subdivisions (Greek-letter construction
variants ``(a)(b)(g)(d)`` and bare grammatical glosses like ``inf.``/``dat.``) are
collapsed; sense IRIs are minted and Perseus xml:id + CTS citations kept. Tested
against the REAL narro entry fixture and the real TEI (pater depth regression).
"""

import re
from pathlib import Path

import pytest

from latincy_lexicon.parsers.lewis_short_senses import (
    is_construction,
    lila_entry_iri,
    parse_entry,
    perseus_entry_url,
    sense_depth,
    sense_tree_orphans,
)

from tests.conftest import LS_TEI, skip_no_ls

NARRO = (Path(__file__).parent.parent / "fixtures" / "ls-narro.xml").read_text(
    encoding="utf-8"
)


def test_repeated_sibling_labels_merge_not_duplicate():
    # L&S splits one sense across repeated <sense n="I"> siblings (deduco pattern):
    # a marker head-note, then the real meaning. They must merge to ONE "I".
    xml = (
        '<entryFree id="nX" key="x"><orth>x</orth>'
        '<sense level="1" n="I"><hi rend="ital">imper.</hi></sense>'
        '<sense level="1" n="I"><hi rend="ital">to draw off, lead off</hi></sense>'
        '<sense level="3" n="2"><hi rend="ital">to lead forth</hi></sense>'
        "</entryFree>"
    )
    senses = parse_entry(xml, "x")
    levels = [s["level"] for s in senses]
    assert levels.count("I") == 1                       # merged, not duplicated
    one_I = next(s for s in senses if s["level"] == "I")
    assert one_I["display_gloss"] == "to draw off, lead off"  # substantive wins over "imper."


def test_display_gloss_inherits_meaning_for_marker_leaves():
    # a leaf whose own gloss is only prepositions/markers shows the parent meaning.
    xml = (
        '<entryFree id="nY" key="y"><orth>y</orth>'
        '<sense level="1" n="II"><hi rend="ital">To depart from</hi></sense>'
        '<sense level="2" n="A"></sense>'
        '<sense level="3" n="1"><hi rend="ital">ab, ex</hi><hi rend="ital">absol.</hi></sense>'
        "</entryFree>"
    )
    leaf = next(s for s in parse_entry(xml, "y") if s["level"] == "II.A.1")
    assert leaf["gloss"] == "ab, ex"                     # raw lead italic unchanged
    assert leaf["display_gloss"] == "To depart from"     # inherited from II


def test_sense_depth_from_label_class_overrides_buggy_tei_level():
    # pater's F/G/H carry level=1 in the TEI but are capital-letter children of II.
    assert sense_depth("F", 1) == 2   # capital letter → depth 2, not the TEI's 1
    assert sense_depth("II", 1) == 1  # multi-char Roman → 1
    assert sense_depth("A", 2) == 2
    assert sense_depth("2", 3) == 3   # arabic → 3
    assert sense_depth("a", 4) == 4   # lowercase → 4
    assert sense_depth("C", 2) == 2   # ambiguous (Roman C / capital C) → trust TEI level
    assert sense_depth("I", 1) == 1   # ambiguous I at top → trust TEI level
    assert sense_depth("A. 1.", 1) == 2  # appello's mangled label → first token A → 2


def test_orphaned_capital_senses_nest_under_their_roman_parent():
    # Reproduces the pater bug: F (level=1 in TEI) must become II.F, not a root F.
    xml = (
        '<entryFree id="nX" key="x"><orth>x</orth>'
        '<sense level="1" n="I"><hi rend="ital">first sense</hi></sense>'
        '<sense level="1" n="II"><hi rend="ital">second</hi></sense>'
        '<sense level="2" n="A"><hi rend="ital">alpha</hi></sense>'
        '<sense level="2" n="E"><hi rend="ital">epsilon</hi></sense>'
        '<sense level="1" n="F"><hi rend="ital">the host</hi></sense>'
        '<sense level="1" n="G"><hi rend="ital">sire</hi></sense>'
        "</entryFree>"
    )
    levels = {s["gloss"]: s["level"] for s in parse_entry(xml, "x")}
    assert levels["the host"] == "II.F"   # was "F" before the fix
    assert levels["sire"] == "II.G"
    assert levels["alpha"] == "II.A"


def test_parse_narro_extracts_real_meaning_senses():
    glosses = [s["gloss"] for s in parse_entry(NARRO, "narro")]
    assert "to tell, relate, narrate, report, recount, set forth" in glosses
    assert "to say, speak, tell" in glosses
    assert "to dedicate" in glosses


def test_parse_narro_collapses_syntactic_inf_node():
    # the n='I' node whose gloss is just 'inf.' is a construction split → dropped
    glosses = [s["gloss"].strip().rstrip(".").lower() for s in parse_entry(NARRO, "narro")]
    assert "inf" not in glosses


def test_parse_narro_mints_sense_iri_with_level_and_perseus_id():
    senses = parse_entry(NARRO, "narro")
    first = senses[0]
    assert first["id"] == "https://w3id.org/latincy/lemma/narro/sense/I"
    assert first["level"] == "I"
    assert first["sameAs"]["perseus_ls_id"] == "n30406.0"
    # the 'to dedicate' sub-sense nests under II
    dedicate = next(s for s in senses if s["gloss"] == "to dedicate")
    assert dedicate["level"] == "II.B"
    assert dedicate["id"] == "https://w3id.org/latincy/lemma/narro/sense/II.B"


def test_parse_narro_captures_cts_citations_as_evidence():
    sense_ii = next(s for s in parse_entry(NARRO, "narro") if s["level"] == "II")
    assert sense_ii["citations"]
    assert all(c.startswith("urn:cts:") for c in sense_ii["citations"])


def test_perseus_entry_url_is_a_real_hopper_url():
    assert perseus_entry_url("narro") == (
        "https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0059:entry=narro"
    )
    assert perseus_entry_url("dico1").endswith("entry=dico1")  # homograph keeps its digit


def test_lila_entry_iri_is_the_resolving_ls_sense_node():
    # SPARQL-verified scheme: per-SENSE nodes live at …/id/LexicalSense/{full id},
    # keeping the full Perseus id (incl. the ".k" suffix). Offline: string only.
    assert lila_entry_iri("n30406.0") == (
        "http://lila-erc.eu/data/lexicalResources/LewisShort/id/LexicalSense/n30406.0"
    )
    assert lila_entry_iri("n44548.1") == (
        "http://lila-erc.eu/data/lexicalResources/LewisShort/id/LexicalSense/n44548.1"
    )
    assert lila_entry_iri("") is None


def test_parse_entry_stamps_perseus_and_resolving_lila_sameas():
    senses = parse_entry(NARRO, "narro", perseus_url=perseus_entry_url("narro"))
    s = senses[0]
    assert s["sameAs"]["perseus"].endswith("entry=narro")     # resolvable L&S entry
    assert s["sameAs"]["perseus_ls_id"] == "n30406.0"          # stable L&S node id
    assert s["sameAs"]["lila"] == (                           # resolving LiLa L&S sense node
        "http://lila-erc.eu/data/lexicalResources/LewisShort/id/LexicalSense/n30406.0"
    )


def test_is_construction_rule():
    assert is_construction("(a)", "dat.")           # Greek-letter construction variant
    assert is_construction("I", "inf.")             # bare grammatical marker
    assert is_construction("I", "pres.")            # positional/tense marker (leaked before)
    assert is_construction("II.A", "fin.")          # "in fin." citation-position marker
    assert not is_construction("II", "to say, speak, tell")  # real meaning
    assert not is_construction("I", "")             # empty structural node is NOT construction
    assert not is_construction("I", "esp. of the mind")  # semantic qualifier, kept


_PATER_RE = re.compile(r'<entryFree\b[^>]*\bkey="pater[^"]*".*?</entryFree>', re.DOTALL)


@skip_no_ls
def test_real_pater_sense_tree_has_no_orphans():
    """Depth regression on the real TEI: pater's F/G/H must nest under II, not strand
    at the root. Guards the exact bug ``sense_depth`` was written to fix."""
    text = LS_TEI.read_text(encoding="utf-8")
    blocks = _PATER_RE.findall(text)
    assert blocks, "no pater entryFree found in the L&S TEI"
    for block in blocks:
        senses = parse_entry(block, "pater")
        orphans = sense_tree_orphans([s["level"] for s in senses])
        assert not orphans, f"orphaned senses (depth bug) in pater: {orphans}"
