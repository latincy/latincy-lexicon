"""SQLite schema for Whitaker's Words database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS dict_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stem1 TEXT NOT NULL DEFAULT '',
    stem2 TEXT NOT NULL DEFAULT '',
    stem3 TEXT NOT NULL DEFAULT '',
    stem4 TEXT NOT NULL DEFAULT '',
    pos TEXT NOT NULL,
    decl_which INTEGER NOT NULL DEFAULT 0,
    decl_var INTEGER NOT NULL DEFAULT 0,
    gender TEXT,
    noun_kind TEXT,
    verb_kind TEXT,
    pronoun_kind TEXT,
    comparison TEXT,
    numeral_sort TEXT,
    age TEXT NOT NULL DEFAULT 'X',
    area TEXT NOT NULL DEFAULT 'X',
    geo TEXT NOT NULL DEFAULT 'X',
    freq TEXT NOT NULL DEFAULT 'X',
    source TEXT NOT NULL DEFAULT 'X',
    meaning TEXT NOT NULL DEFAULT '',
    line_number INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS headwords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headword TEXT NOT NULL,
    normalized TEXT NOT NULL,
    dict_entry_id INTEGER NOT NULL,
    FOREIGN KEY (dict_entry_id) REFERENCES dict_entries(id)
);

CREATE TABLE IF NOT EXISTS inflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pos TEXT NOT NULL,
    decl_which INTEGER NOT NULL DEFAULT 0,
    decl_var INTEGER NOT NULL DEFAULT 0,
    case_val TEXT NOT NULL DEFAULT 'X',
    number TEXT NOT NULL DEFAULT 'X',
    gender TEXT NOT NULL DEFAULT 'X',
    tense TEXT NOT NULL DEFAULT 'X',
    voice TEXT NOT NULL DEFAULT 'X',
    mood TEXT NOT NULL DEFAULT 'X',
    person TEXT NOT NULL DEFAULT '0',
    comparison TEXT NOT NULL DEFAULT 'X',
    numeral_sort TEXT NOT NULL DEFAULT 'X',
    stem_key INTEGER NOT NULL DEFAULT 0,
    ending TEXT NOT NULL DEFAULT '',
    age TEXT NOT NULL DEFAULT 'X',
    freq TEXT NOT NULL DEFAULT 'X',
    line_number INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS addons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    addon_type TEXT NOT NULL,
    fix TEXT NOT NULL,
    connect TEXT NOT NULL DEFAULT '',
    from_pos TEXT NOT NULL DEFAULT 'X',
    to_pos TEXT NOT NULL DEFAULT 'X',
    meaning TEXT NOT NULL DEFAULT '',
    line_number INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS uniques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    form TEXT NOT NULL,
    pos TEXT NOT NULL DEFAULT 'X',
    decl_which INTEGER NOT NULL DEFAULT 0,
    decl_var INTEGER NOT NULL DEFAULT 0,
    case_val TEXT NOT NULL DEFAULT 'X',
    number TEXT NOT NULL DEFAULT 'X',
    gender TEXT NOT NULL DEFAULT 'X',
    tense TEXT NOT NULL DEFAULT 'X',
    voice TEXT NOT NULL DEFAULT 'X',
    mood TEXT NOT NULL DEFAULT 'X',
    person TEXT NOT NULL DEFAULT '0',
    comparison TEXT NOT NULL DEFAULT 'X',
    stem1 TEXT NOT NULL DEFAULT '',
    stem2 TEXT NOT NULL DEFAULT '',
    stem3 TEXT NOT NULL DEFAULT '',
    stem4 TEXT NOT NULL DEFAULT '',
    meaning TEXT NOT NULL DEFAULT '',
    line_number INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tricks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trick_class TEXT NOT NULL,
    from_text TEXT NOT NULL,
    to_text TEXT NOT NULL DEFAULT '',
    explanation TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS alignment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    words_headword TEXT NOT NULL,
    latincy_lemma TEXT NOT NULL,
    match_type TEXT NOT NULL DEFAULT 'exact',
    confidence REAL NOT NULL DEFAULT 1.0,
    dict_entry_id INTEGER,
    FOREIGN KEY (dict_entry_id) REFERENCES dict_entries(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dict_entries_pos ON dict_entries(pos);
CREATE INDEX IF NOT EXISTS idx_dict_entries_stem1 ON dict_entries(stem1);
CREATE INDEX IF NOT EXISTS idx_headwords_headword ON headwords(headword);
CREATE INDEX IF NOT EXISTS idx_headwords_normalized ON headwords(normalized);
CREATE INDEX IF NOT EXISTS idx_headwords_entry ON headwords(dict_entry_id);
CREATE INDEX IF NOT EXISTS idx_inflections_pos ON inflections(pos, decl_which, decl_var);
CREATE INDEX IF NOT EXISTS idx_inflections_ending ON inflections(ending);
CREATE INDEX IF NOT EXISTS idx_addons_type ON addons(addon_type);
CREATE INDEX IF NOT EXISTS idx_addons_fix ON addons(fix);
CREATE INDEX IF NOT EXISTS idx_uniques_form ON uniques(form);
CREATE INDEX IF NOT EXISTS idx_alignment_headword ON alignment(words_headword);
CREATE INDEX IF NOT EXISTS idx_alignment_lemma ON alignment(latincy_lemma);
"""


def create_db(path: str | Path | None = None) -> sqlite3.Connection:
    """Create a new database with the full schema.

    Args:
        path: File path for the database, or None for in-memory.

    Returns:
        sqlite3.Connection with schema applied.
    """
    db_path = str(path) if path else ":memory:"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn
