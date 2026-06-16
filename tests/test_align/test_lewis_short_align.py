"""Tests for lemma → Lewis & Short alignment (homograph disambiguation)."""

from latincy_lexicon.align.lewis_short import (
    ls_pos_classes,
    ww_pos_classes,
    rank_ls_candidates,
    align_lexicon_to_ls,
)


# Synthetic L&S store: a 3-way homograph cluster on "malus" plus a lone "ago".
STORE = {
    "n1": {"key": "malus1", "orth": "mălus", "pos": "adj.", "gen": "", "itype": ""},   # bad (adj)
    "n2": {"key": "malus2", "orth": "mālus", "pos": "", "gen": "f.", "itype": ""},      # apple-tree (noun)
    "n3": {"key": "malus3", "orth": "mālus", "pos": "", "gen": "m.", "itype": ""},      # mast (noun)
    "n9": {"key": "ago", "orth": "ăgo", "pos": "v. a.", "gen": "", "itype": ""},        # drive (verb)
}
INDEX = {"malus": ["n1", "n2", "n3"], "ago": ["n9"]}


def test_ls_pos_classes_from_pos():
    assert "verb" in ls_pos_classes(STORE["n9"])
    assert "adj" in ls_pos_classes(STORE["n1"])


def test_ls_pos_classes_noun_from_gen():
    # Empty <pos> but a gender → noun.
    assert ls_pos_classes(STORE["n2"]) == {"noun"}


def test_ww_pos_classes():
    assert ww_pos_classes("V") == {"verb"}
    assert ww_pos_classes("N") == {"noun"}
    assert "adj" in ww_pos_classes("VPAR")  # participle ↔ adjective/verb


def test_rank_prefers_matching_pos_verb():
    # A WW verb against the lone "ago" verb entry.
    assert rank_ls_candidates("V", ["n9"], STORE) == ["n9"]


def test_rank_disambiguates_adj_from_nouns():
    # WW adjective "malus" should rank the adj homograph first.
    ranked = rank_ls_candidates("ADJ", ["n1", "n2", "n3"], STORE)
    assert ranked[0] == "n1"
    # Nothing is dropped — all candidates remain available.
    assert set(ranked) == {"n1", "n2", "n3"}


def test_rank_disambiguates_noun_from_adj():
    # WW noun "malus" should rank a gendered noun homograph ahead of the adj.
    ranked = rank_ls_candidates("N", ["n1", "n2", "n3"], STORE)
    assert ranked[0] in {"n2", "n3"}
    assert ranked[-1] == "n1"  # the adjective sinks to last


def test_align_lexicon_attaches_ls_ids():
    lexicon = {
        "malus": [
            {"normalized_headword": "malus", "pos": "ADJ"},
            {"normalized_headword": "malus", "pos": "N"},
        ],
        "ago": [{"normalized_headword": "ago", "pos": "V"}],
    }
    out, stats = align_lexicon_to_ls(lexicon, INDEX, STORE)
    assert out["malus"][0]["ls_ids"][0] == "n1"   # adj entry → adj homograph first
    assert out["malus"][1]["ls_ids"][0] in {"n2", "n3"}  # noun entry → noun homograph
    assert out["ago"][0]["ls_ids"] == ["n9"]
    assert stats["entries_aligned"] == 3
    assert stats["entries_unmatched"] == 0


def test_align_records_unmatched():
    lexicon = {"nonexistentword": [{"normalized_headword": "nonexistentword", "pos": "N"}]}
    out, stats = align_lexicon_to_ls(lexicon, INDEX, STORE)
    assert out["nonexistentword"][0]["ls_ids"] == []
    assert stats["entries_unmatched"] == 1


def test_align_falls_back_to_assimilated_form():
    # WW headword "adcedo" misses; the assimilated "accedo" is in the L&S index.
    store = {"a1": {"key": "accedo", "orth": "accēdo", "pos": "v. n.", "gen": "", "itype": ""}}
    index = {"accedo": ["a1"]}
    lexicon = {"adcedo": [{"normalized_headword": "adcedo", "pos": "V"}]}
    out, stats = align_lexicon_to_ls(lexicon, index, store)
    assert out["adcedo"][0]["ls_ids"] == ["a1"]
    assert stats["entries_aligned"] == 1
    assert stats["entries_assimilated"] == 1


def test_align_prefers_direct_match_over_assimilation():
    # If the un-assimilated form itself is indexed, don't reach for a variant.
    store = {"d1": {"key": "adloquor", "orth": "adloquor", "pos": "v. dep.", "gen": "", "itype": ""}}
    index = {"adloquor": ["d1"]}
    lexicon = {"adloquor": [{"normalized_headword": "adloquor", "pos": "V"}]}
    out, stats = align_lexicon_to_ls(lexicon, index, store)
    assert out["adloquor"][0]["ls_ids"] == ["d1"]
    assert stats["entries_assimilated"] == 0
