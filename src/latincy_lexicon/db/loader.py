"""Bulk loader for parsed Whitaker's Words data into SQLite."""

from __future__ import annotations

import sqlite3

from latincy_lexicon.models import Addon, DictEntry, Inflection, Trick, Unique


def load_dict_entries(conn: sqlite3.Connection, entries: list[DictEntry]) -> None:
    """Bulk insert DictEntry objects."""
    conn.executemany(
        """INSERT INTO dict_entries
           (stem1, stem2, stem3, stem4, pos, decl_which, decl_var,
            gender, noun_kind, verb_kind, pronoun_kind, comparison, numeral_sort,
            age, area, geo, freq, source, meaning, line_number)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (
                e.stem1, e.stem2, e.stem3, e.stem4,
                str(e.pos), e.decl_which, e.decl_var,
                str(e.gender) if e.gender else None,
                str(e.noun_kind) if e.noun_kind else None,
                str(e.verb_kind) if e.verb_kind else None,
                str(e.pronoun_kind) if e.pronoun_kind else None,
                str(e.comparison) if e.comparison else None,
                str(e.numeral_sort) if e.numeral_sort else None,
                str(e.age), str(e.area), str(e.geo),
                str(e.freq), str(e.source),
                e.meaning, e.line_number,
            )
            for e in entries
        ],
    )
    conn.commit()


def load_inflections(conn: sqlite3.Connection, entries: list[Inflection]) -> None:
    """Bulk insert Inflection objects."""
    conn.executemany(
        """INSERT INTO inflections
           (pos, decl_which, decl_var, case_val, number, gender,
            tense, voice, mood, person, comparison, numeral_sort,
            stem_key, ending, age, freq, line_number)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (
                str(e.pos), e.decl_which, e.decl_var,
                e.case, e.number, e.gender,
                e.tense, e.voice, e.mood, e.person,
                e.comparison, e.numeral_sort,
                e.stem_key, e.ending,
                str(e.age), str(e.freq), e.line_number,
            )
            for e in entries
        ],
    )
    conn.commit()


def load_addons(conn: sqlite3.Connection, entries: list[Addon]) -> None:
    """Bulk insert Addon objects."""
    conn.executemany(
        """INSERT INTO addons
           (addon_type, fix, connect, from_pos, to_pos, meaning, line_number)
           VALUES (?,?,?,?,?,?,?)""",
        [
            (
                str(e.addon_type), e.fix, e.connect,
                str(e.from_pos), str(e.to_pos),
                e.meaning, e.line_number,
            )
            for e in entries
        ],
    )
    conn.commit()


def load_uniques(conn: sqlite3.Connection, entries: list[Unique]) -> None:
    """Bulk insert Unique objects."""
    conn.executemany(
        """INSERT INTO uniques
           (form, pos, decl_which, decl_var, case_val, number, gender,
            tense, voice, mood, person, comparison,
            stem1, stem2, stem3, stem4, meaning, line_number)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (
                e.form, str(e.pos), e.decl_which, e.decl_var,
                e.case, e.number, e.gender,
                e.tense, e.voice, e.mood, e.person, e.comparison,
                e.stem1, e.stem2, e.stem3, e.stem4,
                e.meaning, e.line_number,
            )
            for e in entries
        ],
    )
    conn.commit()


def load_tricks(conn: sqlite3.Connection, entries: list[Trick]) -> None:
    """Bulk insert Trick objects."""
    conn.executemany(
        """INSERT INTO tricks (trick_class, from_text, to_text, explanation)
           VALUES (?,?,?,?)""",
        [
            (str(e.trick_class), e.from_text, e.to_text, e.explanation)
            for e in entries
        ],
    )
    conn.commit()


def load_headwords(
    conn: sqlite3.Connection,
    headwords: list[tuple[str, str, int]],
) -> None:
    """Bulk insert headword records.

    Args:
        conn: Database connection.
        headwords: List of (headword, normalized, dict_entry_id) tuples.
    """
    conn.executemany(
        "INSERT INTO headwords (headword, normalized, dict_entry_id) VALUES (?,?,?)",
        headwords,
    )
    conn.commit()
