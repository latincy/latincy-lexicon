"""Tests for database schema."""

from latincy_lexicon.db.schema import create_db


def test_create_in_memory():
    conn = create_db()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {r["name"] for r in tables}
    assert "dict_entries" in table_names
    assert "headwords" in table_names
    assert "inflections" in table_names
    assert "addons" in table_names
    assert "uniques" in table_names
    assert "tricks" in table_names
    assert "alignment" in table_names
    conn.close()


def test_indexes_exist():
    conn = create_db()
    indexes = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    ).fetchall()
    idx_names = {r["name"] for r in indexes}
    assert "idx_dict_entries_stem1" in idx_names
    assert "idx_headwords_normalized" in idx_names
    assert "idx_inflections_ending" in idx_names
    conn.close()
