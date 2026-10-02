"""Tests for the Lewis & Short sense-store builder."""

import json

from latincy_lexicon.export.lewis_short import build_lewis_short_senses
from tests.test_parsers.test_lewis_short import SAMPLE_TEI


def _build(tmp_path, lemmas=None):
    tei = tmp_path / "ls.xml"
    tei.write_text(SAMPLE_TEI, encoding="utf-8")
    stats = build_lewis_short_senses(tei, tmp_path, lemmas=lemmas)
    store = json.loads(
        (tmp_path / "lewis_short_senses.json").read_text(encoding="utf-8")
    )
    assert store.pop("_meta")["license"] == "CC-BY-SA-4.0"  # provenance header
    return stats, store


def test_store_keyed_by_id_with_slug_and_senses(tmp_path):
    # Only n1605 (ago) carries a <sense>; the two abactus entries have none.
    stats, store = _build(tmp_path)
    assert stats == {"entries": 1, "senses": 1}
    assert set(store) == {"n1605"}
    assert store["n1605"]["key"] == "ago"
    assert store["n1605"]["slug"] == "ago"


def test_sense_shape_matches_parser(tmp_path):
    _, store = _build(tmp_path)
    sense = store["n1605"]["senses"][0]
    assert sense["level"] == "I"
    assert sense["id"] == "https://w3id.org/latincy/lemma/ago/sense/I"
    assert sense["gloss"] == "put in motion"
    assert sense["sameAs"]["perseus_ls_id"] == "n1605.0"
    assert sense["sameAs"]["perseus"].endswith("entry=ago")


def test_store_carries_citation_records_and_entry_citations(tmp_path):
    _, store = _build(tmp_path)
    entry = store["n1605"]
    assert entry["entry_citations"] == []                    # ago fixture has no <etym> bibl
    sense = entry["senses"][0]
    assert sense["citation_records"] == []                   # and no citations in its sense
    assert sense["citations"] == []


HOMOGRAPH_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI.2><text><body>
<entryFree key="cum1" type="main" id="n11"><orth lang="la">cum</orth>, <pos>prep.</pos> <sense level="1" n="I" id="n11.0"><hi rend="ital">with</hi></sense></entryFree>
<entryFree key="Cum2" type="main" id="n12"><orth lang="la">cum</orth>, <pos>conj.</pos> <sense level="1" n="I" id="n12.0"><hi rend="ital">when</hi></sense><sense level="1" n="II" id="n12.1"><hi rend="ital">since</hi></sense></entryFree>
<entryFree key="ago" type="main" id="n1605"><orth lang="la" extent="full">ăgo</orth>, <pos>v. a.</pos> <sense level="1" n="I" id="n1605.0">to <hi rend="ital">put in motion</hi></sense></entryFree>
</body></text></TEI.2>
"""


def test_homograph_entries_mint_distinct_iris(tmp_path):
    tei = tmp_path / "ls.xml"
    tei.write_text(HOMOGRAPH_TEI, encoding="utf-8")
    build_lewis_short_senses(tei, tmp_path)
    store = json.loads((tmp_path / "lewis_short_senses.json").read_text(encoding="utf-8"))
    assert store["n11"]["slug"] == store["n12"]["slug"] == "cum"
    assert (store["n11"]["iri_slug"], store["n12"]["iri_slug"]) == ("cum1", "cum2")
    ids = [s["id"] for e in ("n11", "n12") for s in store[e]["senses"]]
    assert ids == [
        "https://w3id.org/latincy/lemma/cum1/sense/I",
        "https://w3id.org/latincy/lemma/cum2/sense/I",
        "https://w3id.org/latincy/lemma/cum2/sense/II",
    ]
    # a single-entry slug keeps its bare IRI
    assert store["n1605"]["iri_slug"] == "ago"
    assert store["n1605"]["senses"][0]["id"] == "https://w3id.org/latincy/lemma/ago/sense/I"


def test_lemmas_filter_scopes_the_store(tmp_path):
    # Restricting to a slug that isn't present yields an empty store.
    stats, store = _build(tmp_path, lemmas={"nonexistent"})
    assert stats == {"entries": 0, "senses": 0}
    assert store == {}
