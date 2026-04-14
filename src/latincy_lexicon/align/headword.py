"""Align Whitaker's Words headwords to LatinCy lemmas.

Uses la_lemma_lookup.json (form→lemma mapping) for alignment.
Match strategies: exact → normalized → stem prefix.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from latincy_lexicon.align.normalize import normalize_latin
from latincy_lexicon.db.loader import load_headwords


def build_headwords(conn: sqlite3.Connection) -> int:
    """Reconstruct headwords from stem1 + nominative/infinitive endings.

    For nouns: stem1 + appropriate nom.sg ending from inflections table.
    For verbs: stem1 + appropriate 1st person sg present ending.
    For adjectives: stem1 + appropriate nom.sg.m ending.
    For others: stem1 as-is.

    Returns number of headwords created.
    """
    entries = conn.execute(
        """SELECT id, stem1, stem2, stem3, stem4, pos, decl_which, decl_var,
                  gender, verb_kind FROM dict_entries"""
    ).fetchall()

    headwords: list[tuple[str, str, int]] = []

    for entry in entries:
        entry_id = entry["id"]
        stem1 = entry["stem1"]
        pos = entry["pos"]
        decl_which = entry["decl_which"]
        decl_var = entry["decl_var"]
        gender = entry["gender"]
        verb_kind = entry["verb_kind"]

        if not stem1:
            continue

        hw = _reconstruct_headword(conn, stem1, pos, decl_which, decl_var,
                                   gender=gender, verb_kind=verb_kind)
        normalized = normalize_latin(hw)
        headwords.append((hw, normalized, entry_id))

    load_headwords(conn, headwords)
    return len(headwords)


def _reconstruct_headword(
    conn: sqlite3.Connection,
    stem1: str,
    pos: str,
    decl_which: int,
    decl_var: int,
    *,
    gender: str | None = None,
    verb_kind: str | None = None,
) -> str:
    """Reconstruct headword from stem1 + ending."""
    if pos == "N":
        # Declension 9 = indeclinable (abbreviations, foreign words)
        if decl_which == 9:
            return stem1
        # For 2nd declension, gender disambiguates (us/um/er/on)
        # Try gender-specific OR gender=X (wildcard) match
        if decl_which == 2 and gender and gender not in ("C", "X"):
            ending = _find_ending_with_wildcard_gender(
                conn, "N", decl_which, decl_var,
                gender=gender, stem_key=1)
            if ending is not None:
                return stem1 + ending
        ending = _find_ending(conn, "N", decl_which, decl_var,
                              case="NOM", number="S", stem_key=1)
        if ending is not None:
            return stem1 + ending

    elif pos == "V":
        if verb_kind == "DEP":
            # Deponent: headword is 1st person sg present passive
            ending = _find_ending(conn, "V", decl_which, decl_var,
                                  tense="PRES", voice="PASSIVE", mood="IND",
                                  person="1", number="S", stem_key=1)
            if ending is not None:
                return stem1 + ending
        # Active, semi-deponent, or fallback
        ending = _find_ending(conn, "V", decl_which, decl_var,
                              tense="PRES", voice="ACTIVE", mood="IND",
                              person="1", number="S", stem_key=1)
        if ending is not None:
            return stem1 + ending

    elif pos == "ADJ":
        # ADJ 3,2 (habilis-type): NOM.S ending is -is, gender=C
        # ADJ 3,1 (absens-type): NOM.S ending is empty (stem1 = full form)
        # ADJ 3,3 (acer-type): NOM.S ending is empty for M
        # For 3,2: prefer non-empty endings to avoid grabbing a wildcard ""
        # For others: accept empty endings normally
        prefer_nonempty = (decl_which == 3 and decl_var == 2)
        for g in ("M", "C", "X"):
            ending = _find_ending(conn, "ADJ", decl_which, decl_var,
                                  case="NOM", number="S", gender=g,
                                  comparison="POS", stem_key=1)
            if ending is not None:
                if prefer_nonempty and ending == "":
                    continue  # skip wildcard empty match, try next gender
                return stem1 + ending
        # Fallback without gender constraint
        ending = _find_ending(conn, "ADJ", decl_which, decl_var,
                              case="NOM", number="S",
                              comparison="POS", stem_key=1)
        if ending is not None:
            return stem1 + ending

    elif pos in ("PRON", "PACK"):
        # Pronouns are highly irregular. Strategy:
        # 1. Try NOM.S.M (the standard citation form)
        # 2. Try NOM.S with gender=C (common, for nos/ego)
        # 3. Try NOM.P with gender=C (for nos/vos which are inherently plural)
        # 4. Fall through to stem1 (for ille/iste/ipse where NOM.S.M is
        #    irregular and not derivable from stem + ending)
        # NO broadening across decl_var — pronouns are too irregular.
        for num, gender in [("S", "M"), ("S", "C"), ("P", "C")]:
            row = conn.execute(
                """SELECT ending FROM inflections
                   WHERE pos = 'PRON' AND decl_which = ? AND decl_var = ?
                   AND case_val = 'NOM' AND number = ? AND gender = ?
                   AND stem_key = 1 AND freq IN ('A', 'B', 'C')
                   ORDER BY length(ending) ASC, freq ASC LIMIT 1""",
                (decl_which, decl_var, num, gender),
            ).fetchone()
            if row:
                return stem1 + row["ending"]
        # No M/C ending found — irregular pronoun, stem1 is the best guess
        # (ille, iste, ipse: stem1 = ill/ist/ips, need special handling)

    elif pos == "NUM":
        # Check if this numeral has an exact NOM S ending for its decl_var
        exact_s = conn.execute(
            """SELECT ending FROM inflections
               WHERE pos = 'NUM' AND decl_which = ? AND decl_var = ?
               AND case_val = 'NOM' AND number = 'S' AND stem_key = 1
               LIMIT 1""",
            (decl_which, decl_var),
        ).fetchone()
        if exact_s:
            return stem1 + exact_s["ending"]
        # No exact singular — try plural (tres, duo, etc.)
        exact_p = conn.execute(
            """SELECT ending FROM inflections
               WHERE pos = 'NUM' AND decl_which = ? AND decl_var = ?
               AND case_val = 'NOM' AND number = 'P' AND stem_key = 1
               AND (gender = 'C' OR gender = 'M')
               LIMIT 1""",
            (decl_which, decl_var),
        ).fetchone()
        if exact_p:
            return stem1 + exact_p["ending"]
        # No NUM-specific ending found — indeclinable (septem, novem, etc.)
        return stem1

    elif pos in ("ADV", "PREP", "CONJ", "INTERJ"):
        return stem1

    # Fallback: stem1 as-is
    return stem1


def _find_ending_with_wildcard_gender(
    conn: sqlite3.Connection,
    pos: str,
    decl_which: int,
    decl_var: int,
    *,
    gender: str,
    stem_key: int = 1,
) -> str | None:
    """Find NOM.S ending matching gender OR gender=X (wildcard).

    For N 2.x: gender=M finds -us (2.1/2.5) or "" (2.3/2.7),
    gender=N finds -um (2.2/2.4), gender=X matches any.
    """
    row = conn.execute(
        """SELECT ending FROM inflections
           WHERE pos = ? AND decl_which = ? AND (decl_var = ? OR decl_var = 0)
           AND case_val = 'NOM' AND number = 'S' AND stem_key = ?
           AND (gender = ? OR gender = 'X')
           AND freq IN ('A', 'B', 'C')
           ORDER BY
               CASE WHEN gender = ? THEN 0 ELSE 1 END,
               freq ASC
           LIMIT 1""",
        (pos, decl_which, decl_var, stem_key, gender, gender),
    ).fetchone()
    if row:
        return row["ending"]
    return None


def _find_ending(
    conn: sqlite3.Connection,
    pos: str,
    decl_which: int,
    decl_var: int | None,
    stem_key: int = 1,
    **conditions: str,
) -> str | None:
    """Find a matching inflection ending with progressively broader matching.

    Tries exact (decl_which, decl_var) first, then decl_var=0 wildcard,
    then any decl_var for the given decl_which.
    """
    where_parts = ["pos = ?", "stem_key = ?"]
    params: list = [pos, stem_key]

    for col, val in conditions.items():
        if col == "case":
            where_parts.append("case_val = ?")
        else:
            where_parts.append(f"{col} = ?")
        params.append(val)

    where_base = " AND ".join(where_parts)

    # Strategy 1: exact match
    if decl_var is not None:
        query = f"""SELECT ending FROM inflections
                    WHERE {where_base} AND decl_which = ? AND (decl_var = ? OR decl_var = 0)
                    AND freq IN ('A', 'B', 'C')
                    ORDER BY freq ASC LIMIT 1"""
        row = conn.execute(query, params + [decl_which, decl_var]).fetchone()
        if row:
            return row["ending"]

    # Strategy 2: any decl_var for this decl_which
    query = f"""SELECT ending FROM inflections
                WHERE {where_base} AND decl_which = ?
                AND freq IN ('A', 'B', 'C')
                ORDER BY freq ASC LIMIT 1"""
    row = conn.execute(query, params + [decl_which]).fetchone()
    if row:
        return row["ending"]

    # Strategy 3: any decl_which (for universal endings like perf active)
    query = f"""SELECT ending FROM inflections
                WHERE {where_base}
                AND freq IN ('A', 'B', 'C')
                ORDER BY freq ASC LIMIT 1"""
    row = conn.execute(query, params).fetchone()
    if row:
        return row["ending"]

    return None


def align_to_latincy(
    conn: sqlite3.Connection,
    lemma_lookup_path: str | Path,
) -> dict[str, int]:
    """Align Words headwords to LatinCy lemmas using la_lemma_lookup.json.

    Populates the alignment table. Returns match statistics.

    Match strategies (in order):
    1. Exact: normalized headword == lemma in lookup values
    2. Direct: normalized headword exists as a key in lookup
    3. Stem prefix: try progressively shorter prefixes

    Args:
        conn: Database connection with headwords populated.
        lemma_lookup_path: Path to la_lemma_lookup.json.

    Returns:
        Dict with match statistics.
    """
    lemma_lookup_path = Path(lemma_lookup_path)
    with open(lemma_lookup_path) as f:
        lemma_lookup: dict[str, str] = json.load(f)

    # Build lemma set (all known lemma values, lowercased)
    lemma_set: set[str] = set()
    for lemma in lemma_lookup.values():
        lemma_set.add(lemma.lower())

    # Build lowercased key lookup for form→lemma
    lc_lookup: dict[str, str] = {}
    for form, lemma in lemma_lookup.items():
        lc_lookup[form.lower()] = lemma.lower()

    # Get all unique normalized headwords with entry IDs
    rows = conn.execute(
        "SELECT DISTINCT normalized, id, dict_entry_id FROM headwords"
    ).fetchall()

    stats = {"total": 0, "exact": 0, "lookup_form": 0, "stem_match": 0, "unmatched": 0}
    alignments: list[tuple] = []

    seen: set[tuple[str, str]] = set()

    for row in rows:
        normalized = row["normalized"]
        entry_id = row["dict_entry_id"]
        stats["total"] += 1

        # Strategy 1: normalized headword is a known lemma value
        if normalized in lemma_set:
            key = (normalized, normalized)
            if key not in seen:
                alignments.append((normalized, normalized, "exact", 1.0, entry_id))
                seen.add(key)
            stats["exact"] += 1
            continue

        # Strategy 2: normalized headword is a form key → use its lemma
        if normalized in lc_lookup:
            latincy_lemma = lc_lookup[normalized]
            key = (normalized, latincy_lemma)
            if key not in seen:
                alignments.append((normalized, latincy_lemma, "lookup_form", 0.9, entry_id))
                seen.add(key)
            stats["lookup_form"] += 1
            continue

        # Strategy 3: try stem1 directly (without ending) as a form key
        stem1_row = conn.execute(
            "SELECT stem1 FROM dict_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if stem1_row:
            stem1_norm = normalize_latin(stem1_row["stem1"])
            if stem1_norm in lc_lookup:
                latincy_lemma = lc_lookup[stem1_norm]
                key = (normalized, latincy_lemma)
                if key not in seen:
                    alignments.append((normalized, latincy_lemma, "stem_match", 0.7, entry_id))
                    seen.add(key)
                stats["stem_match"] += 1
                continue

        stats["unmatched"] += 1

    # Bulk insert alignments
    conn.executemany(
        """INSERT INTO alignment
           (words_headword, latincy_lemma, match_type, confidence, dict_entry_id)
           VALUES (?,?,?,?,?)""",
        alignments,
    )
    conn.commit()

    return stats
