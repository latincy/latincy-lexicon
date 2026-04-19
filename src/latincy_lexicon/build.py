"""In-memory build pipeline: raw WW data files → JSON, no SQLite.

Replaces the build-db → export chain with a single pass that parses
the bundled data files directly into dicts and writes JSON.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from latincy_lexicon.align.normalize import normalize_latin
from latincy_lexicon.glosses import split_glosses
from latincy_lexicon.models import DictEntry, Inflection


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
    return next_id


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
        )
        normalized = normalize_latin(hw)
        headwords[entry["id"]] = (hw, normalized)

    return headwords


def _reconstruct_headword(
    inflections: list[dict],
    stem1: str,
    pos: str,
    decl_which: int,
    decl_var: int,
    *,
    gender: str | None = None,
    verb_kind: str | None = None,
) -> str:
    """Reconstruct headword from stem1 + ending (in-memory)."""
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

    data = {
        "inflections": inf_out,
        "uniques": uni_out,
        "tackons": tackons,
        "entries": ent_out,
        "headwords": hw_out,
        "plural_mappings": plural_mappings,
    }

    with open(output_path, "w") as f:
        json.dump(data, f, ensure_ascii=False)

    return len(entries)


def _export_lexicon(
    entries: list[dict],
    addons: list[dict],
    headwords: dict[int, tuple[str, str]],
    plural_mappings: dict[str, str],
    output_path: Path,
) -> int:
    """Write lexicon.json from in-memory data.

    Without alignment data, all entries are keyed by normalized headword
    (match_type='self'). This is the no-external-dependency path.
    """
    from latincy_lexicon.enums import WORDS_TO_UD_POS

    output_path.parent.mkdir(parents=True, exist_ok=True)

    lexicon: dict[str, list[dict]] = {}

    # Group entries by normalized headword
    for entry in entries:
        entry_id = entry["id"]
        if entry_id not in headwords:
            continue

        hw, normalized = headwords[entry_id]
        stems = [entry["stem1"], entry["stem2"], entry["stem3"], entry["stem4"]]
        principal_parts = [s for s in stems if s and s != "zzz"]

        lex_entry: dict = {
            "headword": hw,
            "normalized_headword": normalized,
            "pos": entry["pos"],
            "ud_pos": sorted(WORDS_TO_UD_POS.get(entry["pos"], set())),
            "glosses": split_glosses(entry["meaning"]),
            "principal_parts": principal_parts,
            "age": entry["age"],
            "freq": entry["freq"],
            "area": entry["area"],
            "geo": entry["geo"],
            "source": entry["source"],
            "match_type": "self",
        }

        for field in ("gender", "verb_kind", "noun_kind", "comparison"):
            val = entry.get(field)
            if val and val != "X":
                lex_entry[field] = val

        # Avoid exact duplicates
        existing = lexicon.get(normalized, [])
        if not any(e["headword"] == lex_entry["headword"]
                   and e["pos"] == lex_entry["pos"]
                   and e["glosses"] == lex_entry["glosses"]
                   for e in existing):
            lexicon.setdefault(normalized, []).append(lex_entry)

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

        addon_entry = {
            "headword": a["fix"],
            "normalized_headword": fix,
            "pos": addon_type,
            "ud_pos": ud_pos,
            "glosses": split_glosses(a["meaning"]),
            "principal_parts": [],
            "age": "X", "freq": "X", "area": "X", "geo": "X", "source": "X",
            "match_type": "addon",
            "addon_type": addon_type,
        }
        if a.get("connect"):
            addon_entry["connect"] = a["connect"]
        lexicon.setdefault(fix, []).append(addon_entry)

    with open(output_path, "w") as f:
        json.dump(lexicon, f, ensure_ascii=False, indent=1)

    return len(lexicon)


# ---------------------------------------------------------------------------
# Public API: full build pipeline
# ---------------------------------------------------------------------------

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
