"""Tests for database loader."""

from latincy_lexicon.db.schema import create_db
from latincy_lexicon.db.loader import (
    load_dict_entries, load_inflections, load_addons,
    load_uniques, load_tricks, load_headwords,
)
from latincy_lexicon.enums import *
from latincy_lexicon.models import DictEntry, Inflection, Addon, Unique, Trick


def test_load_dict_entries():
    conn = create_db()
    entries = [
        DictEntry(stem1="am", stem2="am", stem3="amav", stem4="amat",
                  pos=PartOfSpeech.V, decl_which=1, decl_var=1,
                  verb_kind=VerbKind.TRANS, freq=Frequency.A,
                  meaning="love"),
    ]
    load_dict_entries(conn, entries)
    row = conn.execute("SELECT * FROM dict_entries WHERE stem1 = 'am'").fetchone()
    assert row is not None
    assert row["meaning"] == "love"
    conn.close()


def test_load_inflections():
    conn = create_db()
    entries = [
        Inflection(pos=PartOfSpeech.N, decl_which=1, decl_var=1,
                   case="NOM", number="S", gender="F",
                   stem_key=1, ending="a"),
    ]
    load_inflections(conn, entries)
    row = conn.execute("SELECT * FROM inflections WHERE ending = 'a'").fetchone()
    assert row is not None
    conn.close()


def test_load_addons():
    conn = create_db()
    entries = [
        Addon(addon_type=AddonType.PREFIX, fix="ab", meaning="away from"),
    ]
    load_addons(conn, entries)
    row = conn.execute("SELECT * FROM addons WHERE fix = 'ab'").fetchone()
    assert row is not None
    assert row["meaning"] == "away from"
    conn.close()


def test_load_headwords():
    conn = create_db()
    entries = [
        DictEntry(stem1="am", stem2="am", stem3="amav", stem4="amat",
                  pos=PartOfSpeech.V, decl_which=1, decl_var=1,
                  meaning="love"),
    ]
    load_dict_entries(conn, entries)
    load_headwords(conn, [("amo", "amo", 1)])
    row = conn.execute("SELECT * FROM headwords WHERE headword = 'amo'").fetchone()
    assert row is not None
    assert row["normalized"] == "amo"
    conn.close()
