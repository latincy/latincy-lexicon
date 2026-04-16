"""Rule-based morphological analyzer replicating Whitaker's Words logic.

Given an inflected Latin form, decompose it into all possible
stem + ending combinations, look up stems in DICTLINE, and return
full grammatical parses.

This is the core Words engine: INFLECTS × DICTLINE matching.

At runtime, loads from JSON (no sqlite3 dependency). The JSON is
exported from the SQLite build database by the CLI ``export-analyzer``
command.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


from latincy_lexicon.align.normalize import normalize_latin


@dataclass
class Parse:
    """A single morphological parse of a Latin form."""
    form: str
    lemma: str
    headword: str
    pos: str
    # Declension/conjugation
    decl_which: int = 0
    decl_var: int = 0
    # Grammatical features
    case: str = "X"
    number: str = "X"
    gender: str = "X"
    tense: str = "X"
    voice: str = "X"
    mood: str = "X"
    person: str = "0"
    comparison: str = "X"
    # Lexical info
    verb_kind: str = "X"
    noun_kind: str = "X"
    age: str = "X"
    freq: str = "X"
    meaning: str = ""
    # How we got here
    stem_key: int = 0
    ending: str = ""
    stem_used: str = ""

    def to_dict(self) -> dict:
        d = {
            "form": self.form,
            "lemma": self.lemma,
            "headword": self.headword,
            "pos": self.pos,
            "decl": f"{self.decl_which}.{self.decl_var}",
            "meaning": self.meaning,
            "stem": self.stem_used,
            "ending": self.ending,
        }
        # Only include non-default grammatical features
        if self.case != "X":
            d["case"] = self.case
        if self.number != "X":
            d["number"] = self.number
        if self.gender != "X":
            d["gender"] = self.gender
        if self.tense != "X":
            d["tense"] = self.tense
        if self.voice != "X":
            d["voice"] = self.voice
        if self.mood != "X":
            d["mood"] = self.mood
        if self.person != "0":
            d["person"] = self.person
        if self.comparison != "X":
            d["comparison"] = self.comparison
        if self.verb_kind != "X":
            d["verb_kind"] = self.verb_kind
        if self.noun_kind != "X":
            d["noun_kind"] = self.noun_kind
        d["age"] = self.age
        d["freq"] = self.freq
        return d


class Analyzer:
    """Rule-based Latin morphological analyzer using Whitaker's Words data.

    Replicates the core Words algorithm:
    1. For each possible split point in the form, extract (candidate_stem, candidate_ending)
    2. Look up candidate_ending in INFLECTS to get POS + grammatical features + stem_key
    3. Look up candidate_stem in DICTLINE where POS and decl match, using the right stem slot
    4. If match found, emit a Parse

    Also handles:
    - Unique/irregular forms (UNIQUES table)
    - Enclitic stripping (-que, -ne, -ve)

    Load from JSON (preferred, no sqlite3 dependency)::

        analyzer = Analyzer.from_json("data/json/analyzer.json")

    Load from SQLite (build-time only)::

        import sqlite3
        conn = sqlite3.connect("data/db/whitakers.db")
        conn.row_factory = sqlite3.Row
        analyzer = Analyzer.from_db(conn)
    """

    def __init__(
        self,
        inflections: list[dict],
        uniques: list[dict],
        tackons: list[str],
        entries: list[dict],
        headwords: dict[int, str],
        plural_mappings: dict[str, str],
    ) -> None:
        self.plural_to_singular: dict[str, str] = {v: k for k, v in plural_mappings.items()}
        self.singular_to_plural: dict[str, str] = plural_mappings
        self._build_caches(inflections, uniques, tackons, entries, headwords)

    @classmethod
    def from_json(cls, path: str | Path) -> "Analyzer":
        """Load analyzer from a JSON file (no sqlite3 dependency)."""
        with open(path) as f:
            data = json.load(f)
        headwords = {int(k): v for k, v in data["headwords"].items()}
        return cls(
            inflections=data["inflections"],
            uniques=data["uniques"],
            tackons=data["tackons"],
            entries=data["entries"],
            headwords=headwords,
            plural_mappings=data["plural_mappings"],
        )

    @classmethod
    def from_db(cls, conn) -> "Analyzer":
        """Load analyzer from a SQLite database (build-time)."""
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

        from latincy_lexicon.align.pluralia import build_plural_mappings
        plural_mappings = build_plural_mappings(conn)

        return cls(inflections, uniques, tackons, entries, headwords, plural_mappings)

    def _build_caches(
        self,
        inflections: list[dict],
        uniques: list[dict],
        tackons: list[str],
        entries: list[dict],
        headwords: dict[int, str],
    ) -> None:
        """Build in-memory lookup structures from raw data."""
        # Cache: ending → list of inflection dicts.
        # `ending` is lowercased at the build-time trust boundary
        # (build.py::_export_analyzer, db/loader.py consumes pre-lowercased
        # parser output), so no per-row .lower() is needed here.
        self._endings: dict[str, list[dict]] = {}
        for r in inflections:
            self._endings.setdefault(r["ending"], []).append(r)

        if "" not in self._endings:
            self._endings[""] = []

        # Cache: form → list of unique dicts. `form` is pre-lowercased
        # for the same reason as `ending` above.
        self._uniques: dict[str, list[dict]] = {}
        for r in uniques:
            self._uniques.setdefault(r["form"], []).append(r)

        # Tackons for enclitic stripping
        self._tackons = tackons

        # Stem index: (pos, decl_which, decl_var, stem_key) → stem_value → list[entry]
        self._stems: dict[tuple, dict[str, list[dict]]] = {}
        for entry in entries:
            pos = entry["pos"]
            dw = entry["decl_which"]
            dv = entry["decl_var"]
            stems = {1: entry["stem1"], 2: entry["stem2"],
                     3: entry["stem3"], 4: entry["stem4"]}
            for sk, sv in stems.items():
                if sv and sv != "zzz":
                    sv_lower = sv.lower()
                    seen_keys: set[tuple] = set()
                    for p in self._pos_variants(pos, sk):
                        for d_which in (dw, 0):
                            for d_var in (dv, 0):
                                key = (p, d_which, d_var, sk)
                                if key not in seen_keys:
                                    seen_keys.add(key)
                                    self._stems.setdefault(key, {}).setdefault(sv_lower, []).append(entry)

        # Index empty-stem entries (V 5.1 sum/esse: stem2 is intentionally "")
        for entry in entries:
            if entry["pos"] == "V" and entry["decl_which"] == 5 and entry["stem2"] == "":
                for d_var in (entry["decl_var"], 0):
                    key = ("V", 5, d_var, 2)
                    self._stems.setdefault(key, {}).setdefault("", []).append(entry)

        # Headword cache: entry_id → normalized headword
        self._headwords = headwords

    def _lookup_stem(self, pos: str, dw: int, dv: int, sk: int, stem: str) -> list[dict]:
        """Look up a stem, trying multiple key combinations and v/u variants."""
        # Generate v/u variants of the stem
        stem_variants = {stem}
        # Try replacing each 'u' with 'v' individually and all at once
        if "u" in stem:
            stem_variants.add(stem.replace("u", "v"))
        if "v" in stem:
            stem_variants.add(stem.replace("v", "u"))

        for sv in stem_variants:
            for d_var in (dv, 0):
                key = (pos, dw, d_var, sk)
                entries = self._stems.get(key, {}).get(sv, [])
                if entries:
                    return entries
        return []

    def lemmas_equivalent(self, lemma_a: str, lemma_b: str) -> bool:
        """Check if two lemmas refer to the same word, accounting for pluralia tantum.

        Handles cases like arma≈armum, castra≈castrum, divitiae≈divitia.
        """
        a = lemma_a.lower().replace("v", "u").replace("j", "i")
        b = lemma_b.lower().replace("v", "u").replace("j", "i")

        if a == b:
            return True

        # Check pluralia tantum: a is plural of b, or b is plural of a
        if self.singular_to_plural.get(a) == b:
            return True
        if self.singular_to_plural.get(b) == a:
            return True
        if self.plural_to_singular.get(a) == b:
            return True
        if self.plural_to_singular.get(b) == a:
            return True

        return False

    @staticmethod
    def _pos_variants(pos: str, stem_key: int) -> list[str]:
        """Return POS values to index a stem under.

        Verb entries (V) also need to be findable under VPAR and SUPINE
        for stem3/stem4 lookups, since those inflections use different POS codes.
        """
        variants = [pos]
        if pos == "V":
            if stem_key in (3, 4):
                variants.extend(["VPAR", "SUPINE"])
        return variants

    def analyze(self, form: str) -> list[Parse]:
        """Analyze a Latin form and return all possible parses.

        Args:
            form: An inflected Latin word (e.g., "fecerunt").

        Returns:
            List of Parse objects, sorted by frequency (most common first).
        """
        form_lower = form.lower()
        forms_to_try = [form_lower]

        parses: list[Parse] = []

        # 1. Check uniques first
        if form_lower in self._uniques:
            for u in self._uniques[form_lower]:
                parses.append(Parse(
                    form=form,
                    lemma=form_lower,
                    headword=form_lower,
                    pos=u["pos"],
                    case=u.get("case_val", "X"),
                    number=u.get("number", "X"),
                    gender=u.get("gender", "X"),
                    tense=u.get("tense", "X"),
                    voice=u.get("voice", "X"),
                    mood=u.get("mood", "X"),
                    person=u.get("person", "0"),
                    meaning=u.get("meaning", ""),
                ))

        # 2. Try all stem+ending splits
        parses.extend(self._try_splits(form, form_lower))

        # 3. Try after stripping enclitics
        for tackon in self._tackons:
            if form_lower.endswith(tackon) and len(form_lower) > len(tackon) + 1:
                base = form_lower[:-len(tackon)]
                parses.extend(self._try_splits(form, base))

        # Deduplicate and sort by frequency
        seen: set[tuple] = set()
        unique_parses: list[Parse] = []
        for p in parses:
            key = (p.lemma, p.pos, p.case, p.number, p.gender,
                   p.tense, p.voice, p.mood, p.person)
            if key not in seen:
                seen.add(key)
                unique_parses.append(p)

        # Sort: freq A > B > C > ... > X
        freq_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "X": 9}
        unique_parses.sort(key=lambda p: freq_order.get(p.freq, 8))

        return unique_parses

    def _try_splits(self, original_form: str, form_lower: str) -> list[Parse]:
        """Try all possible stem+ending splits of a form."""
        parses: list[Parse] = []

        # Try every split point: ending can be 0 to len(form) characters
        for i in range(len(form_lower), -1, -1):
            candidate_stem = form_lower[:i]
            candidate_ending = form_lower[i:]

            if not candidate_stem:
                # Empty stems only valid for V 5.1 (sum/esse)
                # Skip unless the full form is a known V 5.1 ending
                if not any(infl["pos"] == "V" and infl["decl_which"] == 5
                           for infl in self._endings.get(candidate_ending, [])):
                    continue

            # Look up the ending in inflections
            infl_matches = self._endings.get(candidate_ending, [])
            if not infl_matches and candidate_ending != "":
                continue

            # For empty ending, use indeclinable inflections
            if candidate_ending == "":
                infl_matches = self._endings.get("", [])

            for infl in infl_matches:
                pos = infl["pos"]
                dw = infl["decl_which"]
                dv = infl["decl_var"]
                sk = infl["stem_key"]

                # Look up stem in dict_entries, trying both u-space and v-space
                stem_entries = self._lookup_stem(pos, dw, dv, sk, candidate_stem)

                for entry in stem_entries:
                    lemma = self._headwords.get(entry["id"], candidate_stem)
                    headword = lemma

                    # For NUM ordinals (stem_key=2), reconstruct the ordinal
                    # lemma from stem2 instead of returning the cardinal headword.
                    # e.g. tres (stem2=terti) + us → tertius, not tres
                    if pos == "NUM" and sk == 2:
                        num_sort = infl.get("numeral_sort", "X")
                        if num_sort == "ORD":
                            lemma = normalize_latin(candidate_stem + "us")
                            headword = lemma
                        elif num_sort == "DIST":
                            lemma = normalize_latin(candidate_stem + "i")
                            headword = lemma

                    parses.append(Parse(
                        form=original_form,
                        lemma=lemma,
                        headword=headword,
                        pos=pos,
                        decl_which=dw,
                        decl_var=dv,
                        case=infl.get("case_val", "X"),
                        number=infl.get("number", "X"),
                        gender=infl.get("gender", "X") if pos != "V" else "X",
                        tense=infl.get("tense", "X"),
                        voice=infl.get("voice", "X"),
                        mood=infl.get("mood", "X"),
                        person=infl.get("person", "0"),
                        comparison=infl.get("comparison", "X"),
                        verb_kind=entry.get("verb_kind") or "X",
                        noun_kind=entry.get("noun_kind") or "X",
                        age=entry.get("freq", "X"),  # entry freq, not inflection freq
                        freq=entry.get("freq", "X"),
                        meaning=entry.get("meaning", ""),
                        stem_key=sk,
                        ending=candidate_ending,
                        stem_used=candidate_stem,
                    ))

        return parses
