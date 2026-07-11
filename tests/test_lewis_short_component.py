"""The lewis_short spaCy component attaches ranked L&S entries to tokens.

Runtime lookup: given a token's lemma, it consults lewis_short_index.json
(and the lazily-loaded store) and ranks homographs by the token's POS.
"""

from __future__ import annotations

import json

import pytest

spacy = pytest.importorskip("spacy")


# A 3-way "malus" homograph cluster + lone "ago", written to tmp JSON files.
_STORE = {
    "n1": {"key": "malus1", "orth": "mălus", "pos": "adj.", "gen": "", "itype": "", "text": "bad"},
    "n2": {"key": "malus2", "orth": "mālus", "pos": "", "gen": "f.", "itype": "", "text": "apple-tree"},
    "n3": {"key": "malus3", "orth": "mālus", "pos": "", "gen": "m.", "itype": "", "text": "mast"},
    "n9": {"key": "ago", "orth": "ăgo", "pos": "v. a.", "gen": "", "itype": "", "text": "drive"},
}
_INDEX = {"malus": ["n1", "n2", "n3"], "ago": ["n9"], "accedo": ["n5"]}
_STORE["n5"] = {"key": "accedo", "orth": "accēdo", "pos": "v. n.", "gen": "", "itype": "", "text": "approach"}


@pytest.fixture(scope="module")
def _paths(tmp_path_factory):
    out = tmp_path_factory.mktemp("ls")
    (out / "lewis_short_index.json").write_text(json.dumps(_INDEX), encoding="utf-8")
    (out / "lewis_short.json").write_text(json.dumps(_STORE), encoding="utf-8")
    return str(out / "lewis_short_index.json"), str(out / "lewis_short.json")


@pytest.fixture(scope="module")
def nlp(_paths):
    idx, store = _paths
    nlp = spacy.blank("la")
    nlp.add_pipe(
        "lewis_short",
        config={"ls_index_path": idx, "ls_store_path": store},
    )
    return nlp


@pytest.fixture(scope="module")
def nlp_full(_paths):
    idx, store = _paths
    nlp = spacy.blank("la")
    nlp.add_pipe(
        "lewis_short",
        config={"ls_index_path": idx, "ls_store_path": store, "include_text": True},
    )
    return nlp


def _run(nlp, text, lemma, pos):
    doc = nlp.make_doc(text)
    doc[0].lemma_ = lemma
    doc[0].pos_ = pos
    return nlp.get_pipe("lewis_short")(doc)[0]


def test_single_candidate(nlp):
    tok = _run(nlp, "agit", "ago", "VERB")
    entries = tok._.lewis_short
    assert [e["id"] for e in entries] == ["n9"]
    assert entries[0]["key"] == "ago"


def test_default_payload_is_lean(nlp):
    # Default: a light handle — metadata but NOT the (large) entry text.
    tok = _run(nlp, "agit", "ago", "VERB")
    handle = tok._.lewis_short[0]
    assert handle["id"] == "n9"
    assert handle["orth"] == "ăgo"
    assert handle["pos"] == "v. a."
    assert "text" not in handle


def test_include_text_inlines_full_entry(nlp_full):
    # Opt-in: the full entry text is inlined on the token.
    tok = _run(nlp_full, "agit", "ago", "VERB")
    handle = tok._.lewis_short[0]
    assert handle["text"] == "drive"
    assert handle["orth"] == "ăgo"


def test_get_entry_fetches_full_text_on_demand(nlp):
    # Even with lean handles, the full entry is retrievable by id.
    tok = _run(nlp, "agit", "ago", "VERB")
    cid = tok._.lewis_short[0]["id"]
    entry = nlp.get_pipe("lewis_short").get_entry(cid)
    assert entry["text"] == "drive"
    assert entry["key"] == "ago"
    assert nlp.get_pipe("lewis_short").get_entry("nope") is None


def test_homograph_ranked_by_pos_verb_vs_noun(nlp):
    # A noun reading of "malus" ranks a gendered noun homograph first.
    tok = _run(nlp, "malus", "malus", "NOUN")
    ids = [e["id"] for e in tok._.lewis_short]
    assert ids[0] in {"n2", "n3"}
    assert ids[-1] == "n1"  # adjective sinks
    assert set(ids) == {"n1", "n2", "n3"}  # nothing dropped


def test_homograph_ranked_by_pos_adj(nlp):
    tok = _run(nlp, "malus", "malus", "ADJ")
    assert tok._.lewis_short[0]["id"] == "n1"


def test_no_match_leaves_none(nlp):
    tok = _run(nlp, "xyzzy", "xyzzy", "NOUN")
    assert tok._.lewis_short is None


def test_include_text_survives_byte_roundtrip(_paths):
    idx, store = _paths
    nlp = spacy.blank("la")
    nlp.add_pipe(
        "lewis_short",
        config={"ls_index_path": idx, "ls_store_path": store, "include_text": True},
    )
    data = nlp.get_pipe("lewis_short").to_bytes()

    fresh = spacy.blank("la")
    pipe = fresh.add_pipe("lewis_short")  # defaults include_text=False
    pipe.from_bytes(data)
    assert pipe._include_text is True


def test_resolves_unassimilated_lemma_via_assimilation(nlp):
    # WW-style un-assimilated lemma "adcedo" should reach L&S "accedo".
    tok = _run(nlp, "adcedit", "adcedo", "VERB")
    entries = tok._.lewis_short
    assert [e["id"] for e in entries] == ["n5"]
    assert entries[0]["key"] == "accedo"


def test_falls_back_to_surface_when_no_lemma(nlp):
    # Even without an upstream lemmatizer, the surface form is normalized + used.
    doc = nlp.make_doc("ago")
    # blank pipeline: lemma_ is unset; component should fall back to text.
    tok = nlp.get_pipe("lewis_short")(doc)[0]
    assert tok._.lewis_short is not None
    assert tok._.lewis_short[0]["key"] == "ago"


# --- sense store (.get_senses) ------------------------------------------------

_SENSES = {
    "n9": {
        "key": "ago",
        "slug": "ago",
        "senses": [
            {
                "id": "https://w3id.org/latincy/lemma/ago/sense/I",
                "level": "I",
                "n": "I",
                "gloss": "to put in motion",
                "display_gloss": "to put in motion",
                "sameAs": {"perseus_ls_id": "n9.0", "perseus": None, "lila": None},
                "citations": [],
                "citation_tr": {},
            }
        ],
    }
}


@pytest.fixture(scope="module")
def nlp_senses(_paths, tmp_path_factory):
    idx, store = _paths
    senses = tmp_path_factory.mktemp("ls_senses") / "lewis_short_senses.json"
    senses.write_text(json.dumps(_SENSES), encoding="utf-8")
    nlp = spacy.blank("la")
    nlp.add_pipe(
        "lewis_short",
        config={"ls_index_path": idx, "ls_store_path": store, "ls_senses_path": str(senses)},
    )
    return nlp


def test_get_senses_returns_sense_list(nlp_senses):
    senses = nlp_senses.get_pipe("lewis_short").get_senses("n9")
    assert [s["level"] for s in senses] == ["I"]
    assert senses[0]["id"] == "https://w3id.org/latincy/lemma/ago/sense/I"
    assert senses[0]["sameAs"]["perseus_ls_id"] == "n9.0"


def test_get_senses_empty_for_unknown_id(nlp_senses):
    assert nlp_senses.get_pipe("lewis_short").get_senses("nope") == []


def test_get_senses_does_not_inflate_token_handles(nlp_senses):
    # Sense store is opt-in via get_senses; per-token handles stay lean.
    tok = _run(nlp_senses, "agit", "ago", "VERB")
    assert "senses" not in tok._.lewis_short[0]


def test_senses_path_survives_byte_roundtrip(_paths, tmp_path_factory):
    idx, store = _paths
    senses = tmp_path_factory.mktemp("ls_senses_rt") / "lewis_short_senses.json"
    senses.write_text(json.dumps(_SENSES), encoding="utf-8")
    nlp = spacy.blank("la")
    nlp.add_pipe(
        "lewis_short",
        config={"ls_index_path": idx, "ls_store_path": store, "ls_senses_path": str(senses)},
    )
    data = nlp.get_pipe("lewis_short").to_bytes()

    fresh = spacy.blank("la")
    pipe = fresh.add_pipe("lewis_short")
    pipe.from_bytes(data)
    assert pipe.get_senses("n9")[0]["level"] == "I"


# --- tier-1 sense attachment (attach_senses) ----------------------------------


@pytest.fixture(scope="module")
def nlp_attach(_paths, tmp_path_factory):
    idx, store = _paths
    senses = tmp_path_factory.mktemp("ls_attach") / "lewis_short_senses.json"
    senses.write_text(json.dumps(_SENSES), encoding="utf-8")
    nlp = spacy.blank("la")
    nlp.add_pipe(
        "lewis_short",
        config={"ls_index_path": idx, "ls_store_path": store,
                "ls_senses_path": str(senses), "attach_senses": True},
    )
    return nlp


def test_attach_senses_populates_lean_sense_list(nlp_attach):
    tok = _run(nlp_attach, "agit", "ago", "VERB")
    senses = tok._.lewis_short_senses
    assert senses == [{"level": "I", "n": "I", "display_gloss": "to put in motion"}]
    # Lean: raw gloss, citations, sameAs, id stay behind get_senses().
    assert all(
        set(s) <= {"level", "n", "display_gloss"} for s in senses
    )


def test_attach_senses_uses_top_ranked_entry_only(nlp_attach):
    # "malus" has three homograph entries but none carry senses in the
    # fixture store, so the attachment is an empty list — crucially from
    # the top-ranked id, not a merge across homographs.
    tok = _run(nlp_attach, "malus", "malus", "ADJ")
    assert tok._.lewis_short_senses == []


def test_attach_senses_default_off_leaves_extension_none(nlp_senses):
    tok = _run(nlp_senses, "agit", "ago", "VERB")
    assert tok._.lewis_short_senses is None


def test_attach_senses_default_off_skips_sense_store_load(nlp_senses):
    # Without attach_senses, running the component must not pay the (48 MB
    # in production) sense-store load.
    pipe = nlp_senses.get_pipe("lewis_short")
    assert pipe._attach_senses is False


def test_attach_senses_survives_byte_roundtrip(_paths, tmp_path_factory):
    idx, store = _paths
    senses = tmp_path_factory.mktemp("ls_attach_rt") / "lewis_short_senses.json"
    senses.write_text(json.dumps(_SENSES), encoding="utf-8")
    nlp = spacy.blank("la")
    nlp.add_pipe(
        "lewis_short",
        config={"ls_index_path": idx, "ls_store_path": store,
                "ls_senses_path": str(senses), "attach_senses": True},
    )
    data = nlp.get_pipe("lewis_short").to_bytes()

    fresh = spacy.blank("la")
    pipe = fresh.add_pipe("lewis_short")  # defaults attach_senses=False
    pipe.from_bytes(data)
    assert pipe._attach_senses is True
