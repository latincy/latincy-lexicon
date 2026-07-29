"""In-memory build pipeline: raw WW data files → JSON, no SQLite.

Replaces the build-db → export chain with a single pass that parses
the bundled data files directly into dicts and writes JSON.
"""

from __future__ import annotations

import hashlib
import json
import os
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from latincy_lexicon.align.normalize import normalize_latin
from latincy_lexicon.glosses import (
    extract_sources,
    split_glosses,
    strip_usage_note,
)
from latincy_lexicon.models import DictEntry, Inflection

if TYPE_CHECKING:
    from latincy_lexicon.analyzer import Analyzer


# Source-code priority for dedup tiebreaking. Higher = more authoritative.
# Classical references outrank Whitaker's custom/overlay additions — the
# latter sometimes carry shortcut stems (e.g. cano missing the reduplicated
# perfect stem `cecin`) that would otherwise win by first-seen.
_SOURCE_PRIORITY: dict[str, int] = {
    "O": 10,  # Oxford Latin Dictionary
    "L": 9,   # Lewis
    "G": 9,   # Lewis & Short
    "C": 8,   # Cassell's
    "W": 7,   # Whitaker's Words
    "E": 6,   # Stelten, Ecclesiastical Latin
    "F": 6,   # Deferrari, Aquinas
    "P": 5,   # Souter
    "K": 5,   # Calepinus Novus
    "M": 5,   # Latham
    "B": 5,   # Beeson, Medieval Primer
    "D": 4,   # Adams, Sexual Vocabulary
    "V": 4,   # Vademecum
    "Q": 3,   # Other
    "S": 2,   # Whitaker custom — frequently carries stub/shortcut stems
    "X": 1,   # Unknown
}

# Whitaker frequency-code rank for dedup tiebreaking. Higher = more frequent =
# more authoritative. Breaks ties *within* a source-priority tie, so the
# canonical high-frequency homograph wins over a rarer duplicate that shares
# (headword, pos, glosses) — e.g. `pario` (bear/give birth) ships as both a
# freq-A entry (peperi/partum) and a freq-E entry (parire/paritum) from the
# same source; without this the first-listed freq-E stub would win.
_FREQ_PRIORITY: dict[str, int] = {
    "A": 7,  # very frequent
    "B": 6,
    "C": 5,
    "D": 4,
    "E": 3,
    "F": 2,  # rare
    "X": 1,  # unknown / unranked (also N, I, etc. fall through to default 0)
}


# ---------------------------------------------------------------------------
# Locate bundled data files
# ---------------------------------------------------------------------------

def _data_path(filename: str) -> Path:
    """Return path to a bundled data file in latincy_lexicon/data/."""
    ref = resources.files("latincy_lexicon") / "data" / filename
    # resources.files returns a Traversable; for on-disk files it's a Path
    return Path(str(ref))


def data_dir() -> Path:
    """Return the package data directory."""
    return Path(str(resources.files("latincy_lexicon") / "data"))


def senses_path() -> Path:
    """Return path to the bundled lewis_short_senses.json (shipped in wheel)."""
    return Path(str(resources.files("latincy_lexicon") / "data" / "json" / "lewis_short_senses.json"))


def sense_index_path() -> Path:
    """Return path to the bundled lewis_short_index.json (shipped in wheel)."""
    return Path(str(resources.files("latincy_lexicon") / "data" / "json" / "lewis_short_index.json"))


# ---------------------------------------------------------------------------
# Parse raw files → model objects
# ---------------------------------------------------------------------------

def _parse_all(vendor: Path | None = None) -> dict:
    """Parse all WW data files from bundled package data (or vendor override).

    Returns dict with keys: entries, inflections, addons, uniques.
    """
    from latincy_lexicon.parsers.dictline import parse_dictline
    from latincy_lexicon.parsers.inflects import parse_inflects
    from latincy_lexicon.parsers.addons import parse_addons
    from latincy_lexicon.parsers.uniques import parse_uniques

    if vendor is None:
        base = data_dir()
    else:
        base = Path(vendor)

    return {
        "entries": parse_dictline(base / "DICTLINE.GEN"),
        "inflections": parse_inflects(base / "INFLECTS.LAT"),
        "addons": parse_addons(base / "ADDONS.LAT"),
        "uniques": parse_uniques(base / "UNIQUES.LAT"),
    }


# ---------------------------------------------------------------------------
# Convert model objects → dicts (same shape as DB rows)
# ---------------------------------------------------------------------------

def _entry_to_dict(e: DictEntry, entry_id: int) -> dict:
    """Convert a DictEntry model to a dict matching the DB row shape."""
    return {
        "id": entry_id,
        "stem1": e.stem1,
        "stem2": e.stem2,
        "stem3": e.stem3,
        "stem4": e.stem4,
        "pos": str(e.pos),
        "decl_which": e.decl_which,
        "decl_var": e.decl_var,
        "gender": str(e.gender) if e.gender else None,
        "noun_kind": str(e.noun_kind) if e.noun_kind else None,
        "verb_kind": str(e.verb_kind) if e.verb_kind else None,
        "pronoun_kind": str(e.pronoun_kind) if e.pronoun_kind else None,
        "comparison": str(e.comparison) if e.comparison else None,
        "numeral_sort": str(e.numeral_sort) if e.numeral_sort else None,
        "age": str(e.age),
        "area": str(e.area),
        "geo": str(e.geo),
        "freq": str(e.freq),
        "source": str(e.source),
        "meaning": e.meaning,
        "line_number": e.line_number,
    }


def _inflection_to_dict(inf: Inflection) -> dict:
    """Convert an Inflection model to a dict matching the DB row shape."""
    return {
        "pos": str(inf.pos),
        "decl_which": inf.decl_which,
        "decl_var": inf.decl_var,
        "case_val": inf.case,
        "number": inf.number,
        "gender": inf.gender,
        "tense": inf.tense,
        "voice": inf.voice,
        "mood": inf.mood,
        "person": inf.person,
        "comparison": inf.comparison,
        "numeral_sort": inf.numeral_sort,
        "stem_key": inf.stem_key,
        "ending": inf.ending,
        "age": str(inf.age),
        "freq": str(inf.freq),
    }


def _unique_to_dict(u) -> dict:
    """Convert a Unique model to a dict matching the DB row shape."""
    return {
        "form": u.form,
        "pos": str(u.pos),
        "decl_which": u.decl_which,
        "decl_var": u.decl_var,
        "case_val": u.case,
        "number": u.number,
        "gender": u.gender,
        "tense": u.tense,
        "voice": u.voice,
        "mood": u.mood,
        "person": u.person,
        "comparison": u.comparison,
        "stem1": u.stem1,
        "stem2": u.stem2,
        "stem3": u.stem3,
        "stem4": u.stem4,
        "meaning": u.meaning,
    }


def _addon_to_dict(a) -> dict:
    """Convert an Addon model to a dict matching the DB row shape."""
    return {
        "addon_type": str(a.addon_type),
        "fix": a.fix,
        "connect": a.connect,
        "from_pos": str(a.from_pos),
        "to_pos": str(a.to_pos),
        "meaning": a.meaning,
    }


# ---------------------------------------------------------------------------
# Patches (in-memory equivalents of db/patches.py)
# ---------------------------------------------------------------------------

def _apply_patches(
    entries: list[dict],
    inflections: list[dict],
    headwords: dict[int, tuple[str, str]],
    next_id: int,
) -> int:
    """Apply all patches in-memory. Returns updated next_id."""
    next_id = _patch_sum_esse(entries, headwords, next_id)
    _patch_sum_inflections(inflections)
    _patch_pronoun_inflections(inflections)
    next_id = _patch_packon_pronouns(entries, headwords, next_id)
    _apply_overrides(entries, _overrides_dir())
    return next_id


def _overrides_dir() -> Path:
    """Path to the bundled overrides directory."""
    return Path(str(resources.files("latincy_lexicon") / "data" / "overrides"))


def _apply_overrides(
    entries: list[dict],
    overrides_dir: Path,
) -> None:
    """Layer curated overrides on top of canonical entries.

    Reads every ``OVR-*.toml`` file under ``overrides_dir``, skips those
    whose ``status != "active"``, and applies each active override by
    mutating the matching entry's field and recording provenance under
    ``entry["_overrides"]``.

    See ``src/latincy_lexicon/data/overrides/README.md`` for the schema.
    Missing directory is a no-op (forks without overrides still build).
    """
    import tomllib

    if not overrides_dir.exists() or not overrides_dir.is_dir():
        return

    for toml_path in sorted(overrides_dir.glob("OVR-*.toml")):
        with open(toml_path, "rb") as f:
            ovr = tomllib.load(f)

        if ovr.get("status") != "active":
            continue

        _apply_one_override(entries, ovr)


def _apply_one_override(entries: list[dict], ovr: dict) -> None:
    """Apply a single parsed override to `entries` in place.

    ``[change]`` may be a single table or an array-of-tables (``[[change]]``);
    the latter lets one override edit several fields of the same entry as one
    attributable record (e.g. backfilling both ``stem3`` and ``stem4`` of a
    truncated stub). The ``[target]`` may carry optional ``decl_which`` /
    ``decl_var`` to disambiguate homographs sharing (stem1, pos).
    """
    ovr_id = ovr["id"]
    target = ovr["target"]

    target_entry = _find_entry(
        entries, target["lemma"], target["pos"],
        decl_which=target.get("decl_which"), decl_var=target.get("decl_var"),
    )
    if target_entry is None:
        raise ValueError(
            f"{ovr_id}: target entry not found "
            f"(lemma={target['lemma']!r}, pos={target['pos']!r})"
        )

    changes = ovr["change"]
    if isinstance(changes, dict):
        changes = [changes]
    for change in changes:
        _apply_one_change(entries, ovr, target_entry, change)


def _apply_one_change(
    entries: list[dict], ovr: dict, target_entry: dict, change: dict,
) -> None:
    """Apply one field change (borrow_from or literal) to ``target_entry``."""
    ovr_id = ovr["id"]
    field = change["field"]

    if "borrow_from" in change:
        borrow = change["borrow_from"]
        source_entry = _find_entry(
            entries, borrow["lemma"], borrow["pos"],
            decl_which=borrow.get("decl_which"), decl_var=borrow.get("decl_var"),
        )
        if source_entry is None:
            raise ValueError(
                f"{ovr_id}: borrow_from source not found "
                f"(lemma={borrow['lemma']!r}, pos={borrow['pos']!r})"
            )
        new_value = source_entry[borrow["field"]]
        source_record = {
            "kind": "borrow",
            "lemma": borrow["lemma"],
            "pos": borrow["pos"],
            "field": borrow["field"],
        }
    elif "to" in change:
        new_value = change["to"]
        source_record = {"kind": "literal"}
    else:
        raise ValueError(
            f"{ovr_id}: change block must have either 'borrow_from' or 'to'"
        )

    original = target_entry.get(field)
    target_entry[field] = new_value
    date_val = ovr.get("date")
    date_str = date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)
    target_entry.setdefault("_overrides", []).append({
        "id": ovr_id,
        "field": field,
        "original_value": original,
        "source": source_record,
        "date": date_str,
        "reason_short": ovr.get("reason_short", ""),
    })


def _find_entry(
    entries: list[dict], lemma: str, pos: str,
    *, decl_which: int | None = None, decl_var: int | None = None,
) -> dict | None:
    """Return the first entry matching stem1==lemma and pos.

    When ``decl_which`` / ``decl_var`` are given, they further constrain the
    match so an override can target one of several homographs.
    """
    for e in entries:
        if e.get("stem1") != lemma or e.get("pos") != pos:
            continue
        if decl_which is not None and e.get("decl_which") != decl_which:
            continue
        if decl_var is not None and e.get("decl_var") != decl_var:
            continue
        return e
    return None


def _patch_sum_esse(
    entries: list[dict],
    headwords: dict[int, tuple[str, str]],
    next_id: int,
) -> int:
    """Add sum/esse entry — hardcoded in original Ada, missing from DICTLINE."""
    # Check if already present
    for e in entries:
        if e["pos"] == "V" and e["decl_which"] == 5 and e["decl_var"] == 1:
            if "be; exist" in (e.get("meaning") or ""):
                return next_id

    meaning = (
        "be; exist; (also used to form verb perfect passive tenses) "
        "with compound forms (adsum, absum, possum, prosum, etc.);"
    )
    entry_id = next_id
    next_id += 1

    entries.append({
        "id": entry_id,
        "stem1": "s", "stem2": "", "stem3": "fu", "stem4": "fut",
        "pos": "V", "decl_which": 5, "decl_var": 1,
        "gender": None, "noun_kind": None, "verb_kind": "TO_BE",
        "pronoun_kind": None, "comparison": None, "numeral_sort": None,
        "age": "X", "area": "X", "geo": "X", "freq": "A", "source": "X",
        "meaning": meaning, "line_number": None,
    })

    headwords[entry_id] = ("sum", "sum")
    return next_id


def _patch_sum_inflections(inflections: list[dict]) -> None:
    """Add V 5.1 inflections for present/imperfect/future and present subj."""
    # Check if already patched
    for inf in inflections:
        if (inf["pos"] == "V" and inf["decl_which"] == 5 and inf["decl_var"] == 1
                and inf["tense"] == "PRES" and inf["mood"] == "IND"
                and inf["person"] == "1" and inf["number"] == "S"):
            return

    new = [
        # Present indicative
        (1, "um",    "PRES", "ACTIVE", "IND", "1", "S"),
        (2, "es",    "PRES", "ACTIVE", "IND", "2", "S"),
        (2, "est",   "PRES", "ACTIVE", "IND", "3", "S"),
        (1, "umus",  "PRES", "ACTIVE", "IND", "1", "P"),
        (2, "estis", "PRES", "ACTIVE", "IND", "2", "P"),
        (1, "unt",   "PRES", "ACTIVE", "IND", "3", "P"),
        # Imperfect indicative
        (2, "eram",   "IMPF", "ACTIVE", "IND", "1", "S"),
        (2, "eras",   "IMPF", "ACTIVE", "IND", "2", "S"),
        (2, "erat",   "IMPF", "ACTIVE", "IND", "3", "S"),
        (2, "eramus", "IMPF", "ACTIVE", "IND", "1", "P"),
        (2, "eratis", "IMPF", "ACTIVE", "IND", "2", "P"),
        (2, "erant",  "IMPF", "ACTIVE", "IND", "3", "P"),
        # Future indicative
        (2, "ero",    "FUT", "ACTIVE", "IND", "1", "S"),
        (2, "eris",   "FUT", "ACTIVE", "IND", "2", "S"),
        (2, "erit",   "FUT", "ACTIVE", "IND", "3", "S"),
        (2, "erimus", "FUT", "ACTIVE", "IND", "1", "P"),
        (2, "eritis", "FUT", "ACTIVE", "IND", "2", "P"),
        (2, "erunt",  "FUT", "ACTIVE", "IND", "3", "P"),
        # Present subjunctive
        (1, "im",   "PRES", "ACTIVE", "SUB", "1", "S"),
        (1, "is",   "PRES", "ACTIVE", "SUB", "2", "S"),
        (1, "it",   "PRES", "ACTIVE", "SUB", "3", "S"),
        (1, "imus", "PRES", "ACTIVE", "SUB", "1", "P"),
        (1, "itis", "PRES", "ACTIVE", "SUB", "2", "P"),
        (1, "int",  "PRES", "ACTIVE", "SUB", "3", "P"),
    ]

    for sk, ending, tense, voice, mood, person, number in new:
        inflections.append({
            "pos": "V", "decl_which": 5, "decl_var": 1,
            "stem_key": sk, "ending": ending,
            "tense": tense, "voice": voice, "mood": mood,
            "person": person, "number": number,
            "case_val": None, "gender": None,
            "comparison": None, "numeral_sort": None,
            "age": "X", "freq": "A",
        })


def _patch_pronoun_inflections(inflections: list[dict]) -> None:
    """Add missing NOM.S.M/F endings for demonstrative pronouns."""
    for inf in inflections:
        if (inf["pos"] == "PRON" and inf["decl_which"] == 6 and inf["decl_var"] == 1
                and inf["case_val"] == "NOM" and inf["number"] == "S"
                and inf["gender"] == "M"):
            return

    for dw, dv, ending, gender in [(6,1,"e","M"), (6,1,"a","F"),
                                    (6,2,"e","M"), (6,2,"a","F")]:
        inflections.append({
            "pos": "PRON", "decl_which": dw, "decl_var": dv,
            "stem_key": 1, "ending": ending,
            "case_val": "NOM", "number": "S", "gender": gender,
            "tense": None, "voice": None, "mood": None,
            "person": None, "comparison": None, "numeral_sort": None,
            "age": "X", "freq": "A",
        })


# PACKON pronouns — indefinite/relative pronouns whose paradigms are
# assembled at runtime from a base pronoun stem (qui/quis) plus a TACKON
# suffix (-quam, -que, -dam, -piam, -libet, -vis, -cumque). They have NO
# entry in DICTLINE.GEN — Whitaker's original Ada program recognizes them
# via the PACKON descriptors in ADDONS.LAT and the UNIQUES entries for
# irregular neuter nom/acc forms (quicquam, quidquam, quidque, etc.).
#
# The analyzer already handles surface-form lookup correctly (UNIQUES +
# tackon stripping). But the lexicon export (keyed by lemma) has no
# `quisquam` / `quisque` / `quidam` key, so downstream `token._.lexicon`
# lookups using the LatinCy-assigned lemma return empty.
#
# Fix: synthesize a DICTLINE-equivalent entry for each PACKON pronoun so
# the lexicon export picks it up, in the same spirit as the sum/esse
# patch above. Meanings come verbatim from the PACKON comments in
# ADDONS.LAT (search "PACKON w/quis"/"PACKON w/qui" in that file).
#
# Listed here in the order LatinCy's lemmatizer actually emits them (so
# `quicquam` → `quisquam`, etc.). We only add lemmas that LatinCy is
# known to produce as targets and that have no DICTLINE entry.
_PACKON_PRONOUNS: list[dict] = [
    {
        "lemma": "quisquam",
        # `quis` + `-quam` (indefinite). Substantive neuter is `quicquam`
        # / `quidquam` (handled via UNIQUES in the analyzer).
        # ADDONS.LAT: PACKON w/quis (TACKON quam).
        "meaning": (
            "any; any man/person, anybody/anyone, any whatever, anything;"
        ),
    },
    {
        "lemma": "quisque",
        # `qui` + `-que` (indefinite/universal). ADDONS.LAT: PACKON w/qui
        # (TACKON que).
        "meaning": (
            "whoever it be; whatever; each, each one; everyone, everything;"
        ),
    },
    {
        "lemma": "quidam",
        # `qui` + `-dam` (indefinite). ADDONS.LAT: PACKON w/qui
        # (TACKON dam).
        "meaning": (
            "certain; a certain (one); a certain thing;"
        ),
    },
    {
        "lemma": "quispiam",
        # `qui` + `-piam` (indefinite). ADDONS.LAT: PACKON w/qui
        # (TACKON piam). Despite the "w/qui" comment in ADDONS, the
        # lemma surface form is `quispiam` (with the `quis` nom sg).
        "meaning": (
            "any/somebody, any, some, any/something;"
        ),
    },
    {
        "lemma": "quilibet",
        # `qui` + `-libet` (indefinite). ADDONS.LAT: PACKON w/qui
        # (TACKON libet).
        "meaning": (
            "anyone; whatever; what you will; no matter which;"
        ),
    },
    {
        "lemma": "quivis",
        # `qui` + `-vis` (indefinite). ADDONS.LAT: PACKON w/qui
        # (TACKON vis).
        "meaning": (
            "whoever it be, whomever you please; any/anything whatever;"
        ),
    },
    {
        "lemma": "quicumque",
        # `qui` + `-cumque` (generalizing relative). ADDONS.LAT:
        # PACKON w/qui (TACKON cumque).
        "meaning": (
            "whoever; whatever; everyone who, all that, anything that;"
        ),
    },
]


def _patch_packon_pronouns(
    entries: list[dict],
    headwords: dict[int, tuple[str, str]],
    next_id: int,
) -> int:
    """Add dict entries for PACKON pronouns (quisquam, etc.).

    These are assembled at runtime from pronoun stem + TACKON in WW, so
    they lack DICTLINE entries. Without this patch, the exported lexicon
    has no key for the LatinCy-produced lemma, and `token._.lexicon` is
    empty for every form of the paradigm (see fix-quisquam-lexicon-gap
    branch / regression test ``tests/test_lexicon_quisquam.py``).
    """
    # A quisquam/quisque-style entry may already exist — guard against
    # double-adding on re-runs. We look both at patch-provided headwords
    # (e.g., sum from _patch_sum_esse) and at DICTLINE entries whose
    # stem1 would normalize to the target lemma.
    existing_lemmas = {norm for _, norm in headwords.values()}
    for e in entries:
        if e["pos"] == "PRON" and e.get("stem1"):
            existing_lemmas.add(normalize_latin(e["stem1"]))

    for spec in _PACKON_PRONOUNS:
        lemma = spec["lemma"]
        if lemma in existing_lemmas:
            continue  # already present from DICTLINE or another patch

        entry_id = next_id
        next_id += 1

        entries.append({
            "id": entry_id,
            # stem1 set to the lemma so headword reconstruction and
            # stem-based lookups both see a sensible value. The analyzer
            # never reaches these entries via stem+ending (the analyzer
            # uses UNIQUES/tackon stripping for this paradigm), so the
            # concrete stem choice doesn't affect parse results.
            "stem1": lemma,
            "stem2": "zzz", "stem3": "zzz", "stem4": "zzz",
            "pos": "PRON",
            "decl_which": 1, "decl_var": 0,
            "gender": None, "noun_kind": None, "verb_kind": None,
            "pronoun_kind": "INDEF",
            "comparison": None, "numeral_sort": None,
            "age": "X", "area": "X", "geo": "X", "freq": "C", "source": "X",
            "meaning": spec["meaning"],
            "line_number": None,
        })
        headwords[entry_id] = (lemma, lemma)

    return next_id


# ---------------------------------------------------------------------------
# Headword reconstruction (in-memory, replaces align/headword.py SQL)
# ---------------------------------------------------------------------------

# WW-capitalized common nouns: entries whose DICTLINE stem carries a capital for
# a folded-in proper/deity sense, even though the word is fundamentally a common
# noun that a dictionary lemmatizes lowercase. Reconstruction would otherwise
# render the display headword capitalized (e.g. stem "De" → "Deus"), the lone
# false-capital once headwords stopped being force-lowercased — genuine proper
# nouns (Juno, Roma, Latinus) and correctly case-split homographs (augustus vs
# Augustus) are unaffected. Keyed by (stem1, pos); the stems themselves are left
# capitalized so the form generator can still recover the proper-sense variant
# ("Deus"), keeping the lowercase paradigm standard (see generator.py, REG-002).
# Mirrors the curated-allowlist pattern already used for WW quirks
# (generator._LOCATIVE_COMMON_NOUNS).
_LOWERCASE_DISPLAY_HEADWORDS: frozenset[tuple[str, str]] = frozenset({
    ("De", "N"),   # deus, dei — the general "god"; cf. OVR-004
})


def _build_headwords(
    entries: list[dict],
    inflections: list[dict],
) -> dict[int, tuple[str, str]]:
    """Build headwords dict: entry_id → (headword, normalized).

    Replicates the logic from align/headword.py without SQL.
    """
    headwords: dict[int, tuple[str, str]] = {}

    for entry in entries:
        stem1 = entry["stem1"]
        if not stem1:
            continue

        hw = _reconstruct_headword(
            inflections, stem1,
            entry["pos"], entry["decl_which"], entry["decl_var"],
            gender=entry.get("gender"),
            verb_kind=entry.get("verb_kind"),
            stem2=entry.get("stem2"),
            stem3=entry.get("stem3"),
            meaning=entry.get("meaning"),
        )
        if hw and (stem1, entry["pos"]) in _LOWERCASE_DISPLAY_HEADWORDS:
            hw = hw[:1].lower() + hw[1:]
        normalized = normalize_latin(hw)
        headwords[entry["id"]] = (hw, normalized)

    return headwords


def _reconstruct_defective_headword(
    inflections: list[dict],
    pos: str,
    decl_which: int,
    decl_var: int,
    *,
    stem2: str | None,
    stem3: str | None,
    gender: str | None,
    verb_kind: str | None,
    meaning: str | None,
) -> str:
    """Lemma for entries whose stem1 is the Whitaker 'zzz' placeholder.

    Builds the citation form from the first real stem instead of emitting a
    'zzz'-prefixed lemma. Guarantees the placeholder never reaches output:
    when no rule fits, falls back to the first non-placeholder stem.
    """
    real = (stem2 if stem2 and stem2 != "zzz" else None,
            stem3 if stem3 and stem3 != "zzz" else None)

    if pos == "V" and real[1]:
        # Perfect-system-only verbs (memini, odi, novi). Real stem is the
        # perfect (stem3); cite the perfect 1sg, or 3sg for impersonals.
        person = "3" if verb_kind == "IMPERS" else "1"
        ending = _find_ending(
            inflections, "V", decl_which, decl_var, stem_key=3,
            tense="PERF", voice="ACTIVE", mood="IND", person=person, number="S")
        return real[1] + (ending if ending is not None
                          else ("it" if person == "3" else "i"))

    if pos == "ADJ" and real[1]:
        # Comparative-only adjectives (deterior, ulterior): stem3 + COMP NOM.S.
        ending = _find_ending(
            inflections, "ADJ", decl_which, decl_var, stem_key=3,
            case_val="NOM", number="S", comparison="COMP")
        return real[1] + (ending if ending is not None else "or")

    if pos in ("ADV", "PREP", "CONJ", "INTERJ") and real[0]:
        # Comparative adverbs (deterius, ditius): the form itself is stem2.
        return real[0]

    if pos == "N" and real[0]:
        # Pluralia tantum with no singular (multi/multae): stem2 + NOM.P.
        # Plural endings are coded gender C/N, never M/F, so only constrain
        # gender to pick the neuter ending apart from the common one.
        if meaning and ("(pl.)" in meaning or "(pl)" in meaning):
            conds = {"case_val": "NOM", "number": "P"}
            if gender == "N":
                conds["gender"] = "N"
            ending = _find_ending(inflections, "N", decl_which, decl_var,
                                  stem_key=2, **conds)
            if ending is not None:
                return real[0] + ending
        return real[0]

    if pos == "PRON" and real[0]:
        # Reflexive pronoun (sui/sibi/se): no nominative; cite the genitive.
        # Its genitive ending is coded number=X (number-invariant), so don't
        # constrain number or the lookup falls through to the wrong paradigm.
        ending = _find_ending(inflections, "PRON", decl_which, decl_var,
                              stem_key=2, case_val="GEN")
        if ending is not None:
            return real[0] + ending
        return real[0]

    # No rule matched: never emit the placeholder.
    return real[0] or real[1] or "zzz"


def _reconstruct_headword(
    inflections: list[dict],
    stem1: str,
    pos: str,
    decl_which: int,
    decl_var: int,
    *,
    gender: str | None = None,
    verb_kind: str | None = None,
    stem2: str | None = None,
    stem3: str | None = None,
    meaning: str | None = None,
) -> str:
    """Reconstruct headword from stem1 + ending (in-memory)."""
    if stem1 == "zzz":
        # Whitaker uses 'zzz' as a placeholder for a missing stem. Defective
        # paradigms (PERFDEF/impersonal verbs like memini/odi/novi, the
        # comparative-only adjectives deterior/ulterior, comparative adverbs,
        # the reflexive pronoun, a few pluralia tantum) have no first stem, so
        # the citation lemma must come from the first *real* stem — never from
        # the 'zzz' placeholder, which previously leaked lemmas like 'zzzo'.
        return _reconstruct_defective_headword(
            inflections, pos, decl_which, decl_var,
            stem2=stem2, stem3=stem3, gender=gender,
            verb_kind=verb_kind, meaning=meaning,
        )
    if pos == "N":
        if decl_which == 9:
            return stem1
        if decl_which == 2 and gender and gender not in ("C", "X"):
            ending = _find_ending_with_wildcard_gender(
                inflections, "N", decl_which, decl_var,
                gender=gender, stem_key=1)
            if ending is not None:
                return stem1 + ending
        ending = _find_ending(inflections, "N", decl_which, decl_var,
                              case_val="NOM", number="S", stem_key=1)
        if ending is not None:
            return stem1 + ending

    elif pos == "V":
        if verb_kind == "DEP":
            ending = _find_ending(inflections, "V", decl_which, decl_var,
                                  tense="PRES", voice="PASSIVE", mood="IND",
                                  person="1", number="S", stem_key=1)
            if ending is not None:
                return stem1 + ending
        ending = _find_ending(inflections, "V", decl_which, decl_var,
                              tense="PRES", voice="ACTIVE", mood="IND",
                              person="1", number="S", stem_key=1)
        if ending is not None:
            return stem1 + ending

    elif pos == "ADJ":
        if decl_which == 9:
            return stem1
        prefer_nonempty = (decl_which == 3 and decl_var == 2)
        for g in ("M", "C", "X"):
            ending = _find_ending(inflections, "ADJ", decl_which, decl_var,
                                  case_val="NOM", number="S", gender=g,
                                  comparison="POS", stem_key=1)
            if ending is not None:
                if prefer_nonempty and ending == "":
                    continue
                return stem1 + ending
        ending = _find_ending(inflections, "ADJ", decl_which, decl_var,
                              case_val="NOM", number="S",
                              comparison="POS", stem_key=1)
        if ending is not None:
            return stem1 + ending

    elif pos in ("PRON", "PACK"):
        for num, g in [("S", "M"), ("S", "C"), ("P", "C")]:
            matches = [
                inf for inf in inflections
                if inf["pos"] == "PRON"
                and inf["decl_which"] == decl_which
                and inf["decl_var"] == decl_var
                and inf["case_val"] == "NOM"
                and inf["number"] == num
                and inf["gender"] == g
                and inf["stem_key"] == 1
                and inf.get("freq", "A") in ("A", "B", "C")
            ]
            if matches:
                matches.sort(key=lambda x: (len(x["ending"]), x.get("freq", "A")))
                return stem1 + matches[0]["ending"]

    elif pos == "NUM":
        exact_s = [
            inf for inf in inflections
            if inf["pos"] == "NUM"
            and inf["decl_which"] == decl_which
            and inf["decl_var"] == decl_var
            and inf["case_val"] == "NOM"
            and inf["number"] == "S"
            and inf["stem_key"] == 1
        ]
        if exact_s:
            return stem1 + exact_s[0]["ending"]
        exact_p = [
            inf for inf in inflections
            if inf["pos"] == "NUM"
            and inf["decl_which"] == decl_which
            and inf["decl_var"] == decl_var
            and inf["case_val"] == "NOM"
            and inf["number"] == "P"
            and inf["stem_key"] == 1
            and inf.get("gender") in ("C", "M")
        ]
        if exact_p:
            return stem1 + exact_p[0]["ending"]
        return stem1

    elif pos in ("ADV", "PREP", "CONJ", "INTERJ"):
        return stem1

    return stem1


def _find_ending_with_wildcard_gender(
    inflections: list[dict],
    pos: str,
    decl_which: int,
    decl_var: int,
    *,
    gender: str,
    stem_key: int = 1,
) -> str | None:
    """Find NOM.S ending matching gender OR gender=X (wildcard)."""
    matches = [
        inf for inf in inflections
        if inf["pos"] == pos
        and (inf["decl_which"] == decl_which or inf["decl_which"] == 0)
        and (inf["decl_var"] == decl_var or inf["decl_var"] == 0)
        and inf["case_val"] == "NOM"
        and inf["number"] == "S"
        and inf["stem_key"] == stem_key
        and inf.get("gender") in (gender, "X")
        and inf.get("freq", "A") in ("A", "B", "C")
    ]
    if not matches:
        return None
    # Prefer exact gender match over wildcard
    matches.sort(key=lambda x: (0 if x.get("gender") == gender else 1,
                                 x.get("freq", "A")))
    return matches[0]["ending"]


def _find_ending(
    inflections: list[dict],
    pos: str,
    decl_which: int,
    decl_var: int | None,
    stem_key: int = 1,
    **conditions: str,
) -> str | None:
    """Find inflection ending with progressively broader matching."""
    def matches_conditions(inf: dict) -> bool:
        if inf["pos"] != pos or inf["stem_key"] != stem_key:
            return False
        for col, val in conditions.items():
            if inf.get(col) != val:
                return False
        if inf.get("freq", "A") not in ("A", "B", "C"):
            return False
        return True

    # Strategy 1: exact (decl_which, decl_var or 0)
    if decl_var is not None:
        s1 = [
            inf for inf in inflections
            if matches_conditions(inf)
            and inf["decl_which"] == decl_which
            and (inf["decl_var"] == decl_var or inf["decl_var"] == 0)
        ]
        if s1:
            s1.sort(key=lambda x: x.get("freq", "A"))
            return s1[0]["ending"]

    # Strategy 2: any decl_var for this decl_which
    s2 = [
        inf for inf in inflections
        if matches_conditions(inf)
        and inf["decl_which"] == decl_which
    ]
    if s2:
        s2.sort(key=lambda x: x.get("freq", "A"))
        return s2[0]["ending"]

    # Strategy 3: any decl_which
    s3 = [inf for inf in inflections if matches_conditions(inf)]
    if s3:
        s3.sort(key=lambda x: x.get("freq", "A"))
        return s3[0]["ending"]

    return None


# ---------------------------------------------------------------------------
# Pluralia tantum (in-memory, replaces align/pluralia.py SQL)
# ---------------------------------------------------------------------------

def _build_plural_mappings(
    entries: list[dict],
    inflections: list[dict],
    headwords: dict[int, tuple[str, str]],
) -> dict[str, str]:
    """Build singular→plural mappings for pluralia tantum nouns."""
    mappings: dict[str, str] = {}

    for entry in entries:
        if entry["pos"] != "N":
            continue
        meaning = entry.get("meaning") or ""
        if "(pl.)" not in meaning and "(pl)" not in meaning:
            continue

        entry_id = entry["id"]
        if entry_id not in headwords:
            continue

        _, singular = headwords[entry_id]
        stem2 = entry["stem2"] or entry["stem1"]
        if not stem2 or stem2 == "zzz":
            stem2 = entry["stem1"]

        gender = entry.get("gender")
        dw = entry["decl_which"]
        dv = entry["decl_var"]

        ending = None
        if gender and gender not in ("C", "X"):
            candidates = [
                inf for inf in inflections
                if inf["pos"] == "N"
                and (inf["decl_which"] == dw or inf["decl_which"] == 0)
                and (inf["decl_var"] == dv or inf["decl_var"] == 0)
                and inf["case_val"] == "NOM" and inf["number"] == "P"
                and inf["stem_key"] == 2 and inf.get("gender") == gender
                and inf.get("freq", "A") in ("A", "B", "C")
            ]
            if candidates:
                candidates.sort(key=lambda x: x.get("freq", "A"))
                ending = candidates[0]["ending"]

        if ending is None:
            candidates = [
                inf for inf in inflections
                if inf["pos"] == "N"
                and (inf["decl_which"] == dw or inf["decl_which"] == 0)
                and (inf["decl_var"] == dv or inf["decl_var"] == 0)
                and inf["case_val"] == "NOM" and inf["number"] == "P"
                and inf["stem_key"] == 2
                and inf.get("freq", "A") in ("A", "B", "C")
            ]
            if candidates:
                candidates.sort(key=lambda x: x.get("freq", "A"))
                ending = candidates[0]["ending"]

        if ending is not None:
            plural = normalize_latin(stem2 + ending)
            if plural != singular:
                mappings[singular] = plural

    return mappings


# ---------------------------------------------------------------------------
# Export: in-memory dicts → JSON files
# ---------------------------------------------------------------------------

def _analyzer_payload(
    entries: list[dict],
    inflections: list[dict],
    uniques: list[dict],
    addons: list[dict],
    headwords: dict[int, tuple[str, str]],
    plural_mappings: dict[str, str],
) -> dict:
    """Build the analyzer's in-memory payload from parsed WW data.

    Returns the exact dict :func:`_export_analyzer` serializes to
    ``analyzer.json`` — the six keys ``Analyzer.from_json`` reads
    (``inflections``, ``uniques``, ``tackons``, ``entries``, ``headwords``,
    ``plural_mappings``). Field subsetting and the ``ending``/``form``
    lowercasing happen here so :class:`~latincy_lexicon.analyzer.Analyzer` can
    index directly. Shared by :func:`_export_analyzer` (JSON dump) and
    :func:`build_analyzer` (direct in-memory construction) so both paths stay
    byte-for-byte identical.
    """
    # Strip fields the analyzer doesn't need from inflections.
    # Lowercase `ending` here so Analyzer._build_caches can index directly
    # without per-row .lower() calls at load time.
    inf_out = []
    for inf in inflections:
        row = {
            k: inf[k] for k in (
                "pos", "decl_which", "decl_var", "stem_key", "ending",
                "case_val", "number", "gender", "tense", "voice", "mood",
                "person", "comparison", "numeral_sort", "age", "freq",
            ) if k in inf
        }
        if "ending" in row and row["ending"]:
            row["ending"] = row["ending"].lower()
        inf_out.append(row)

    # Strip fields from uniques. Lowercase `form` for same reason as above.
    uni_out = []
    for u in uniques:
        row = {
            k: u[k] for k in (
                "form", "pos", "decl_which", "decl_var",
                "case_val", "number", "gender", "tense", "voice", "mood",
                "person", "comparison", "meaning",
            ) if k in u
        }
        if "form" in row and row["form"]:
            row["form"] = row["form"].lower()
        uni_out.append(row)

    tackons = sorted(
        [a["fix"].lower() for a in addons if a["addon_type"] == "TACKON"],
        key=len, reverse=True,
    )

    # Entries for analyzer (subset of fields)
    ent_out = []
    for e in entries:
        ent_out.append({
            k: e[k] for k in (
                "id", "stem1", "stem2", "stem3", "stem4",
                "pos", "decl_which", "decl_var",
                "gender", "noun_kind", "verb_kind", "pronoun_kind",
                "comparison", "numeral_sort",
                "age", "area", "geo", "freq", "source", "meaning",
            ) if k in e
        })

    # Headwords: entry_id → normalized
    hw_out = {str(eid): norm for eid, (_, norm) in headwords.items()}

    return {
        "inflections": inf_out,
        "uniques": uni_out,
        "tackons": tackons,
        "entries": ent_out,
        "headwords": hw_out,
        "plural_mappings": plural_mappings,
    }


def _export_analyzer(
    entries: list[dict],
    inflections: list[dict],
    uniques: list[dict],
    addons: list[dict],
    headwords: dict[int, tuple[str, str]],
    plural_mappings: dict[str, str],
    output_path: Path,
) -> int:
    """Write analyzer.json from in-memory data."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = _analyzer_payload(
        entries, inflections, uniques, addons, headwords, plural_mappings
    )
    with open(output_path, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    return len(entries)


def _clean_glosses(
    meaning: str,
) -> tuple[list[str], list[str], Optional[list[str]]]:
    """Split a DICTLINE meaning into clean glosses + source refs + original.

    Pipeline: split on ``;`` (paren/bracket-aware, with leading-artifact
    cleaning) → pull bibliographic citations into ``source_refs`` → strip
    trailing syntactic/cross-reference usage notes. Glosses that reduce to
    nothing (pure citation) are dropped. Shared by the main-entry and addon
    builders so both paths clean identically.

    Returns ``(glosses, source_refs, gloss_orig)`` where ``gloss_orig`` is the
    verbatim original split (``clean=False``) when our cleaning changed the
    glosses, else ``None`` — keeping the unaltered WW senses accessible in the
    dataset without bloating unchanged entries.
    """
    original = split_glosses(meaning, clean=False)
    glosses: list[str] = []
    source_refs: list[str] = []
    for raw_gloss in split_glosses(meaning):
        clean, srcs = extract_sources(raw_gloss)
        clean = strip_usage_note(clean)
        if clean:
            glosses.append(clean)
        for s in srcs:
            if s not in source_refs:
                source_refs.append(s)
    gloss_orig = original if original != glosses else None
    return glosses, source_refs, gloss_orig


def _dedup_rank(entry: dict) -> tuple[int, int]:
    """Authority rank for dedup tiebreaking: (source priority, frequency).

    Source dominates (classical dictionaries outrank Whitaker overlays); when
    two duplicates share a source, the more frequent one wins so the canonical
    homograph beats a rarer stub with identical (headword, pos, glosses).
    """
    return (
        _SOURCE_PRIORITY.get(entry.get("source", "X"), 0),
        _FREQ_PRIORITY.get(entry.get("freq", "X"), 0),
    )


def _build_lexicon_dict(
    entries: list[dict],
    addons: list[dict],
    headwords: dict[int, tuple[str, str]],
    plural_mappings: dict[str, str],
) -> dict[str, list[dict]]:
    """Build the lexicon dict from in-memory data (no disk I/O).

    Without alignment data, all entries are keyed by normalized headword
    (match_type='self'). This is the no-external-dependency path.
    """
    from latincy_lexicon.enums import WORDS_TO_UD_POS

    lexicon: dict[str, list[dict]] = {}

    # Group entries by normalized headword
    for entry in entries:
        entry_id = entry["id"]
        if entry_id not in headwords:
            continue

        hw, normalized = headwords[entry_id]
        stems = [entry["stem1"], entry["stem2"], entry["stem3"], entry["stem4"]]
        principal_parts = [s for s in stems if s and s != "zzz"]
        # Keep the display citation case-consistent with the (lowercased) headword
        # for WW-capitalized common nouns like deus: render "deus, dei", not
        # "deus, Dei". Only the exported display list is lowercased — the entry's
        # underlying stems stay capitalized so the form generator can still
        # recover the proper-sense variant (see _LOWERCASE_DISPLAY_HEADWORDS).
        if (entry["stem1"], entry["pos"]) in _LOWERCASE_DISPLAY_HEADWORDS:
            principal_parts = [p[:1].lower() + p[1:] for p in principal_parts]

        glosses, source_refs, gloss_orig = _clean_glosses(entry["meaning"])

        lex_entry: dict = {
            # Preserve the reconstructed case for display: common-noun stems are
            # lowercase in DICTLINE (so hw is already lowercase), while proper
            # nouns/adjectives keep their capital (Juno, Roma, Latinus, Sequana).
            # Force-lowercasing here made the headword ('juno') disagree with its
            # own case-preserving principal_parts ('Juno, Junonis'). Lookup is
            # unaffected: the dict is keyed by `normalized` (always case-folded).
            "headword": hw,
            "normalized_headword": normalized,
            "pos": entry["pos"],
            "decl_which": entry["decl_which"],
            "decl_var": entry["decl_var"],
            "ud_pos": sorted(WORDS_TO_UD_POS.get(entry["pos"], set())),
            "glosses": glosses,
            "principal_parts": principal_parts,
            "age": entry["age"],
            "freq": entry["freq"],
            "area": entry["area"],
            "geo": entry["geo"],
            "source": entry["source"],
            "match_type": "self",
        }

        for field in ("gender", "verb_kind", "noun_kind", "comparison",
                      "pronoun_kind", "numeral_sort"):
            val = entry.get(field)
            if val and val != "X":
                lex_entry[field] = val

        if source_refs:
            lex_entry["source_refs"] = source_refs

        if gloss_orig is not None:
            lex_entry["gloss_orig"] = gloss_orig

        # Whitaker 'zzz' in stem1 marks a defective paradigm (no first stem):
        # perfect-only verbs (memini/odi/novi) and comparative-only adjectives
        # (deterior/ulterior). The citation builder needs this to avoid
        # fabricating a present infinitive from the perfect stem.
        if entry.get("stem1") == "zzz":
            lex_entry["defective"] = True

        if entry.get("_overrides"):
            lex_entry["_overrides"] = entry["_overrides"]

        # Dedup by (headword, pos, glosses). When DICTLINE ships two entries
        # that agree on those fields but disagree on stems — e.g. the Oxford
        # entry for `cano` (stems can/can/cecin/cant) vs. the Whitaker-custom
        # entry (stems can/can/can/canit) — prefer whichever has the more
        # authoritative source, and break source ties by frequency so the
        # canonical high-frequency homograph wins over a rarer duplicate (e.g.
        # `pario` freq-A peperi/partum over freq-E parire/paritum, same source).
        # Without this, whichever entry DICTLINE lists first wins, and we've
        # seen the bad one win for reduplicated-perfect verbs like cano/pario.
        existing = lexicon.setdefault(normalized, [])
        dup_idx = next(
            (
                i for i, e in enumerate(existing)
                if e["headword"] == lex_entry["headword"]
                and e["pos"] == lex_entry["pos"]
                and e["glosses"] == lex_entry["glosses"]
            ),
            None,
        )
        if dup_idx is None:
            existing.append(lex_entry)
        elif _dedup_rank(lex_entry) > _dedup_rank(existing[dup_idx]):
            existing[dup_idx] = lex_entry

    # Pluralia tantum
    from latincy_lexicon.align.pluralia import apply_plural_mappings
    apply_plural_mappings(plural_mappings, lexicon)

    # Addons (tackons, prefixes, suffixes)
    for a in addons:
        fix = a["fix"].lower().replace("v", "u").replace("j", "i")
        addon_type = a["addon_type"]

        if addon_type == "TACKON":
            ud_pos = ["CCONJ", "PART", "SCONJ"]
        else:
            ud_pos = ["X"]

        addon_glosses, addon_sources, addon_orig = _clean_glosses(a["meaning"])
        addon_entry = {
            "headword": a["fix"].lower(),
            "normalized_headword": fix,
            "pos": addon_type,
            "ud_pos": ud_pos,
            "glosses": addon_glosses,
            "principal_parts": [],
            "age": "X", "freq": "X", "area": "X", "geo": "X", "source": "X",
            "match_type": "addon",
            "addon_type": addon_type,
        }
        if addon_sources:
            addon_entry["source_refs"] = addon_sources
        if addon_orig is not None:
            addon_entry["gloss_orig"] = addon_orig
        if a.get("connect"):
            addon_entry["connect"] = a["connect"]
        lexicon.setdefault(fix, []).append(addon_entry)

    return lexicon


def _export_lexicon(
    entries: list[dict],
    addons: list[dict],
    headwords: dict[int, tuple[str, str]],
    plural_mappings: dict[str, str],
    output_path: Path,
) -> int:
    """Write lexicon.json to disk; returns the number of lexicon keys."""
    lexicon = _build_lexicon_dict(entries, addons, headwords, plural_mappings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(lexicon, f, ensure_ascii=False, indent=1)
    return len(lexicon)


# ---------------------------------------------------------------------------
# Public API: full build pipeline
# ---------------------------------------------------------------------------

def _prepare(vendor: str | Path | None = None) -> dict:
    """Parse → patch → headwords → plural mappings (no export).

    Shared by :func:`build` (which also writes the analyzer + lexicon JSON) and
    :func:`build_lexicon` (which returns the lexicon dict in memory). Returns the
    in-memory data structures keyed by name.
    """
    # 1. Parse
    parsed = _parse_all(vendor)

    # 2. Convert to dicts with IDs
    entries = [_entry_to_dict(e, i + 1) for i, e in enumerate(parsed["entries"])]
    inflections = [_inflection_to_dict(inf) for inf in parsed["inflections"]]
    uniques = [_unique_to_dict(u) for u in parsed["uniques"]]
    addons = [_addon_to_dict(a) for a in parsed["addons"]]

    next_id = len(entries) + 1

    # 3. Apply patches
    headwords: dict[int, tuple[str, str]] = {}
    next_id = _apply_patches(entries, inflections, headwords, next_id)

    # 4. Build headwords
    hw = _build_headwords(entries, inflections)
    # Merge patch headwords (sum) with generated ones
    hw.update(headwords)
    headwords = hw

    # 5. Plural mappings
    plural_mappings = _build_plural_mappings(entries, inflections, headwords)

    return {
        "entries": entries,
        "inflections": inflections,
        "uniques": uniques,
        "addons": addons,
        "headwords": headwords,
        "plural_mappings": plural_mappings,
    }


def _cache_dir() -> Path:
    """User cache directory for the built lexicon (dependency-free, XDG-style).

    Honors ``LATINCY_LEXICON_CACHE_DIR`` (explicit override; also used to isolate
    tests), then ``XDG_CACHE_HOME``, else ``~/.cache`` — never writes into
    site-packages.
    """
    override = os.environ.get("LATINCY_LEXICON_CACHE_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "latincy-lexicon"


def _lexicon_cache_key(base: Path) -> str:
    """Cache key = package version + a hash of the DICTLINE the build reads.

    Version discriminates releases (code + bundled data move together); the
    DICTLINE hash distinguishes bundled vs. vendor data and catches local edits.
    """
    from latincy_lexicon import __version__

    digest = hashlib.sha256((base / "DICTLINE.GEN").read_bytes()).hexdigest()[:16]
    return f"{__version__}-{digest}"


def _read_json_cache(cache_file: Path) -> Optional[dict]:
    """Best-effort cache read; ``None`` on any miss or corruption."""
    try:
        with open(cache_file) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_json_cache(cache_file: Path, payload: dict) -> None:
    """Best-effort cache write; a read-only cache dir must not break builds."""
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(payload, f, ensure_ascii=False)
    except OSError:
        pass


def _lexicon_cache_file(base: Path) -> Path:
    return _cache_dir() / f"lexicon-{_lexicon_cache_key(base)}.json"


def _analyzer_cache_file(base: Path) -> Path:
    return _cache_dir() / f"analyzer-{_lexicon_cache_key(base)}.json"


def build_lexicon(
    vendor: str | Path | None = None, *, use_cache: bool = True
) -> dict[str, list[dict]]:
    """Build the lexicon in memory (no analyzer), with a disk cache.

    Returns the same dict :func:`build` writes to ``lexicon.json`` — keyed by
    normalized headword, each value a list of entry dicts (glosses, principal
    parts, POS, metadata). Uses the bundled DICTLINE by default; the
    defective-verb (``zzz``) fix is applied, so no key or citation form contains
    the placeholder. This is the path downstream consumers (latincy-vocab, the
    ``whitakers_words`` component) use to get glosses + citation forms without a
    prebuilt ``lexicon.json`` on disk.

    The full build is ~5s, so the result is cached under :func:`_cache_dir`
    keyed by :func:`_lexicon_cache_key`. Pass ``use_cache=False`` to force a
    rebuild and skip the cache entirely. Cache read/write failures degrade to a
    plain in-memory build rather than raising.

    If both a lexicon and an analyzer are needed, prefer
    :func:`build_lexicon_and_analyzer` — it shares the ~5s :func:`_prepare` parse
    across both instead of paying it twice.
    """
    base = data_dir() if vendor is None else Path(vendor)
    cache_file = _lexicon_cache_file(base)

    if use_cache:
        cached = _read_json_cache(cache_file)
        if cached is not None:
            return cached

    p = _prepare(vendor)
    lexicon = _build_lexicon_dict(
        p["entries"], p["addons"], p["headwords"], p["plural_mappings"]
    )

    if use_cache:
        _write_json_cache(cache_file, lexicon)

    return lexicon


def _analyzer_from_payload(
    payload: dict, macron_path: str | Path | None = None
) -> "Analyzer":
    from latincy_lexicon.analyzer import Analyzer

    return Analyzer(
        inflections=payload["inflections"],
        uniques=payload["uniques"],
        tackons=payload["tackons"],
        entries=payload["entries"],
        headwords={int(k): v for k, v in payload["headwords"].items()},
        plural_mappings=payload["plural_mappings"],
        macron_path=macron_path,
    )


def build_analyzer(
    vendor: str | Path | None = None, *, use_cache: bool = True,
    macron_path: str | Path | None = None,
) -> "Analyzer":
    """Build the morphological analyzer in memory, with a disk cache.

    Returns a ready-to-use :class:`~latincy_lexicon.analyzer.Analyzer` built from
    the same payload :func:`build` writes to ``analyzer.json`` — no 15 MB
    prebuilt JSON on disk required. Uses the bundled WW data files by default
    (the ``zzz`` defective-verb fix is applied upstream in :func:`_prepare`).
    This is the path the ``whitakers_words`` component uses, under
    ``use_bundled_analyzer=True``, to recover glosses on forms the upstream
    lemmatizer misses: the lexicon is lemma-keyed, and the analyzer is the
    form → headword engine that lets the component look an entry up from the
    surface form when the lemma is wrong.

    ``macron_path`` is forwarded to the constructed :class:`Analyzer` exactly as
    :meth:`Analyzer.from_json` forwards it — pass it here so a macronized-form
    filter still applies when using the bundled (rather than an explicit
    ``analyzer_path``) analyzer.

    The full parse is ~5s, so the payload is cached under :func:`_cache_dir`
    (``analyzer-`` prefix) keyed by :func:`_lexicon_cache_key`. On a warm cache
    the payload loads without touching :func:`_prepare`. Pass ``use_cache=False``
    to force a rebuild. Cache read/write failures degrade to a plain in-memory
    build rather than raising.

    If a lexicon is also needed, prefer :func:`build_lexicon_and_analyzer` — it
    shares the ~5s :func:`_prepare` parse across both instead of paying it twice.
    """
    base = data_dir() if vendor is None else Path(vendor)
    cache_file = _analyzer_cache_file(base)

    payload = _read_json_cache(cache_file) if use_cache else None

    if payload is None:
        p = _prepare(vendor)
        payload = _analyzer_payload(
            p["entries"], p["inflections"], p["uniques"], p["addons"],
            p["headwords"], p["plural_mappings"],
        )
        if use_cache:
            _write_json_cache(cache_file, payload)

    return _analyzer_from_payload(payload, macron_path=macron_path)


def build_lexicon_and_analyzer(
    vendor: str | Path | None = None, *, use_cache: bool = True,
    macron_path: str | Path | None = None,
) -> tuple[dict[str, list[dict]], "Analyzer"]:
    """Build both the bundled lexicon and analyzer, sharing one cold-cache parse.

    Equivalent to calling :func:`build_lexicon` and :func:`build_analyzer`
    separately, except that when *neither* has a warm cache, the ~5s
    :func:`_prepare` parse of the bundled WW data runs once instead of twice —
    this is the path ``whitakers_words`` uses when both ``use_bundled_lexicon``
    and ``use_bundled_analyzer`` are on (the zero-config default). Each result
    is still cached to its own file exactly as the standalone builders do, so a
    warm cache for either resource is used as-is, and a later standalone
    :func:`build_lexicon`/:func:`build_analyzer` call also hits the shared cache.
    """
    base = data_dir() if vendor is None else Path(vendor)
    lexicon_cache_file = _lexicon_cache_file(base)
    analyzer_cache_file = _analyzer_cache_file(base)

    lexicon = _read_json_cache(lexicon_cache_file) if use_cache else None
    analyzer_payload = _read_json_cache(analyzer_cache_file) if use_cache else None

    if lexicon is None or analyzer_payload is None:
        p = _prepare(vendor)
        if lexicon is None:
            lexicon = _build_lexicon_dict(
                p["entries"], p["addons"], p["headwords"], p["plural_mappings"]
            )
            if use_cache:
                _write_json_cache(lexicon_cache_file, lexicon)
        if analyzer_payload is None:
            analyzer_payload = _analyzer_payload(
                p["entries"], p["inflections"], p["uniques"], p["addons"],
                p["headwords"], p["plural_mappings"],
            )
            if use_cache:
                _write_json_cache(analyzer_cache_file, analyzer_payload)

    analyzer = _analyzer_from_payload(analyzer_payload, macron_path=macron_path)
    return lexicon, analyzer


def build(
    output_dir: str | Path = "data/json",
    vendor: str | Path | None = None,
) -> dict[str, int]:
    """Run the full build pipeline: parse → patch → headwords → JSON.

    Args:
        output_dir: Directory for output JSON files.
        vendor: Optional path to WW data files. Defaults to bundled package data.

    Returns:
        Dict with counts of entries, inflections, headwords, etc.
    """
    output_dir = Path(output_dir)

    p = _prepare(vendor)
    entries = p["entries"]
    inflections = p["inflections"]
    uniques = p["uniques"]
    addons = p["addons"]
    headwords = p["headwords"]
    plural_mappings = p["plural_mappings"]

    # 6. Export
    analyzer_path = output_dir / "analyzer.json"
    lexicon_path = output_dir / "lexicon.json"

    n_entries = _export_analyzer(
        entries, inflections, uniques, addons,
        headwords, plural_mappings, analyzer_path,
    )
    n_lexicon = _export_lexicon(
        entries, addons, headwords, plural_mappings, lexicon_path,
    )

    return {
        "entries": n_entries,
        "inflections": len(inflections),
        "uniques": len(uniques),
        "addons": len(addons),
        "headwords": len(headwords),
        "lexicon_keys": n_lexicon,
        "analyzer_path": str(analyzer_path),
        "lexicon_path": str(lexicon_path),
    }
