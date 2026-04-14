"""Query functions for the Whitaker's Words database."""

from __future__ import annotations

import sqlite3


def lookup_by_headword(conn: sqlite3.Connection, headword: str) -> list[dict]:
    """Look up dictionary entries by headword.

    Returns list of dict_entries rows joined with headword info.
    """
    rows = conn.execute(
        """SELECT d.*, h.headword, h.normalized
           FROM dict_entries d
           JOIN headwords h ON h.dict_entry_id = d.id
           WHERE h.headword = ? OR h.normalized = ?""",
        (headword, headword),
    ).fetchall()
    return [dict(r) for r in rows]


def lookup_by_lemma(conn: sqlite3.Connection, lemma: str) -> list[dict]:
    """Look up dictionary entries by normalized headword (LatinCy lemma).

    Tries normalized headword first, falls back to raw headword.
    """
    rows = conn.execute(
        """SELECT d.*, h.headword, h.normalized
           FROM dict_entries d
           JOIN headwords h ON h.dict_entry_id = d.id
           WHERE h.normalized = ?""",
        (lemma,),
    ).fetchall()
    if rows:
        return [dict(r) for r in rows]

    # Fallback: try raw headword match
    rows = conn.execute(
        """SELECT d.*, h.headword, h.normalized
           FROM dict_entries d
           JOIN headwords h ON h.dict_entry_id = d.id
           WHERE h.headword = ?""",
        (lemma,),
    ).fetchall()
    return [dict(r) for r in rows]


def search_meaning(conn: sqlite3.Connection, query: str) -> list[dict]:
    """Search dictionary entries by meaning substring."""
    rows = conn.execute(
        """SELECT d.*, h.headword, h.normalized
           FROM dict_entries d
           LEFT JOIN headwords h ON h.dict_entry_id = d.id
           WHERE d.meaning LIKE ?
           LIMIT 100""",
        (f"%{query}%",),
    ).fetchall()
    return [dict(r) for r in rows]


def get_inflections_for(
    conn: sqlite3.Connection,
    pos: str,
    decl_which: int,
    decl_var: int,
) -> list[dict]:
    """Get inflection endings for a given POS and declension/conjugation."""
    rows = conn.execute(
        """SELECT * FROM inflections
           WHERE pos = ? AND (decl_which = ? OR decl_which = 0)
           AND (decl_var = ? OR decl_var = 0)
           ORDER BY stem_key, ending""",
        (pos, decl_which, decl_var),
    ).fetchall()
    return [dict(r) for r in rows]


def get_addons_by_type(conn: sqlite3.Connection, addon_type: str) -> list[dict]:
    """Get all addons of a given type."""
    rows = conn.execute(
        "SELECT * FROM addons WHERE addon_type = ?",
        (addon_type,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_unique_form(conn: sqlite3.Connection, form: str) -> list[dict]:
    """Look up a unique/irregular form."""
    rows = conn.execute(
        "SELECT * FROM uniques WHERE form = ?",
        (form,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Get row counts for all tables."""
    tables = [
        "dict_entries", "headwords", "inflections",
        "addons", "uniques", "tricks", "alignment",
    ]
    counts = {}
    for table in tables:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        counts[table] = row[0]
    return counts
