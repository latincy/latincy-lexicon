"""Morphological form generator: lemma → all inflected forms.

The inverse of the Analyzer. Given a Latin lemma, looks it up in DICTLINE
to get its stems and class, then applies INFLECTS rules to generate all
inflected forms with UD feature strings.

Data source: the same ``analyzer.json`` that the Analyzer uses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from latincy_lexicon.align.normalize import normalize_latin


# ---------------------------------------------------------------------------
# WW → UD feature mapping constants
# ---------------------------------------------------------------------------

_MOOD_MAP = {"IND": "Ind", "SUB": "Sub", "IMP": "Imp", "INF": "Inf", "PPL": "Part"}
_VOICE_MAP = {"ACTIVE": "Act", "PASSIVE": "Pass"}
_NUMBER_MAP = {"S": "Sing", "P": "Plur"}
_CASE_MAP = {
    "NOM": "Nom", "GEN": "Gen", "DAT": "Dat",
    "ACC": "Acc", "ABL": "Abl", "VOC": "Voc", "LOC": "Loc",
}
_GENDER_MAP = {"M": "Masc", "F": "Fem", "N": "Neut", "C": "Com"}
_COMPARISON_MAP = {"POS": "Pos", "COMP": "Cmp", "SUPER": "Sup"}


def _build_feats(rule: dict, pos: str, entry: dict | None = None) -> str:
    """Build a UD feature string from an INFLECTS rule dict.

    Args:
        rule: An INFLECTS rule dict with WW-style keys.
        pos: The WW part-of-speech (V, VPAR, SUPINE, N, ADJ, etc.).
        entry: Optional DICTLINE entry for gender fallback (nouns).

    Returns:
        Pipe-separated UD feature string, e.g. "Mood=Ind|Number=Sing|..."
        sorted alphabetically by key.
    """
    feats: dict[str, str] = {}

    # -- Aspect (derived from tense for verbs) --
    tense = rule.get("tense", "X")
    if tense in ("PRES", "IMPF"):
        feats["Aspect"] = "Imp"
    elif tense == "PERF":
        feats["Aspect"] = "Perf"

    # -- Case --
    case_val = rule.get("case_val", "X")
    if case_val in _CASE_MAP:
        feats["Case"] = _CASE_MAP[case_val]

    # -- Gender (from rule, or fall back to entry for nouns) --
    gender = rule.get("gender", "X")
    if gender in _GENDER_MAP:
        feats["Gender"] = _GENDER_MAP[gender]
    elif entry and pos == "N" and entry.get("gender") in _GENDER_MAP:
        feats["Gender"] = _GENDER_MAP[entry["gender"]]

    # -- Mood (finite verbs only) --
    mood = rule.get("mood", "X")
    if mood in _MOOD_MAP and pos == "V":
        feats["Mood"] = _MOOD_MAP[mood]

    # -- Number --
    number = rule.get("number", "X")
    if number in _NUMBER_MAP:
        feats["Number"] = _NUMBER_MAP[number]

    # -- Person --
    person = rule.get("person", "0")
    if person in ("1", "2", "3"):
        feats["Person"] = person

    # -- Tense (UD mapping) --
    _tense_map = {
        "PRES": "Pres", "IMPF": "Imp", "FUT": "Fut",
        "PERF": "Past", "PLUP": "Pqp", "FUTP": "Fut",
    }
    if tense in _tense_map:
        feats["Tense"] = _tense_map[tense]

    # -- VerbForm --
    if pos == "V":
        mood_val = rule.get("mood", "X")
        if mood_val == "INF":
            feats["VerbForm"] = "Inf"
        else:
            feats["VerbForm"] = "Fin"
    elif pos == "VPAR":
        feats["VerbForm"] = "Part"
    elif pos == "SUPINE":
        feats["VerbForm"] = "Sup"

    # -- Voice --
    voice = rule.get("voice", "X")
    if voice in _VOICE_MAP:
        feats["Voice"] = _VOICE_MAP[voice]

    # -- Comparison (adjectives/adverbs) --
    comparison = rule.get("comparison", "X")
    if comparison in _COMPARISON_MAP:
        feats["Degree"] = _COMPARISON_MAP[comparison]

    # Sort by key and join
    return "|".join(f"{k}={v}" for k, v in sorted(feats.items()))


def _ud_pos(entry: dict) -> str:
    """Map a WW DICTLINE entry to a UD UPOS tag.

    Args:
        entry: A DICTLINE entry dict with 'pos' and 'verb_kind' keys.

    Returns:
        UD UPOS string (e.g. 'VERB', 'AUX', 'NOUN', 'ADJ').
    """
    pos = entry.get("pos", "")
    verb_kind = entry.get("verb_kind", "X")

    _POS_MAP = {
        "N": "NOUN",
        "ADJ": "ADJ",
        "ADV": "ADV",
        "PRON": "PRON",
        "PACK": "DET",
        "NUM": "NUM",
        "CONJ": "CCONJ",
        "PREP": "ADP",
        "INTERJ": "INTJ",
    }

    if pos in ("V", "VPAR", "SUPINE"):
        if verb_kind == "TO_BE":
            return "AUX"
        return "VERB"
    return _POS_MAP.get(pos, "X")


@dataclass
class Form:
    """A single generated inflected form."""
    form: str
    lemma: str
    upos: str
    feats: str


# ---------------------------------------------------------------------------
# Pedagogical paradigm sort order
# ---------------------------------------------------------------------------

# Traditional Latin paradigm orderings — used when ``Generator.generate(...)``
# is called with ``sort="paradigm"`` to produce human-readable output rather
# than the inflection-rule traversal order that comes out by default.

_CASE_ORDER = {"Nom": 0, "Gen": 1, "Dat": 2, "Acc": 3, "Abl": 4, "Voc": 5, "Loc": 6}
_NUMBER_ORDER = {"Sing": 0, "Plur": 1}
_GENDER_ORDER = {"Masc": 0, "Fem": 1, "Neut": 2, "Com": 3}
_DEGREE_ORDER = {"Pos": 0, "Cmp": 1, "Sup": 2}
_TENSE_ORDER = {
    "Pres": 0, "Imp": 1, "Fut": 2, "Past": 3, "Pqp": 4, "FutPerf": 5,
}
_MOOD_ORDER = {"Ind": 0, "Sub": 1, "Imp": 2, "Inf": 3, "Part": 4}
_VOICE_ORDER = {"Act": 0, "Pass": 1, "Mid": 2}
_PERSON_ORDER = {"1": 0, "2": 1, "3": 2, "0": 3}
_VERBFORM_ORDER = {"Fin": 0, "Inf": 1, "Part": 2, "Sup": 3, "Ger": 4, "Gdv": 5}

_NOUN_UPOS = {"NOUN", "PROPN"}
_ADJECTIVAL_UPOS = {"ADJ", "PRON", "DET", "NUM"}
_VERBAL_UPOS = {"VERB", "AUX"}


def _paradigm_sort_key(form: "Form") -> tuple:
    """Return a sort key that orders forms in pedagogical paradigm order.

    For **nouns** (NOUN, PROPN): number → case → gender. Nouns have one
    inherent gender, so sorting by gender first would split a single
    paradigm into multiple gender-tagged sub-blocks (a WW data-tagging
    artifact where some rules emit Gender=Masc and others emit Gender=Com
    for the same lemma). Sorting by number+case keeps the textbook reading
    sequence nom→gen→dat→acc→abl→voc, sing first then plur, with gender
    only as a tiebreaker for genuinely-ambiguous forms.

    For **adjectivals** (ADJ, PRON, DET, NUM): degree → gender → number
    → case. Gender IS the primary axis here because adjective paradigms
    are traditionally presented as masculine paradigm, then feminine
    paradigm, then neuter paradigm.

    For **verbals** (VERB, AUX): verbform → mood → voice → tense → number
    → person → case/gender (for participles). Standard textbook order
    1sg/2sg/3sg/1pl/2pl/3pl reads sing-before-plur with person inner.

    Unknown features sort to the end (sentinel value 9).
    """
    feats = (
        dict(kv.split("=") for kv in form.feats.split("|") if "=" in kv)
        if form.feats
        else {}
    )
    upos = form.upos

    if upos in _NOUN_UPOS:
        return (
            0,  # nominals before verbals
            _NUMBER_ORDER.get(feats.get("Number", ""), 9),
            _CASE_ORDER.get(feats.get("Case", ""), 9),
            _GENDER_ORDER.get(feats.get("Gender", ""), 9),
            form.form,
        )
    if upos in _ADJECTIVAL_UPOS:
        return (
            0,  # nominals before verbals
            _DEGREE_ORDER.get(feats.get("Degree", "Pos"), 9),
            _GENDER_ORDER.get(feats.get("Gender", ""), 9),
            _NUMBER_ORDER.get(feats.get("Number", ""), 9),
            _CASE_ORDER.get(feats.get("Case", ""), 9),
            form.form,
        )
    if upos in _VERBAL_UPOS:
        return (
            1,
            _VERBFORM_ORDER.get(feats.get("VerbForm", ""), 9),
            _MOOD_ORDER.get(feats.get("Mood", ""), 9),
            _VOICE_ORDER.get(feats.get("Voice", ""), 9),
            _TENSE_ORDER.get(feats.get("Tense", ""), 9),
            # Number outer, Person inner: traditional Latin reading order is
            # 1sg, 2sg, 3sg, 1pl, 2pl, 3pl (sing column completes before plur).
            _NUMBER_ORDER.get(feats.get("Number", ""), 9),
            _PERSON_ORDER.get(feats.get("Person", ""), 9),
            _CASE_ORDER.get(feats.get("Case", ""), 9),
            _GENDER_ORDER.get(feats.get("Gender", ""), 9),
            form.form,
        )
    return (2, form.form)


class Generator:
    """Generate all inflected forms of a Latin lemma.

    Uses the same DICTLINE + INFLECTS data as the Analyzer, but in reverse:
    look up lemma → get stems → apply matching inflection rules → emit forms.

    Load from JSON (same file as Analyzer)::

        gen = Generator.from_json("data/json/analyzer.json")
        forms = gen.generate("amo")
    """

    def __init__(
        self,
        entries: list[dict],
        inflections: list[dict],
        uniques: list[dict],
        headwords: dict[int, str],
    ) -> None:
        self._entries = entries
        self._inflections = inflections
        self._uniques = uniques
        self._headwords = headwords
        self._build_caches()

    @classmethod
    def from_json(cls, path: str | Path) -> "Generator":
        """Load generator from analyzer.json."""
        with open(path) as f:
            data = json.load(f)
        headwords = {int(k): v for k, v in data["headwords"].items()}
        return cls(
            entries=data["entries"],
            inflections=data["inflections"],
            uniques=data["uniques"],
            headwords=headwords,
        )

    # Manual overrides for UNIQUE forms where prefix-based resolution
    # picks the wrong (or too narrow) source lemma, or where the form is
    # an orphan idiom that should not be sprayed across the fallback class.
    # Each entry maps a (form, pos, decl_which, decl_var) tuple to the set
    # of lemma headwords that should claim the unique; an empty list means
    # "drop this unique entirely". Resolved to entry IDs at load time.
    _UNIQUE_LEMMA_OVERRIDES: dict[tuple, list[str]] = {
        # vult/vultis are the standard 3sg/2pl present indicative of volo,
        # but the prefix matcher prefers the rare same-class alt vulo (stem
        # 'vul') over volo (stems 'vol', 'vel', 'volu'). Attach to both.
        ("vult", "V", 6, 2): ["volo", "vulo"],
        ("vultis", "V", 6, 2): ["volo", "vulo"],
        # vis (2sg present indicative of volo) shares no 2-char prefix with
        # any V 6 2 stem, so it would otherwise fall through unrestricted.
        ("vis", "V", 6, 2): ["volo"],
        # Orphan idioms: drop entirely rather than spraying across the class.
        # ``necessest`` is a contraction of ``necesse est`` (it is necessary),
        # not a true form of any single esse compound. Without this override
        # it appears as a 3sg present in sum, absum, possum, prosum, etc.
        ("necessest", "V", 5, 1): [],
        # ``memento``/``mementote`` are imperatives of ``memini`` (perfect-only,
        # not in our DICTLINE as a citation form). Stored under V 0 0, they
        # would otherwise fall through to every verb's paradigm via the
        # cascade fallback.
        ("memento", "V", 0, 0): [],
        ("mementote", "V", 0, 0): [],
    }

    def _build_caches(self) -> None:
        """Build lookup structures for generation."""
        # Lemma → list of DICTLINE entries
        self._lemma_index: dict[str, list[dict]] = {}
        for entry in self._entries:
            eid = entry["id"]
            hw = self._headwords.get(eid)
            if hw:
                self._lemma_index.setdefault(normalize_latin(hw), []).append(entry)

        # (pos, decl_which, decl_var) → list of inflection rules
        self._rules: dict[tuple, list[dict]] = {}
        for rule in self._inflections:
            key = (rule["pos"], rule["decl_which"], rule["decl_var"])
            self._rules.setdefault(key, []).append(rule)

        # (pos, decl_which, decl_var) → list of DICTLINE entries (for UNIQUES resolution)
        entries_by_class: dict[tuple, list[dict]] = {}
        for entry in self._entries:
            k = (entry["pos"], entry["decl_which"], entry["decl_var"])
            entries_by_class.setdefault(k, []).append(entry)

        # (pos, decl_which, decl_var) → list of UNIQUES dicts
        self._uniques_index: dict[tuple, list[dict]] = {}
        for u in self._uniques:
            key = (u["pos"], u.get("decl_which", 0), u.get("decl_var", 0))
            self._uniques_index.setdefault(key, []).append(u)
            # Resolve which DICTLINE entry/entries this UNIQUE belongs to.
            # Manual overrides take precedence; otherwise fall back to prefix
            # matching against same-class stems.
            override_key = (u["form"], *key)
            override_lemmas = self._UNIQUE_LEMMA_OVERRIDES.get(override_key)
            if override_lemmas is not None:
                u["_source_entry_ids"] = {
                    e["id"]
                    for lemma in override_lemmas
                    for e in self._lemma_index.get(normalize_latin(lemma), [])
                    if (e["pos"], e["decl_which"], e["decl_var"]) == key
                }
            else:
                u["_source_entry_ids"] = self._resolve_unique_source(u, entries_by_class)

    @staticmethod
    def _resolve_unique_source(
        unique: dict, entries_by_class: dict[tuple, list[dict]],
    ) -> set[int] | None:
        """Find DICTLINE entries that a UNIQUE form most likely belongs to.

        Uses common-prefix matching between the unique's surface form and each
        candidate entry's stems. Returns the set of entry IDs whose stems share
        at least one character of prefix with the form (within the most
        specific class that has any matches), or ``None`` if no entry shares
        any prefix (orphan forms like ``necessest`` then fall through to all
        matching classes — preserving legacy behavior).

        Permissive multi-attach matters because a unique form like ``vult``
        could be the inflection of multiple semantically-overlapping lemmas
        in the same morphological class (here ``volo`` and the rare alt
        ``vulo``). Attaching to *all* entries with any prefix overlap keeps
        common forms attached to common lemmas while still excluding
        unrelated lemmas like ``malo``/``nolo`` which share no prefix at all.
        """
        form = unique["form"]
        u_pos = unique["pos"]
        u_dw = unique.get("decl_which", 0)
        u_dv = unique.get("decl_var", 0)

        matched_ids: set[int] = set()

        # Require a 2-char prefix overlap to claim a unique. 1-char is too
        # permissive (every 'r-' word matches every other 'r-' word) and
        # full longest-match is too strict (loses common forms like ``vult``
        # to obscure same-class lemmas like ``vulo``). Two characters is the
        # sweet spot: ``bo`` separates ``bos`` from ``bestia``, ``vo``/``vu``
        # both attach ``vult`` to volo and vulo, but ``ru`` keeps ``rusi``
        # away from ``rex``.
        min_prefix = 2

        for cls_key in [(u_pos, u_dw, u_dv), (u_pos, u_dw, 0), (u_pos, 0, 0)]:
            for entry in entries_by_class.get(cls_key, []):
                for si in (1, 2, 3, 4):
                    stem = entry.get(f"stem{si}", "")
                    if not stem or stem == "zzz":
                        continue
                    # For stems shorter than min_prefix, require the whole
                    # stem to be a prefix of the form (covers single-letter
                    # stems like sum's "s").
                    target = min(min_prefix, len(stem))
                    if (
                        len(form) >= target
                        and len(stem) >= target
                        and stem[:target] == form[:target]
                    ):
                        matched_ids.add(entry["id"])
                        break
            if matched_ids:
                break  # Stop cascading once we have matches in a more specific class

        return matched_ids if matched_ids else None

    def lookup(self, lemma: str) -> list[dict]:
        """Look up DICTLINE entries for a lemma.

        Args:
            lemma: Citation form (e.g. "amo", "rex", "sum").

        Returns:
            List of matching DICTLINE entry dicts.
        """
        return list(self._lemma_index.get(normalize_latin(lemma), []))

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        lemma: str,
        *,
        pos: str | None = None,
        sort: str = "ud",
    ) -> list[Form]:
        """Generate all inflected forms of *lemma*.

        Looks up the lemma in DICTLINE, then applies every matching
        INFLECTS rule to produce Form objects with UD features.

        Args:
            lemma: Citation form (e.g. "amo", "rex", "sum").
            pos: Optional WW POS filter ("V", "N", "ADJ", etc.).
            sort: Output ordering. ``"ud"`` (default) preserves the
                inflection-rule traversal order — best for downstream NLP
                code that filters by feats. ``"paradigm"`` re-orders forms
                by traditional Latin pedagogical sequence (nom→gen→dat
                →acc→abl→voc for nouns, present→imperfect→future for
                verbs, etc.) — best for human-readable display.

        Returns:
            List of Form dataclass instances, one per inflected form.
        """
        if sort not in ("ud", "paradigm"):
            raise ValueError(f"sort must be 'ud' or 'paradigm', got {sort!r}")

        entries = self.lookup(lemma)
        if pos:
            entries = [e for e in entries if e["pos"] == pos]

        all_forms: list[Form] = []
        seen: set[tuple[str, str]] = set()
        for entry in entries:
            for f in self._generate_entry(entry, lemma):
                key = (f.form, f.feats)
                if key not in seen:
                    seen.add(key)
                    all_forms.append(f)

        # Add matching UNIQUES (irregular forms sharing POS + decl class)
        # Track which class keys to search plus the entry for UPOS resolution
        matched_classes: dict[tuple, dict] = {}
        for entry in entries:
            epos = entry["pos"]
            dw = entry["decl_which"]
            dv = entry["decl_var"]
            # Collect all class keys that could match (same cascade as rules)
            # Keep the first entry per key for verb_kind resolution
            for k in [(epos, dw, dv), (epos, dw, 0), (epos, 0, 0)]:
                if k not in matched_classes:
                    matched_classes[k] = entry

        # Build set of entry IDs for this lemma to filter UNIQUES against
        lemma_entry_ids = {e["id"] for e in entries}

        for cls_key, ref_entry in matched_classes.items():
            for u in self._uniques_index.get(cls_key, []):
                # Skip if this UNIQUE is bound to specific source entries
                # and none of them are in the current lemma's entries.
                # ``_source_entry_ids`` is None for unresolved/orphan uniques
                # which fall through to all matching classes (legacy behavior).
                source_ids = u.get("_source_entry_ids")
                if source_ids is not None and not (source_ids & lemma_entry_ids):
                    continue
                upos = _ud_pos(ref_entry)
                feats = _build_feats(u, u["pos"])
                key = (u["form"], feats)
                if key not in seen:
                    seen.add(key)
                    all_forms.append(Form(
                        form=u["form"], lemma=lemma, upos=upos, feats=feats,
                    ))

        if sort == "paradigm":
            all_forms.sort(key=_paradigm_sort_key)
        return all_forms

    def _generate_entry(self, entry: dict, lemma: str) -> list[Form]:
        """Generate all forms for a single DICTLINE entry.

        For verbs, this includes:
        - V rules (class-specific + generic V 0.0)
        - VPAR rules (class-specific + generic VPAR 0.0 for PPP)
        - SUPINE rules (always generic SUPINE 0.0)
        """
        pos = entry["pos"]
        upos = _ud_pos(entry)
        forms: list[Form] = []

        # Get the stems as a dict keyed by stem_key (1-4)
        stems = {
            1: entry.get("stem1", ""),
            2: entry.get("stem2", ""),
            3: entry.get("stem3", ""),
            4: entry.get("stem4", ""),
        }

        if pos == "V":
            # Class-specific V rules + generic V 0.0
            for rule in self._matching_rules(entry):
                stem = stems.get(rule["stem_key"], "")
                if stem is None or stem == "zzz":
                    continue
                ending = rule.get("ending", "")
                surface = stem + ending
                feats = _build_feats(rule, "V", entry)
                forms.append(Form(form=surface, lemma=lemma, upos=upos, feats=feats))

            # VPAR rules (participles)
            for rule in self._matching_vpar_rules(entry):
                stem = stems.get(rule["stem_key"], "")
                if stem is None or stem == "zzz":
                    continue
                ending = rule.get("ending", "")
                surface = stem + ending
                feats = _build_feats(rule, "VPAR", entry)
                forms.append(Form(form=surface, lemma=lemma, upos=upos, feats=feats))

            # SUPINE rules
            for rule in self._matching_supine_rules(entry):
                stem = stems.get(rule["stem_key"], "")
                if stem is None or stem == "zzz":
                    continue
                ending = rule.get("ending", "")
                surface = stem + ending
                feats = _build_feats(rule, "SUPINE", entry)
                forms.append(Form(form=surface, lemma=lemma, upos=upos, feats=feats))
        else:
            # Non-verb POS: apply class-specific + generic rules
            allow_locative = self._entry_allows_locative(entry)
            matching = self._matching_rules(entry)
            # Pre-scan: which (case, number, stem_key) slots have a freq='A'
            # rule? We use this to suppress alternate forms (freq B/C/D) when
            # the standard form is already present — e.g. ``regium`` (N 3 1
            # GEN P -ium freq=B) is a redundant alternate to ``regum`` (-um
            # freq=A) for consonant-stem 3rd-decl nouns. Orphan archaic forms
            # without an A-frequency sibling (e.g. ``puellabus`` 1st-decl
            # dat/abl plural -abus freq=B age=D) are preserved.
            covered_slots = {
                (r.get("case_val"), r.get("number"), r["stem_key"])
                for r in matching
                if r.get("freq") == "A" and r.get("age", "X") == "X"
            }
            for rule in matching:
                # Suppress locative case rules unless this entry's noun_kind
                # marks it as a place name (L) or "where" noun (W). WW's
                # INFLECTS table emits LOC endings for every declension,
                # which produces semantically nonsensical output like
                # ``Case=Loc`` rex/rege/regibus on common nouns.
                if not allow_locative and rule.get("case_val") == "LOC":
                    continue
                # Suppress period-specific rules (age != 'X') for nominal
                # paradigms. WW marks rare/archaic/late variants with explicit
                # age codes — e.g. ``rege`` as DAT singular is `age='B'` (early
                # Latin), which pollutes the standard paradigm with a form
                # that's actually the ablative. Keep only age='X' (universal)
                # rules for the canonical textbook paradigm.
                if rule.get("age", "X") != "X":
                    continue
                # Suppress redundant alternate forms (freq != 'A') when the
                # same slot already has a standard freq='A' rule.
                if rule.get("freq") != "A":
                    slot = (rule.get("case_val"), rule.get("number"), rule["stem_key"])
                    if slot in covered_slots:
                        continue
                stem = stems.get(rule["stem_key"], "")
                if stem is None or stem == "zzz":
                    continue
                ending = rule.get("ending", "")
                surface = stem + ending
                feats = _build_feats(rule, pos, entry)
                forms.append(Form(form=surface, lemma=lemma, upos=upos, feats=feats))

        return forms

    # Common nouns that classically take a locative form despite being tagged
    # as ``noun_kind='T'`` (thing) or ``'A'`` (abstract) in DICTLINE. Whitaker
    # didn't carry the locative-bearing common nouns into noun_kind='W', so
    # we maintain a small allowlist for the canonical Latin set.
    _LOCATIVE_COMMON_NOUNS: frozenset[str] = frozenset({
        "humus",     # humi — on the ground
        "militia",   # militiae — on campaign
        "bellum",    # belli — in/at war (adverbial)
        "focus",     # foci — at the hearth
    })

    def _entry_allows_locative(self, entry: dict) -> bool:
        """Return True if this entry should emit locative case forms.

        Locative is morphologically real for every Latin noun (and equal to
        ablative in most declensions), but semantically meaningful only for
        place names and a small set of common nouns. Suppressing it elsewhere
        cleans up paradigms without losing any actual usage.
        """
        if entry["pos"] != "N":
            # Adjectives and pronouns don't take locative in classical usage.
            return False
        kind = entry.get("noun_kind", "")
        if kind in ("L", "W"):
            return True
        # Common-noun allowlist (lookup via headword)
        hw = self._headwords.get(entry["id"], "")
        return normalize_latin(hw) in self._LOCATIVE_COMMON_NOUNS

    def _matching_rules(self, entry: dict) -> list[dict]:
        """Return INFLECTS rules matching an entry's POS and class.

        Collects:
        - Exact match: (pos, decl_which, decl_var)
        - Variant-generic: (pos, decl_which, 0) if decl_var != 0
        - Fully generic: (pos, 0, 0) if decl_which != 0
        """
        pos = entry["pos"]
        dw = entry["decl_which"]
        dv = entry["decl_var"]

        rules = list(self._rules.get((pos, dw, dv), []))
        if dv != 0:
            rules.extend(self._rules.get((pos, dw, 0), []))
        if dw != 0:
            rules.extend(self._rules.get((pos, 0, 0), []))
        return rules

    def _matching_vpar_rules(self, entry: dict) -> list[dict]:
        """Return VPAR (participle) rules matching a verb entry.

        For a verb with decl_which=W:
        - Class-specific: (VPAR, W, 0) — present active participle
        - Generic: (VPAR, 0, 0) — PPP and future participles (stem4)
        """
        dw = entry["decl_which"]

        rules = list(self._rules.get(("VPAR", dw, 0), []))
        if dw != 0:
            rules.extend(self._rules.get(("VPAR", 0, 0), []))
        return rules

    def _matching_supine_rules(self, entry: dict) -> list[dict]:
        """Return SUPINE rules (always generic SUPINE 0.0)."""
        return list(self._rules.get(("SUPINE", 0, 0), []))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def to_lookup_dict(
        self, lemmas: list[str], *, pos: str | None = None
    ) -> dict[str, str]:
        """Generate a flat form→lemma lookup dictionary.

        For each lemma, generates all inflected forms and maps each surface
        form to its lemma. First-lemma-wins: if two lemmas produce the same
        surface form, the first lemma in *lemmas* keeps the mapping.

        Args:
            lemmas: List of citation forms to generate.
            pos: Optional WW POS filter passed to :meth:`generate`.

        Returns:
            Dict mapping surface form strings to lemma strings.
        """
        result: dict[str, str] = {}
        for lemma in lemmas:
            for f in self.generate(lemma, pos=pos):
                if f.form not in result:
                    result[f.form] = f.lemma
        return result
