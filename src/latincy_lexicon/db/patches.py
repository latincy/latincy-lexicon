"""Post-build patches for known gaps in Whitaker's Words data files.

The original Ada program hardcodes certain entries (notably sum/esse)
that are not present in DICTLINE.GEN. This module adds them to the
database after the standard data load.
"""

from __future__ import annotations

import sqlite3


def apply_all_patches(conn: sqlite3.Connection) -> dict[str, int]:
    """Apply all patches. Returns counts of items added."""
    stats: dict[str, int] = {}
    stats["sum_entry"] = _patch_sum_esse(conn)
    stats["sum_inflections"] = _patch_sum_inflections(conn)
    stats["pron_inflections"] = _patch_pronoun_inflections(conn)
    conn.commit()
    return stats


def _patch_sum_esse(conn: sqlite3.Connection) -> int:
    """Add sum/esse (to be) — hardcoded in original Ada, missing from DICTLINE.

    The original Words program handles sum through a lookup table in
    words_engine-parse.adb:Is_Sum(). We add it as a regular dict entry
    so the stem-based analyzer can find it.

    Stems follow the compound pattern (cf. absum: abs/ab/abfu/abfut):
      sum: s / (empty) / fu / fut   V 5.1 TO_BE
    """
    # Check if already patched
    existing = conn.execute(
        "SELECT id FROM dict_entries WHERE pos='V' AND decl_which=5 AND decl_var=1 "
        "AND meaning LIKE 'be; exist%'"
    ).fetchone()
    if existing:
        return 0

    meaning = (
        "be; exist; (also used to form verb perfect passive tenses) "
        "with compound forms (adsum, absum, possum, prosum, etc.);"
    )
    conn.execute(
        """INSERT INTO dict_entries
           (stem1, stem2, stem3, stem4, pos, decl_which, decl_var,
            verb_kind, age, area, geo, freq, source, meaning)
           VALUES ('s', '', 'fu', 'fut', 'V', 5, 1,
                   'TO_BE', 'X', 'X', 'X', 'A', 'X', ?)""",
        (meaning,),
    )
    entry_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Add headword
    conn.execute(
        "INSERT INTO headwords (headword, normalized, dict_entry_id) VALUES (?, ?, ?)",
        ("sum", "sum", entry_id),
    )

    return 1


def _patch_sum_inflections(conn: sqlite3.Connection) -> int:
    """Add missing V 5.1 inflections for present/imperfect/future indicative
    and present subjunctive.

    The existing INFLECTS.LAT has V 5.1 entries for:
    - stem2: esse (INF), es/este/esto/estote (IMP), essem..essent (IMPF SUB),
             forem..forent (IMPF SUB alt)
    - stem1: unto (FUT IMP 3P)

    Missing: all present indicative, imperfect indicative, future indicative,
    and present subjunctive forms. Perfect/pluperfect/future perfect are
    handled by wildcard V 0.0 inflections with stem3.

    These inflections also serve compound verbs (absum, adsum, possum, etc.).
    """
    # Check if already patched (look for a distinctive entry)
    existing = conn.execute(
        "SELECT id FROM inflections WHERE pos='V' AND decl_which=5 AND decl_var=1 "
        "AND tense='PRES' AND mood='IND' AND person='1' AND number='S'"
    ).fetchone()
    if existing:
        return 0

    # Inflections derived from words_engine-parse.adb:Is_Sum()
    # Format: (stem_key, ending, tense, voice, mood, person, number)
    new_inflections = [
        # Present indicative
        (1, "um",    "PRES", "ACTIVE", "IND", "1", "S"),
        (2, "es",    "PRES", "ACTIVE", "IND", "2", "S"),
        (2, "est",   "PRES", "ACTIVE", "IND", "3", "S"),
        (1, "umus",  "PRES", "ACTIVE", "IND", "1", "P"),
        (2, "estis", "PRES", "ACTIVE", "IND", "2", "P"),
        (1, "unt",   "PRES", "ACTIVE", "IND", "3", "P"),

        # Imperfect indicative (stem2-based: eram, eras, erat...)
        (2, "eram",   "IMPF", "ACTIVE", "IND", "1", "S"),
        (2, "eras",   "IMPF", "ACTIVE", "IND", "2", "S"),
        (2, "erat",   "IMPF", "ACTIVE", "IND", "3", "S"),
        (2, "eramus", "IMPF", "ACTIVE", "IND", "1", "P"),
        (2, "eratis", "IMPF", "ACTIVE", "IND", "2", "P"),
        (2, "erant",  "IMPF", "ACTIVE", "IND", "3", "P"),

        # Future indicative (stem2-based: ero, eris, erit...)
        (2, "ero",    "FUT", "ACTIVE", "IND", "1", "S"),
        (2, "eris",   "FUT", "ACTIVE", "IND", "2", "S"),
        (2, "erit",   "FUT", "ACTIVE", "IND", "3", "S"),
        (2, "erimus", "FUT", "ACTIVE", "IND", "1", "P"),
        (2, "eritis", "FUT", "ACTIVE", "IND", "2", "P"),
        (2, "erunt",  "FUT", "ACTIVE", "IND", "3", "P"),

        # Present subjunctive (stem1-based: sim, sis, sit...)
        (1, "im",   "PRES", "ACTIVE", "SUB", "1", "S"),
        (1, "is",   "PRES", "ACTIVE", "SUB", "2", "S"),
        (1, "it",   "PRES", "ACTIVE", "SUB", "3", "S"),
        (1, "imus", "PRES", "ACTIVE", "SUB", "1", "P"),
        (1, "itis", "PRES", "ACTIVE", "SUB", "2", "P"),
        (1, "int",  "PRES", "ACTIVE", "SUB", "3", "P"),
    ]

    count = 0
    for sk, ending, tense, voice, mood, person, number in new_inflections:
        conn.execute(
            """INSERT INTO inflections
               (pos, decl_which, decl_var, stem_key, ending,
                tense, voice, mood, person, number, age, freq)
               VALUES ('V', 5, 1, ?, ?, ?, ?, ?, ?, ?, 'X', 'A')""",
            (sk, ending, tense, voice, mood, person, number),
        )
        count += 1

    return count


def _patch_pronoun_inflections(conn: sqlite3.Connection) -> int:
    """Add missing NOM.S.M endings for demonstrative/intensive pronouns.

    PRON 6.1 (ille, iste) and similar demonstratives have NOM.S.N in
    INFLECTS but not NOM.S.M — the masculine nominative is irregular
    in the Ada code. Add them so headword reconstruction works.

    ille = ill + e, iste = ist + e, ipse = ips + e
    """
    existing = conn.execute(
        "SELECT id FROM inflections WHERE pos='PRON' AND decl_which=6 AND decl_var=1 "
        "AND case_val='NOM' AND number='S' AND gender='M'"
    ).fetchone()
    if existing:
        return 0

    existing = conn.execute(
        "SELECT id FROM inflections WHERE pos='PRON' AND decl_which=6 AND decl_var=2 "
        "AND case_val='NOM' AND number='S' AND gender='M' AND ending='e'"
    ).fetchone()
    if existing:
        return 0

    # (decl_which, decl_var, ending, gender)
    new_endings = [
        # PRON 6.1: ille, iste (stem + e/a)
        (6, 1, "e", "M"),
        (6, 1, "a", "F"),
        # PRON 6.2: ipse (stem + e/a) — us/os are archaic variants
        (6, 2, "e", "M"),
        (6, 2, "a", "F"),
    ]

    count = 0
    for dw, dv, ending, gender in new_endings:
        conn.execute(
            """INSERT INTO inflections
               (pos, decl_which, decl_var, stem_key, ending,
                case_val, number, gender, age, freq)
               VALUES ('PRON', ?, ?, 1, ?, 'NOM', 'S', ?, 'X', 'A')""",
            (dw, dv, ending, gender),
        )
        count += 1

    return count
