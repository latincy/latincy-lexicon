"""Tests for database queries."""

from latincy_lexicon.db.schema import create_db
from latincy_lexicon.db.loader import load_dict_entries, load_inflections, load_headwords
from latincy_lexicon.db.queries import (
    lookup_by_headword, lookup_by_lemma, search_meaning, get_table_counts,
)
from latincy_lexicon.enums import PartOfSpeech, Frequency
from latincy_lexicon.models import DictEntry, Inflection


def _setup_db():
    conn = create_db()
    entries = [
        DictEntry(stem1="am", stem2="am", stem3="amav", stem4="amat",
                  pos=PartOfSpeech.V, decl_which=1, decl_var=1,
                  freq=Frequency.A, meaning="love, like; fall in love with"),
        DictEntry(stem1="bell", stem2="bell", stem3="", stem4="",
                  pos=PartOfSpeech.N, decl_which=2, decl_var=1,
                  freq=Frequency.B, meaning="war"),
    ]
    load_dict_entries(conn, entries)
    load_headwords(conn, [
        ("amo", "amo", 1),
        ("bellum", "bellum", 2),
    ])
    return conn


def test_lookup_by_headword():
    conn = _setup_db()
    results = lookup_by_headword(conn, "amo")
    assert len(results) == 1
    assert "love" in results[0]["meaning"]
    conn.close()


def test_lookup_by_lemma():
    conn = _setup_db()
    results = lookup_by_lemma(conn, "amo")
    assert len(results) == 1
    conn.close()


def test_search_meaning():
    conn = _setup_db()
    results = search_meaning(conn, "love")
    assert len(results) >= 1
    assert any("love" in r["meaning"] for r in results)
    conn.close()


def test_table_counts():
    conn = _setup_db()
    counts = get_table_counts(conn)
    assert counts["dict_entries"] == 2
    assert counts["headwords"] == 2
    conn.close()
