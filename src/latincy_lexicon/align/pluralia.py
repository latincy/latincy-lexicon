"""Pluralia tantum handling.

Generates singular↔plural headword mappings for nouns that are
conventionally cited or lemmatized in their plural form (arma, castra,
moenia, divitiae, penates, etc.).

Uses INFLECTS table to correctly generate plural forms from stems,
rather than guessing endings.
"""

from __future__ import annotations

import sqlite3

from latincy_lexicon.align.normalize import normalize_latin


def build_plural_mappings(conn: sqlite3.Connection) -> dict[str, str]:
    """Build a mapping from singular normalized headword to plural form.

    Identifies nouns whose meaning contains "(pl.)" and generates the
    correct NOM PL form using the INFLECTS table.

    Returns:
        Dict mapping singular_normalized → plural_normalized.
    """
    rows = conn.execute(
        """SELECT d.id, d.stem1, d.stem2, d.gender, d.decl_which, d.decl_var,
                  h.normalized as singular
           FROM dict_entries d
           JOIN headwords h ON h.dict_entry_id = d.id
           WHERE d.pos = 'N'
           AND (d.meaning LIKE '%%(pl.)%%' OR d.meaning LIKE '%%(pl)%%')"""
    ).fetchall()

    mappings: dict[str, str] = {}

    for r in rows:
        singular = r["singular"]
        stem2 = r["stem2"] or r["stem1"]
        if not stem2 or stem2 == "zzz":
            stem2 = r["stem1"]

        # Find NOM PL ending from INFLECTS, matching gender
        gender = r["gender"]
        # Gender 'C' (common) matches any gender in inflections
        # Try exact gender match first, then fall back to common/wildcard
        ending_row = None
        if gender and gender not in ("C", "X"):
            ending_row = conn.execute(
                """SELECT ending FROM inflections
                   WHERE pos = 'N'
                   AND (decl_which = ? OR decl_which = 0)
                   AND (decl_var = ? OR decl_var = 0)
                   AND case_val = 'NOM' AND number = 'P'
                   AND stem_key = 2 AND gender = ?
                   AND freq IN ('A', 'B', 'C')
                   ORDER BY freq ASC LIMIT 1""",
                (r["decl_which"], r["decl_var"], gender),
            ).fetchone()

        if not ending_row:
            ending_row = conn.execute(
                """SELECT ending FROM inflections
                   WHERE pos = 'N'
                   AND (decl_which = ? OR decl_which = 0)
                   AND (decl_var = ? OR decl_var = 0)
                   AND case_val = 'NOM' AND number = 'P'
                   AND stem_key = 2
                   AND freq IN ('A', 'B', 'C')
                   ORDER BY freq ASC LIMIT 1""",
                (r["decl_which"], r["decl_var"]),
            ).fetchone()

        if ending_row:
            plural = normalize_latin(stem2 + ending_row["ending"])
            if plural != singular:
                mappings[singular] = plural

    return mappings


def apply_plural_mappings(
    mappings: dict[str, str],
    lexicon: dict[str, list[dict]],
) -> int:
    """Add plural-form keys to the lexicon for pluralia tantum nouns.

    If the lexicon has entries under the singular key (e.g., "armum"),
    also make them available under the plural key (e.g., "arma").

    Returns:
        Number of new keys added.
    """
    added = 0
    for singular, plural in mappings.items():
        if singular in lexicon and plural not in lexicon:
            lexicon[plural] = lexicon[singular]
            added += 1
    return added
