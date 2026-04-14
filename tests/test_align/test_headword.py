"""Tests for headword reconstruction and alignment."""

from latincy_lexicon.db.schema import create_db
from latincy_lexicon.db.loader import load_dict_entries, load_inflections
from latincy_lexicon.align.headword import build_headwords
from latincy_lexicon.enums import PartOfSpeech, Gender, NounKind, Frequency
from latincy_lexicon.models import DictEntry, Inflection


def test_build_headwords():
    conn = create_db()

    # Add a noun entry and inflection
    entries = [
        DictEntry(stem1="aqu", stem2="aqu", stem3="", stem4="",
                  pos=PartOfSpeech.N, decl_which=1, decl_var=1,
                  gender=Gender.F, noun_kind=NounKind.T,
                  meaning="water"),
    ]
    load_dict_entries(conn, entries)

    inflections = [
        Inflection(pos=PartOfSpeech.N, decl_which=1, decl_var=1,
                   case="NOM", number="S", gender="C",
                   stem_key=1, ending="a", freq=Frequency.A),
    ]
    load_inflections(conn, inflections)

    count = build_headwords(conn)
    assert count == 1

    row = conn.execute("SELECT * FROM headwords").fetchone()
    assert row["headword"] == "aqua"
    assert row["normalized"] == "aqua"
    conn.close()


def test_build_verb_headword():
    conn = create_db()

    entries = [
        DictEntry(stem1="am", stem2="am", stem3="amav", stem4="amat",
                  pos=PartOfSpeech.V, decl_which=1, decl_var=1,
                  meaning="love"),
    ]
    load_dict_entries(conn, entries)

    inflections = [
        Inflection(pos=PartOfSpeech.V, decl_which=1, decl_var=1,
                   tense="PRES", voice="ACTIVE", mood="IND",
                   person="1", number="S",
                   stem_key=1, ending="o", freq=Frequency.A),
    ]
    load_inflections(conn, inflections)

    count = build_headwords(conn)
    assert count == 1

    row = conn.execute("SELECT * FROM headwords").fetchone()
    assert row["headword"] == "amo"
    conn.close()
