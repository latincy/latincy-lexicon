"""Perseus L&S TEI → structured sense-tree parser (``parsers/lewis_short_senses``).

Flat ``<sense>`` siblings whose hierarchy lives in ``level``/``n`` attributes are
reconstructed into a tree; purely-syntactic subdivisions (Greek-letter construction
variants ``(a)(b)(g)(d)`` and bare grammatical glosses like ``inf.``/``dat.``) are
collapsed; sense IRIs are minted and Perseus xml:id + CTS citations kept. Tested
against the REAL narro entry fixture and the real TEI (pater depth regression).
"""

import re
from pathlib import Path

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


def test_parse_narro_second_I_merges_with_its_citations():
    # narro's second <sense n="I"> (the "Lit." sense with ~38 citations) used to be
    # collapsed as a construction because its first italic ANYWHERE was "inf." (from
    # "With acc. and inf.", after four examples). It is a top-level sense and must
    # merge into I, bringing its citations along.
    senses = parse_entry(NARRO, "narro")
    glosses = [s["gloss"].strip().rstrip(".").lower() for s in senses]
    assert "inf" not in glosses
    one_I = next(s for s in senses if s["level"] == "I")
    assert len(one_I["citations"]) >= 30
    assert "urn:cts:latinLit:phi0474.phi056.perseus-lat1:9:6:6" in one_I["citations"]
    assert one_I["display_gloss"].startswith("to tell, relate")


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
    assert is_construction("I", "inf.")             # bare grammatical marker (depth unknown)
    assert is_construction("I", "pres.")            # positional/tense marker (leaked before)
    assert is_construction("II.A", "fin.")          # "in fin." citation-position marker
    assert not is_construction("II", "to say, speak, tell")  # real meaning
    assert not is_construction("I", "")             # empty structural node is NOT construction
    assert not is_construction("I", "esp. of the mind")  # semantic qualifier, kept
    # a top-level sense is a major division of meaning whatever its head-note says
    assert not is_construction("I", "inf.", depth=1)
    assert not is_construction("II", "absol.", depth=1)
    assert is_construction("1", "inf.", depth=3)


def test_top_level_sense_with_marker_headnote_is_kept_with_its_citations():
    # accedo / acies pattern: "I. perf. sync., accēstis, Verg. A. 1, 201), to go..."
    xml = (
        '<entryFree id="nA" key="accedo"><orth>accedo</orth>'
        '<sense level="1" n="I" id="nA.0"><hi rend="ital">perf. sync.</hi>, accestis, '
        '<bibl n="urn:cts:latinLit:phi0690.phi003.perseus-lat2:1:201"><author>Verg.</author> A. 1, 201</bibl>), '
        '<hi rend="ital">to go or come to</hi>, to approach</sense>'
        '<sense level="2" n="A" id="nA.1"><hi rend="ital">of persons</hi>: '
        '<cit><quote lang="la">accedere ad urbem</quote> '
        '<bibl n="urn:cts:latinLit:phi0474.phi013.perseus-lat1:1:5"><author>Cic.</author> Cat. 1, 5</bibl></cit></sense>'
        "</entryFree>"
    )
    senses = parse_entry(xml, "accedo")
    levels = {s["level"]: s for s in senses}
    assert set(levels) == {"I", "I.A"}                     # I kept, A nests under it
    assert levels["I"]["display_gloss"] == "to go or come to"
    assert levels["I"]["citations"] == ["urn:cts:latinLit:phi0690.phi003.perseus-lat2:1:201"]


def test_marker_italic_after_a_citation_is_not_the_lead_gloss():
    # the lead gloss is the first italic BEFORE the citation apparatus; "inf." after
    # an example (narro pattern) and "fin." inside a <bibl> never collapse a sense.
    xml = (
        '<entryFree id="nB" key="b"><orth>b</orth>'
        '<sense level="1" n="I" id="nB.0"><hi rend="ital">to run</hi></sense>'
        '<sense level="3" n="1" id="nB.1"> Lit.: <cit><quote lang="la">currere per vias</quote> '
        '<bibl n="urn:cts:latinLit:phi0914.phi001:1:2:3"><author>Liv.</author> 1, 2, 3 <hi rend="ital">fin.</hi></bibl></cit>'
        '; with <hi rend="ital">inf.</hi>: <cit><quote lang="la">currere videre</quote> '
        '<bibl n="urn:cts:latinLit:phi0914.phi001:4:5:6"><author>id.</author> 4, 5, 6</bibl></cit></sense>'
        "</entryFree>"
    )
    senses = parse_entry(xml, "b")
    sub = next(s for s in senses if s["level"] == "I.1")
    assert sub["gloss"] == ""                                # no lead italic before the first <cit>
    assert len(sub["citations"]) == 2


def test_construction_subsense_citations_reparent_to_parent():
    # absimilis pattern: I, then Greek-letter (a)/(b) construction variants with the
    # only citations. They fold into I; the records remember the construction label.
    xml = (
        '<entryFree id="nC" key="absimilis"><orth>absimilis</orth>'
        '<sense level="1" n="I" id="nC.0"><hi rend="ital">unlike</hi></sense>'
        '<sense level="5" n="(a)" id="nC.1"><hi rend="ital">Absol.</hi>: '
        '<cit><quote lang="la">falces non absimili forma</quote> '
        '<bibl n="urn:cts:latinLit:phi0448.phi001.perseus-lat1:3:14:5"><author>Caes.</author> B. G. 3, 14, 5</bibl></cit></sense>'
        '<sense level="5" n="(b)" id="nC.2"> With <hi rend="ital">dat.</hi>: '
        '<bibl n="urn:cts:latinLit:phi0978.phi001:8:121"><author>Plin.</author> 8, 33, 51, § 121</bibl></sense>'
        "</entryFree>"
    )
    senses = parse_entry(xml, "absimilis")
    assert [s["level"] for s in senses] == ["I"]
    one = senses[0]
    assert one["citations"] == [
        "urn:cts:latinLit:phi0448.phi001.perseus-lat1:3:14:5",
        "urn:cts:latinLit:phi0978.phi001:8:121",
    ]
    labels = [r["construction_label"] for r in one["citation_records"]]
    assert labels == ["(a)", "(b)"]
    quoted = one["citation_records"][0]
    assert quoted["has_quote"] and quoted["quote"] == "falces non absimili forma"
    assert quoted["n_words"] == 4 and quoted["in_cit"] and quoted["urn_source"] == "perseus"
    bare = one["citation_records"][1]
    assert not bare["has_quote"] and bare["n_words"] == 0 and not bare["in_cit"]


def test_construction_at_top_of_entry_is_kept_not_orphaned():
    # nothing kept yet → a would-be construction cannot fold into a parent; keep it.
    xml = (
        '<entryFree id="nD" key="d"><orth>d</orth>'
        '<sense level="5" n="(a)" id="nD.0"><hi rend="ital">Absol.</hi>: '
        '<bibl n="urn:cts:latinLit:phi0474.phi013:1:5"><author>Cic.</author> Cat. 1, 5</bibl></sense>'
        "</entryFree>"
    )
    senses = parse_entry(xml, "d")
    assert len(senses) == 1 and senses[0]["citations"] == ["urn:cts:latinLit:phi0474.phi013:1:5"]


def test_ib_anaphora_fills_work_from_the_preceding_bibl():
    xml = (
        '<entryFree id="nE" key="e"><orth>e</orth>'
        '<sense level="1" n="I" id="nE.0"><hi rend="ital">to say</hi>: '
        '<cit><quote lang="la">alpha beta gamma</quote> '
        '<bibl n="urn:cts:latinLit:phi0474.phi056.perseus-lat1:6:1:6"><author>Cic.</author> Fam. 6, 1, 6</bibl></cit>: '
        '<cit><quote lang="la">delta epsilon zeta</quote> <bibl><author>id.</author> ib. 2, 10, 3</bibl></cit>; '
        '<bibl n="urn:cts:latinLit:phi0978.phi001:6:84"><author>Plin.</author> 6, 22, 24, § 84</bibl>: '
        '<cit><quote lang="la">eta theta iota</quote> <bibl><author>id.</author> ib. 7, 45, 46, § 150</bibl></cit>; '
        '<bibl><author>id.</author> 20 praef.</bibl></sense>'
        "</entryFree>"
    )
    recs = parse_entry(xml, "e")[0]["citation_records"]
    assert [r["urn_source"] for r in recs] == [
        "perseus", "anaphora_fill", "perseus", "anaphora_fill", "anaphora_author"
    ]
    assert recs[1]["urn"] == "urn:cts:latinLit:phi0474.phi056.perseus-lat1:2:10:3"
    assert recs[3]["urn"] == "urn:cts:latinLit:phi0978.phi001:7:150"   # book + § section
    assert recs[4]["urn"] == "urn:cts:latinLit:phi0978"                 # author only
    assert [r["anaphoric"] for r in recs] == [False, True, False, True, True]
    assert [r["ordinal"] for r in recs] == [1, 2, 3, 4, 5]


def test_anaphora_after_an_unresolved_bibl_stays_unresolved():
    # abdicatio: "Cod. Just. 6, 31, 6" has no URN, so the following "ib." must not
    # skip back to an earlier citation.
    xml = (
        '<entryFree id="nF" key="abdicatio"><orth>abdicatio</orth>'
        '<sense level="1" n="I" id="nF.0"><hi rend="ital">a renouncing</hi>: '
        '<bibl n="urn:cts:latinLit:phi1002.phi001:7:4:27"><author>Quint.</author> 7, 4, 27</bibl>; '
        '<cit><quote lang="la">hereditatis,</quote> <bibl><author>Cod. Just.</author> 6, 31, 6</bibl></cit>: '
        '<cit><quote lang="la">liberorum,</quote> <bibl><author>ib.</author> 6, 8, 47</bibl></cit></sense>'
        "</entryFree>"
    )
    recs = parse_entry(xml, "abdicatio")[0]["citation_records"]
    assert recs[1]["urn"] is None and recs[1]["urn_source"] is None and not recs[1]["anaphoric"]
    assert recs[2]["urn"] is None and recs[2]["anaphoric"]
    assert recs[2]["n_words"] == 1                       # "liberorum," is a one-word clip


def test_entry_level_citations_are_returned_separately():
    from latincy_lexicon.parsers.lewis_short_senses import parse_entry_full

    senses, entry_cits = parse_entry_full(NARRO, "narro")
    assert [c["location"] for c in entry_cits] == ["etym"]
    assert entry_cits[0]["urn"] == "urn:cts:latinLit:phi1236.phi001"   # Fest. p. 95
    assert entry_cits[0]["ordinal"] == 1
    assert all(entry_cits[0]["urn"] not in s["citations"] for s in senses)


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
