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
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


from latincy_lexicon.align.normalize import normalize_latin


_MACRON_CHARS = frozenset("āēīōūȳĀĒĪŌŪȲ")


def _has_macrons(s: str) -> bool:
    return any(c in _MACRON_CHARS for c in s)


def _strip_macrons(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s)
    return unicodedata.normalize("NFC", "".join(
        c for c in nfd if unicodedata.category(c) != "Mn"
    ))


def _parse_ud_morph(morph: str) -> dict[str, str]:
    return dict(p.split("=", 1) for p in morph.split("|")) if morph else {}


# Mapping from Parse attribute name → (UD key, {WW value → UD value})
_WW_UD: dict[str, tuple[str, dict[str, str]]] = {
    "case":   ("Case",   {"NOM": "Nom", "GEN": "Gen", "DAT": "Dat",
                          "ACC": "Acc", "ABL": "Abl", "VOC": "Voc", "LOC": "Loc"}),
    "number": ("Number", {"S": "Sing", "P": "Plur"}),
    "gender": ("Gender", {"M": "Masc", "F": "Fem", "N": "Neut", "C": "Com"}),
    "mood":   ("Mood",   {"IND": "Ind", "SUB": "Sub", "IMP": "Imp", "INF": "Inf"}),
    "person": ("Person", {"1": "1", "2": "2", "3": "3"}),
    "voice":  ("Voice",  {"ACTIVE": "Act", "PASSIVE": "Pass"}),
    "tense":  ("Tense",  {"PRES": "Pres", "IMPF": "Past", "FUT": "Fut",
                          "PLUP": "Pqp", "FUTP": "Fut"}),
}


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
        macron_path: str | Path | None = None,
    ) -> None:
        self.plural_to_singular: dict[str, str] = {v: k for k, v in plural_mappings.items()}
        self.singular_to_plural: dict[str, str] = plural_mappings
        self._macron_index: dict[str, list[dict]] | None = None
        if macron_path is not None:
            with open(macron_path) as f:
                self._macron_index = json.load(f)
        self._build_caches(inflections, uniques, tackons, entries, headwords)

    @classmethod
    def from_json(cls, path: str | Path, macron_path: str | Path | None = None) -> "Analyzer":
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
            macron_path=macron_path,
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
            form: An inflected Latin word, with or without macrons (e.g., "puellā").
                  If macrons are present and a macron index is loaded, results are
                  post-filtered to the features indicated by the macronized spelling.

        Returns:
            List of Parse objects, sorted by frequency (most common first).
        """
        has_macr = _has_macrons(form)
        form_base = _strip_macrons(form) if has_macr else form
        form_lower = form_base.lower()

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

        if has_macr and self._macron_index is not None:
            unique_parses = self._filter_by_macrons(unique_parses, form)

        return unique_parses

    def _filter_by_macrons(self, parses: list[Parse], macronized_form: str) -> list[Parse]:
        """Post-filter parses using kaikki macron index features.

        Looks up the macronized form, intersects UD features across all kaikki
        candidates (handles genuinely ambiguous macronized forms), and retains only
        parses consistent with the intersection. Falls back to returning all parses
        if the form is not in the index or the filter would eliminate everything.
        """
        candidates = self._macron_index.get(macronized_form)  # type: ignore[union-attr]
        if not candidates:
            return parses

        shared = _parse_ud_morph(candidates[0]["morph"])
        for cand in candidates[1:]:
            feats = _parse_ud_morph(cand["morph"])
            shared = {k: v for k, v in shared.items() if feats.get(k) == v}

        if not shared:
            return parses

        filtered = [p for p in parses if self._parse_matches_ud(p, shared)]
        return filtered if filtered else parses

    def _parse_matches_ud(self, p: Parse, ud_feats: dict[str, str]) -> bool:
        """Return True if parse p is consistent with all features in ud_feats.

        WW values of "X" or "0" are treated as wildcards and always pass.
        WW gender "C" (common = M or F) also passes any gender filter, since
        DICTLINE marks first-declension nouns as common rather than feminine.
        WW values with no UD mapping are skipped (not considered a mismatch).
        """
        for attr, (ud_key, ww_to_ud) in _WW_UD.items():
            if ud_key not in ud_feats:
                continue
            ww_val = getattr(p, attr)
            if ww_val in ("X", "0"):
                continue
            if attr == "gender" and ww_val == "C":
                continue
            mapped = ww_to_ud.get(ww_val)
            if mapped is None:
                continue
            if mapped != ud_feats[ud_key]:
                return False
        return True

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
