"""Generate supplemental lemma→form mappings from Whitaker's Words.

Uses DICTLINE stems + INFLECTS endings to generate all possible forms
for each entry, creating a form→lemma lookup that can supplement
la_lemma_lookup.json with forms/lemmas not in existing LatinCy data.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from latincy_lexicon.align.normalize import normalize_latin


def generate_form_lemma_pairs(conn: sqlite3.Connection) -> dict[str, str]:
    """Generate form→lemma mappings from Words data.

    For each dict_entry with a reconstructed headword:
    1. Get the normalized headword as the lemma
    2. Generate inflected forms by combining stems with matching endings
    3. Map each normalized form → normalized headword (lemma)

    Returns:
        Dict mapping normalized form → normalized lemma.
    """
    form_to_lemma: dict[str, str] = {}

    # Get all entries with headwords
    entries = conn.execute(
        """SELECT d.id, d.stem1, d.stem2, d.stem3, d.stem4,
                  d.pos, d.decl_which, d.decl_var,
                  h.normalized as lemma
           FROM dict_entries d
           JOIN headwords h ON h.dict_entry_id = d.id"""
    ).fetchall()

    for entry in entries:
        lemma = entry["lemma"]
        pos = entry["pos"]
        decl_which = entry["decl_which"]
        decl_var = entry["decl_var"]
        stems = {
            1: entry["stem1"],
            2: entry["stem2"],
            3: entry["stem3"],
            4: entry["stem4"],
        }

        # The lemma itself maps to itself
        form_to_lemma[lemma] = lemma

        # Get matching inflections
        inflections = conn.execute(
            """SELECT stem_key, ending FROM inflections
               WHERE pos = ? AND (decl_which = ? OR decl_which = 0)
               AND (decl_var = ? OR decl_var = 0)""",
            (pos, decl_which, decl_var),
        ).fetchall()

        for infl in inflections:
            stem_key = infl["stem_key"]
            ending = infl["ending"]
            stem = stems.get(stem_key, "")

            if not stem or stem == "zzz":
                continue

            form = normalize_latin(stem + ending)
            if form and form not in form_to_lemma:
                form_to_lemma[form] = lemma

    return form_to_lemma


def export_supplement(
    conn: sqlite3.Connection,
    output_path: str | Path,
    existing_lookup_path: str | Path | None = None,
) -> dict[str, int]:
    """Export supplemental form→lemma mappings.

    Only includes forms NOT already in the existing lookup.

    Args:
        conn: Database connection with headwords and inflections.
        output_path: Path to write supplement JSON.
        existing_lookup_path: Path to existing la_lemma_lookup.json.

    Returns:
        Statistics dict.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate all form→lemma pairs from Words
    words_pairs = generate_form_lemma_pairs(conn)

    # Load existing lookup if provided
    existing: set[str] = set()
    if existing_lookup_path:
        existing_path = Path(existing_lookup_path)
        if existing_path.exists():
            with open(existing_path) as f:
                existing_data = json.load(f)
            existing = set(k.lower() for k in existing_data.keys())

    # Filter to only new forms
    supplement = {
        form: lemma
        for form, lemma in words_pairs.items()
        if form not in existing
    }

    with open(output_path, "w") as f:
        json.dump(supplement, f, ensure_ascii=False, indent=1)

    return {
        "total_words_forms": len(words_pairs),
        "existing_forms": len(existing),
        "new_forms": len(supplement),
        "new_lemmas": len(set(supplement.values())),
    }


def merge_with_existing(
    supplement_path: str | Path,
    existing_path: str | Path,
    output_path: str | Path,
) -> dict[str, int]:
    """Merge supplement into existing lookup, producing a combined file.

    Args:
        supplement_path: Path to supplement JSON from export_supplement().
        existing_path: Path to existing la_lemma_lookup.json.
        output_path: Path to write merged output.

    Returns:
        Statistics dict.
    """
    with open(existing_path) as f:
        existing = json.load(f)

    with open(supplement_path) as f:
        supplement = json.load(f)

    merged = {**existing, **supplement}

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(merged, f, ensure_ascii=False)

    return {
        "existing_entries": len(existing),
        "supplement_entries": len(supplement),
        "merged_entries": len(merged),
        "net_new": len(merged) - len(existing),
    }
