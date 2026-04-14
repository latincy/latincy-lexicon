"""Export Whitaker's Words SQLite data to JSON for LatinCy runtime."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


# Map Words POS codes to UD POS tags for disambiguation
WORDS_TO_UD_POS = {
    "N": {"NOUN", "PROPN"},
    "V": {"VERB", "AUX"},
    "ADJ": {"ADJ"},
    "ADV": {"ADV"},
    "PREP": {"ADP"},
    "CONJ": {"CCONJ", "SCONJ"},
    "INTERJ": {"INTJ"},
    "PRON": {"PRON", "DET"},
    "PACK": {"PRON", "DET"},
    "NUM": {"NUM"},
    "VPAR": {"VERB", "ADJ"},
    "SUPINE": {"VERB"},
    "PREFIX": {"X"},
    "SUFFIX": {"X"},
    "TACKON": {"CCONJ", "SCONJ", "PART", "ADV"},
    "X": set(),
}


def _make_entry(row, match_type: str = "direct") -> dict:
    """Build a lexicon entry dict from a database row."""
    stems = [row["stem1"], row["stem2"], row["stem3"], row["stem4"]]
    principal_parts = [s for s in stems if s and s != "zzz"]

    entry = {
        "headword": row["headword"],
        "normalized_headword": row["normalized"],
        "pos": row["pos"],
        "ud_pos": sorted(WORDS_TO_UD_POS.get(row["pos"], set())),
        "glosses": [g.strip() for g in row["meaning"].split(";") if g.strip()],
        "principal_parts": principal_parts,
        "age": row["age"],
        "freq": row["freq"],
        "area": row["area"],
        "geo": row["geo"],
        "source": row["source"],
        "match_type": match_type,
    }

    if row["gender"]:
        entry["gender"] = row["gender"]
    try:
        if row["verb_kind"] and row["verb_kind"] != "X":
            entry["verb_kind"] = row["verb_kind"]
    except (IndexError, KeyError):
        pass
    try:
        if row["noun_kind"] and row["noun_kind"] != "X":
            entry["noun_kind"] = row["noun_kind"]
    except (IndexError, KeyError):
        pass
    try:
        if row["comparison"] and row["comparison"] != "X":
            entry["comparison"] = row["comparison"]
    except (IndexError, KeyError):
        pass

    return entry


def export_lexicon(conn: sqlite3.Connection, output_path: str | Path) -> int:
    """Export ALL entries to lexicon.json.

    Includes:
    1. Aligned entries (keyed by LatinCy lemma)
    2. Unaligned entries (keyed by normalized headword — self-keyed)
    3. Alternate keys for pluralia tantum (e.g., arma → armum entries)
    4. Tackons and addons

    Structure: {normalized_lemma: [entry_dict, ...]}

    Args:
        conn: Database connection with headwords populated.
        output_path: Path to write lexicon.json.

    Returns:
        Number of lemma keys in the exported lexicon.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lexicon: dict[str, list[dict]] = {}

    # 1. Aligned entries — keyed by LatinCy lemma
    aligned_entry_ids: set[int] = set()
    rows = conn.execute(
        """SELECT
               a.latincy_lemma,
               h.headword, h.normalized,
               d.id as entry_id,
               d.stem1, d.stem2, d.stem3, d.stem4,
               d.pos, d.decl_which, d.decl_var,
               d.gender, d.noun_kind, d.verb_kind,
               d.pronoun_kind, d.comparison, d.numeral_sort,
               d.age, d.area, d.geo, d.freq, d.source,
               d.meaning, a.match_type
           FROM alignment a
           JOIN headwords h ON h.dict_entry_id = a.dict_entry_id
               AND h.normalized = a.words_headword
           JOIN dict_entries d ON d.id = a.dict_entry_id
           ORDER BY a.latincy_lemma, d.freq ASC"""
    ).fetchall()

    for row in rows:
        lemma = row["latincy_lemma"]
        entry = _make_entry(row, row["match_type"])
        lexicon.setdefault(lemma, []).append(entry)
        aligned_entry_ids.add(row["entry_id"])

    # 2. Unaligned entries — keyed by normalized headword
    rows = conn.execute(
        """SELECT
               h.headword, h.normalized, d.id as entry_id,
               d.stem1, d.stem2, d.stem3, d.stem4,
               d.pos, d.decl_which, d.decl_var,
               d.gender, d.noun_kind, d.verb_kind,
               d.pronoun_kind, d.comparison, d.numeral_sort,
               d.age, d.area, d.geo, d.freq, d.source,
               d.meaning
           FROM dict_entries d
           JOIN headwords h ON h.dict_entry_id = d.id
           ORDER BY h.normalized, d.freq ASC"""
    ).fetchall()

    for row in rows:
        if row["entry_id"] in aligned_entry_ids:
            # Already exported under aligned key, but also add under
            # normalized headword as an alternate key
            pass

        lemma = row["normalized"]
        entry = _make_entry(row, "self")
        # Avoid exact duplicates
        existing = lexicon.get(lemma, [])
        if not any(e["headword"] == entry["headword"] and e["pos"] == entry["pos"]
                   and e["glosses"] == entry["glosses"] for e in existing):
            lexicon.setdefault(lemma, []).append(entry)

    # 3. Pluralia tantum — add plural-form keys using INFLECTS
    from latincy_lexicon.align.pluralia import build_plural_mappings, apply_plural_mappings
    pl_mappings = build_plural_mappings(conn)
    apply_plural_mappings(pl_mappings, lexicon)

    # 4. Tackons and addons
    _add_addons(conn, lexicon)

    with open(output_path, "w") as f:
        json.dump(lexicon, f, ensure_ascii=False, indent=1)

    return len(lexicon)




def export_analyzer_data(conn: sqlite3.Connection, output_path: str | Path) -> int:
    """Export analyzer data to JSON for runtime use (no sqlite3 dependency).

    Dumps everything the Analyzer needs into a single JSON file:
    inflections, uniques, tackons, dict entries, headwords, and
    pluralia tantum mappings.

    Args:
        conn: Database connection with all tables populated.
        output_path: Path to write analyzer.json.

    Returns:
        Number of dict entries exported.
    """
    from latincy_lexicon.align.pluralia import build_plural_mappings

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    inflections = [dict(r) for r in conn.execute(
        """SELECT pos, decl_which, decl_var, stem_key, ending,
                  case_val, number, gender, tense, voice, mood,
                  person, comparison, numeral_sort, age, freq
           FROM inflections"""
    ).fetchall()]

    uniques = [dict(r) for r in conn.execute(
        """SELECT form, pos, decl_which, decl_var,
                  case_val, number, gender, tense, voice, mood,
                  person, comparison, meaning
           FROM uniques"""
    ).fetchall()]

    tackons = [r["fix"].lower() for r in conn.execute(
        "SELECT fix FROM addons WHERE addon_type = 'TACKON' ORDER BY length(fix) DESC"
    ).fetchall()]

    entries = [dict(r) for r in conn.execute(
        """SELECT id, stem1, stem2, stem3, stem4,
                  pos, decl_which, decl_var,
                  gender, noun_kind, verb_kind, pronoun_kind,
                  comparison, numeral_sort,
                  age, area, geo, freq, source, meaning
           FROM dict_entries"""
    ).fetchall()]

    headwords: dict[int, str] = {}
    for r in conn.execute("SELECT dict_entry_id, normalized FROM headwords").fetchall():
        headwords[r["dict_entry_id"]] = r["normalized"]

    plural_mappings = build_plural_mappings(conn)

    data = {
        "inflections": inflections,
        "uniques": uniques,
        "tackons": tackons,
        "entries": entries,
        "headwords": headwords,
        "plural_mappings": plural_mappings,
    }

    with open(output_path, "w") as f:
        json.dump(data, f, ensure_ascii=False)

    return len(entries)


def _add_addons(conn: sqlite3.Connection, lexicon: dict) -> None:
    """Add tackons, prefixes, and suffixes to the lexicon."""
    rows = conn.execute(
        "SELECT addon_type, fix, connect, from_pos, to_pos, meaning FROM addons"
    ).fetchall()

    for row in rows:
        fix = row["fix"].lower().replace("v", "u").replace("j", "i")
        addon_type = row["addon_type"]

        # Determine ud_pos based on addon type
        if addon_type == "TACKON":
            ud_pos = ["CCONJ", "PART", "SCONJ"]
        elif addon_type == "PREFIX":
            ud_pos = ["X"]
        elif addon_type == "SUFFIX":
            ud_pos = ["X"]
        else:
            ud_pos = ["X"]

        entry = {
            "headword": row["fix"],
            "normalized_headword": fix,
            "pos": addon_type,
            "ud_pos": ud_pos,
            "glosses": [g.strip() for g in row["meaning"].split(";") if g.strip()],
            "principal_parts": [],
            "age": "X",
            "freq": "X",
            "area": "X",
            "geo": "X",
            "source": "X",
            "match_type": "addon",
            "addon_type": addon_type,
        }
        if row["connect"]:
            entry["connect"] = row["connect"]

        lexicon.setdefault(fix, []).append(entry)
