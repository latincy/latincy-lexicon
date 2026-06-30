"""Canonical-vs-alternate discrimination for generated verb forms.

Whitaker ships parallel paradigms for many verbs: alongside the canonical
``amo`` entry (``V 1 1``, perfect stem ``amav``) sits a syncopated/Plautine
entry (``V 8 1``, perfect stem ``amass``) whose forms — ``amasso``,
``amasseram``, ``amassim`` — are real but non-standard. Crucially many carry
``age='X'``, so a frequency/age filter can't separate them; the discriminator
is the *stem*: a perfect-system form that does not start with the reconstructed
canonical perfect stem is an alternate.

This module reconstructs a verb entry's canonical (present, perfect, supine)
stems and decides, per finite/infinitive form, whether it belongs in the
canonical paradigm or should be flagged ``alternate``. The logic is ported from
the latincy-lexicon-site presentation layer so the library — not each consumer
— owns the linguistic judgement.
"""

from __future__ import annotations

from latincy_lexicon.principal_parts import _detect_conj

# WW field codes → the UD-ish space the discriminators work in.
_TENSE = {
    "PRES": "Pres", "IMPF": "Imp", "FUT": "Fut",
    "PERF": "Past", "PLUP": "Pqp", "FUTP": "FutP",
}
_MOOD = {"IND": "Ind", "SUB": "Sub", "IMP": "Imp", "INF": "Inf"}
_VOICE = {"ACTIVE": "Act", "PASSIVE": "Pass"}
_NUMBER = {"S": "Sing", "P": "Plur"}

# Tenses built on the perfect stem.
_PERF_SYS_TENSES = {"Past", "Pst", "Pqp", "FutP"}

# Future-indicative theme prefixes for 1st/2nd conjugation (``amabo``,
# ``monebo``); used to catch wrong-stem futures.
_FUT_IND_PREFIX = {1: "ab", 2: "eb"}


# ---------------------------------------------------------------------------
# Stem reconstruction
# ---------------------------------------------------------------------------

def verb_stems(
    headword: str, stems: list[str]
) -> tuple[str, str, int | None, bool, str]:
    """Return ``(present_stem, perfect_stem, conj, has_real_ppp, supine_stem)``.

    ``headword`` is the citation form (used to detect conjugation) and ``stems``
    the cleaned principal-part list (no empties or ``zzz``).

    Whitaker's stem layout varies. 1st-conj entries are ``[pres, pres, perf]``
    (``amo`` → ``[am, am, amass]``); irregulars use ``[pres, perf, sup]``
    (``sum`` → ``[s, fu, fut]``); 4-stem entries are ``[pres, pres2, perf, sup]``
    (``audio`` → ``[audi, aud, audiv, audit]``). The 1st-conj perfect is stored
    syncopated as ``-ass``; it is rewritten back to canonical ``-av`` so prefix
    matches catch ``amavero`` and flag ``amasso``.

    ``has_real_ppp`` is False for verbs (e.g. ``sum``) where the library would
    mechanically decline the supine stem into a non-existent PPP (``futus``).
    """
    hw = headword or ""
    if not hw or not stems:
        return "", "", None, False, ""
    conj = _detect_conj(hw, stems)
    pres = stems[0]
    perf, has_ppp = _select_perf_stem(pres, stems)
    if conj == 1 and perf.endswith("ass"):
        perf = perf[:-3] + "av"
    sup = _select_supine_stem(pres, conj, stems, has_ppp)
    return pres, perf, conj, has_ppp, sup


def _select_perf_stem(pres: str, stems: list[str]) -> tuple[str, bool]:
    if len(stems) >= 4:
        return stems[2], True
    if len(stems) == 3:
        s1, s2 = stems[1], stems[2]
        if s1 == pres:
            return s2, True  # 1st-conj-style: stems[2] is perfect
        if s2.startswith(s1) and len(s2) > len(s1):
            return s1, False  # irregular: stems[2] is supine, no real PPP
        return s2, True
    if len(stems) == 2:
        return stems[1], False
    return "", False


def _select_supine_stem(
    pres: str, conj: int | None, stems: list[str], has_ppp: bool
) -> str:
    if len(stems) >= 4:
        return stems[3]
    if conj == 1 and pres and has_ppp:
        return pres + "at"  # amat, portat — synthesized
    return ""


# ---------------------------------------------------------------------------
# Present-system ending table
# ---------------------------------------------------------------------------

def _build_pres_sys_endings():
    out: dict = {}

    def add(conj, mood, tense, voice, sufs, alts=None):
        cell = {
            ("1", "Sing"): {sufs[0]}, ("2", "Sing"): {sufs[1]}, ("3", "Sing"): {sufs[2]},
            ("1", "Plur"): {sufs[3]}, ("2", "Plur"): {sufs[4]}, ("3", "Plur"): {sufs[5]},
        }
        if alts:
            for k, v in alts.items():
                cell[k] = cell[k] | {v}
        out[(conj, mood, tense, voice)] = cell

    # Conjugation 1 (am-)
    add(1, "Ind", "Pres", "Act", ["o", "as", "at", "amus", "atis", "ant"])
    add(1, "Ind", "Pres", "Pass", ["or", "aris", "atur", "amur", "amini", "antur"], {("2", "Sing"): "are"})
    add(1, "Ind", "Imp", "Act", ["abam", "abas", "abat", "abamus", "abatis", "abant"])
    add(1, "Ind", "Imp", "Pass", ["abar", "abaris", "abatur", "abamur", "abamini", "abantur"], {("2", "Sing"): "abare"})
    add(1, "Ind", "Fut", "Act", ["abo", "abis", "abit", "abimus", "abitis", "abunt"])
    add(1, "Ind", "Fut", "Pass", ["abor", "aberis", "abitur", "abimur", "abimini", "abuntur"], {("2", "Sing"): "abere"})
    add(1, "Sub", "Pres", "Act", ["em", "es", "et", "emus", "etis", "ent"])
    add(1, "Sub", "Pres", "Pass", ["er", "eris", "etur", "emur", "emini", "entur"], {("2", "Sing"): "ere"})
    add(1, "Sub", "Imp", "Act", ["arem", "ares", "aret", "aremus", "aretis", "arent"])
    add(1, "Sub", "Imp", "Pass", ["arer", "areris", "aretur", "aremur", "aremini", "arentur"], {("2", "Sing"): "arere"})
    out[(1, "Imp", "Pres", "Act")] = {("2", "Sing"): {"a"}, ("2", "Plur"): {"ate"}}
    out[(1, "Imp", "Pres", "Pass")] = {("2", "Sing"): {"are"}, ("2", "Plur"): {"amini"}}
    out[(1, "Imp", "Fut", "Act")] = {("2", "Sing"): {"ato"}, ("3", "Sing"): {"ato"}, ("2", "Plur"): {"atote"}, ("3", "Plur"): {"anto"}}
    out[(1, "Imp", "Fut", "Pass")] = {("2", "Sing"): {"ator"}, ("3", "Sing"): {"ator"}, ("3", "Plur"): {"antor"}}

    # Conjugation 2 (mon-)
    add(2, "Ind", "Pres", "Act", ["eo", "es", "et", "emus", "etis", "ent"])
    add(2, "Ind", "Pres", "Pass", ["eor", "eris", "etur", "emur", "emini", "entur"], {("2", "Sing"): "ere"})
    add(2, "Ind", "Imp", "Act", ["ebam", "ebas", "ebat", "ebamus", "ebatis", "ebant"])
    add(2, "Ind", "Imp", "Pass", ["ebar", "ebaris", "ebatur", "ebamur", "ebamini", "ebantur"], {("2", "Sing"): "ebare"})
    add(2, "Ind", "Fut", "Act", ["ebo", "ebis", "ebit", "ebimus", "ebitis", "ebunt"])
    add(2, "Ind", "Fut", "Pass", ["ebor", "eberis", "ebitur", "ebimur", "ebimini", "ebuntur"], {("2", "Sing"): "ebere"})
    add(2, "Sub", "Pres", "Act", ["eam", "eas", "eat", "eamus", "eatis", "eant"])
    add(2, "Sub", "Pres", "Pass", ["ear", "earis", "eatur", "eamur", "eamini", "eantur"], {("2", "Sing"): "eare"})
    add(2, "Sub", "Imp", "Act", ["erem", "eres", "eret", "eremus", "eretis", "erent"])
    add(2, "Sub", "Imp", "Pass", ["erer", "ereris", "eretur", "eremur", "eremini", "erentur"], {("2", "Sing"): "erere"})
    out[(2, "Imp", "Pres", "Act")] = {("2", "Sing"): {"e"}, ("2", "Plur"): {"ete"}}
    out[(2, "Imp", "Pres", "Pass")] = {("2", "Sing"): {"ere"}, ("2", "Plur"): {"emini"}}
    out[(2, "Imp", "Fut", "Act")] = {("2", "Sing"): {"eto"}, ("3", "Sing"): {"eto"}, ("2", "Plur"): {"etote"}, ("3", "Plur"): {"ento"}}
    out[(2, "Imp", "Fut", "Pass")] = {("2", "Sing"): {"etor"}, ("3", "Sing"): {"etor"}, ("3", "Plur"): {"entor"}}

    # Conjugation 3 (reg-, dic-)
    add(3, "Ind", "Pres", "Act", ["o", "is", "it", "imus", "itis", "unt"])
    add(3, "Ind", "Pres", "Pass", ["or", "eris", "itur", "imur", "imini", "untur"], {("2", "Sing"): "ere"})
    add(3, "Ind", "Imp", "Act", ["ebam", "ebas", "ebat", "ebamus", "ebatis", "ebant"])
    add(3, "Ind", "Imp", "Pass", ["ebar", "ebaris", "ebatur", "ebamur", "ebamini", "ebantur"], {("2", "Sing"): "ebare"})
    add(3, "Ind", "Fut", "Act", ["am", "es", "et", "emus", "etis", "ent"])
    add(3, "Ind", "Fut", "Pass", ["ar", "eris", "etur", "emur", "emini", "entur"], {("2", "Sing"): "ere"})
    add(3, "Sub", "Pres", "Act", ["am", "as", "at", "amus", "atis", "ant"])
    add(3, "Sub", "Pres", "Pass", ["ar", "aris", "atur", "amur", "amini", "antur"], {("2", "Sing"): "are"})
    add(3, "Sub", "Imp", "Act", ["erem", "eres", "eret", "eremus", "eretis", "erent"])
    add(3, "Sub", "Imp", "Pass", ["erer", "ereris", "eretur", "eremur", "eremini", "erentur"], {("2", "Sing"): "erere"})
    out[(3, "Imp", "Pres", "Act")] = {("2", "Sing"): {"e"}, ("2", "Plur"): {"ite"}}
    out[(3, "Imp", "Pres", "Pass")] = {("2", "Sing"): {"ere"}, ("2", "Plur"): {"imini"}}
    out[(3, "Imp", "Fut", "Act")] = {("2", "Sing"): {"ito"}, ("3", "Sing"): {"ito"}, ("2", "Plur"): {"itote"}, ("3", "Plur"): {"unto"}}
    out[(3, "Imp", "Fut", "Pass")] = {("2", "Sing"): {"itor"}, ("3", "Sing"): {"itor"}, ("3", "Plur"): {"untor"}}

    # Conjugation 4 (audi-)
    add(4, "Ind", "Pres", "Act", ["o", "s", "t", "mus", "tis", "unt"])
    add(4, "Ind", "Pres", "Pass", ["or", "ris", "tur", "mur", "mini", "untur"], {("2", "Sing"): "re"})
    add(4, "Ind", "Imp", "Act", ["ebam", "ebas", "ebat", "ebamus", "ebatis", "ebant"])
    add(4, "Ind", "Imp", "Pass", ["ebar", "ebaris", "ebatur", "ebamur", "ebamini", "ebantur"], {("2", "Sing"): "ebare"})
    add(4, "Ind", "Fut", "Act", ["am", "es", "et", "emus", "etis", "ent"])
    add(4, "Ind", "Fut", "Pass", ["ar", "eris", "etur", "emur", "emini", "entur"], {("2", "Sing"): "ere"})
    add(4, "Sub", "Pres", "Act", ["am", "as", "at", "amus", "atis", "ant"])
    add(4, "Sub", "Pres", "Pass", ["ar", "aris", "atur", "amur", "amini", "antur"], {("2", "Sing"): "are"})
    add(4, "Sub", "Imp", "Act", ["rem", "res", "ret", "remus", "retis", "rent"])
    add(4, "Sub", "Imp", "Pass", ["rer", "reris", "retur", "remur", "remini", "rentur"], {("2", "Sing"): "rere"})
    out[(4, "Imp", "Pres", "Act")] = {("2", "Sing"): {""}, ("2", "Plur"): {"te"}}
    out[(4, "Imp", "Pres", "Pass")] = {("2", "Sing"): {"re"}, ("2", "Plur"): {"mini"}}
    out[(4, "Imp", "Fut", "Act")] = {("2", "Sing"): {"to"}, ("3", "Sing"): {"to"}, ("2", "Plur"): {"tote"}, ("3", "Plur"): {"unto"}}
    out[(4, "Imp", "Fut", "Pass")] = {("2", "Sing"): {"tor"}, ("3", "Sing"): {"tor"}, ("3", "Plur"): {"untor"}}
    return out


_PRES_SYS_ENDINGS = _build_pres_sys_endings()


# ---------------------------------------------------------------------------
# Discriminators (work in the UD-ish space above)
# ---------------------------------------------------------------------------

def _is_finite_alternate(
    form, mood, tense, conj, pres_stem, perf_stem, person, number, voice,
    third_io=False,
) -> bool:
    if not perf_stem and not pres_stem:
        return False
    # Perfect-system forms not built on the canonical perfect stem are
    # alternates (Plautine sigmatic amasso/amasseram off the amass- stem).
    # This is the robust discriminator — a pure stem-prefix test.
    if tense in _PERF_SYS_TENSES:
        return bool(perf_stem) and not form.startswith(perf_stem)
    # Present-system ending validation catches wrong-conj/wrong-stem present
    # artefacts (audio's `audbam` for `audiebam`). Skipped for 3rd-io verbs:
    # _detect_conj maps them to conj 4 by the -io ending, but they build some
    # present forms on the consonant stem (capio → canonical `capere`), which
    # the conj-4 table — and the present-stem prefix test — would mis-flag.
    if third_io:
        return False
    if conj and pres_stem and tense in {"Pres", "Imp", "Fut"}:
        endings = _PRES_SYS_ENDINGS.get((conj, mood, tense, voice), {})
        valid = endings.get((person, number)) if (person and number) else None
        if valid is not None:
            if not form.startswith(pres_stem):
                return True
            return form[len(pres_stem):] not in valid
    if tense == "Fut" and mood == "Ind" and pres_stem and conj in _FUT_IND_PREFIX:
        return not form.startswith(pres_stem + _FUT_IND_PREFIX[conj])
    return False


def _is_inf_alternate(form, tense, voice, perf_stem) -> bool:
    if tense in _PERF_SYS_TENSES:
        if perf_stem and not form.startswith(perf_stem):
            return True
        if voice == "Act" and not form.endswith("isse"):
            return True
        return False
    if tense == "Pres":
        if voice == "Act" and not form.endswith("re"):
            return True
        if voice == "Pass" and not (form.endswith("ri") or form.endswith("i")):
            return True
    return False


def _is_part_alternate(form, tense, voice, conj, pres_stem, sup_stem) -> bool:
    """Route participles built from the wrong stem to alternates — for
    homonyms (dicere + dicare) the generic rule cascade emits both
    ``dicens`` / ``dicans``; keep only the stem consistent with this entry.

    Conservative: when the relevant stem is missing we keep the form.
    """
    if not (pres_stem or sup_stem):
        return False
    if voice == "Pass" and tense == "Past":
        return bool(sup_stem) and not form.startswith(sup_stem)
    if voice == "Act" and tense == "Fut":
        return bool(sup_stem) and not form.startswith(sup_stem)
    if not (conj and pres_stem and form.startswith(pres_stem)):
        return False
    after = form[len(pres_stem):]
    if voice == "Act" and tense == "Pres":
        if conj == 1:
            return not after.startswith(("an", "ant"))
        return not after.startswith(("en", "ient"))
    if voice == "Pass" and tense == "Fut":
        if conj == 1:
            return not after.startswith("and")
        if conj == 4:
            return not after.startswith(("end", "iend"))
        return not after.startswith(("end", "und"))
    return False


def is_participle_alternate(
    surface: str, rule: dict, pres_stem: str, sup_stem: str,
    conj: int | None, has_real_ppp: bool,
) -> bool:
    """Decide whether a generated participle is an alternate.

    Flags (A5) the spurious perfect-passive participle of verbs with no real
    PPP (``sum`` → ``futus``) and (A4) wrong-stem participles from homonym
    contamination. The future *active* participle (``futurus``) is real even
    when there is no PPP, so only Past/Passive is suppressed for A5.
    """
    tense = _TENSE.get(rule.get("tense", "X"))
    voice = _VOICE.get(rule.get("voice", "X"))
    if tense == "Past" and voice == "Pass" and not has_real_ppp:
        return True
    return _is_part_alternate(surface, tense or "", voice or "", conj, pres_stem, sup_stem)


def is_verb_form_alternate(
    surface: str, rule: dict, pres_stem: str, perf_stem: str,
    conj: int | None, third_io: bool = False,
) -> bool:
    """Decide whether a generated finite/infinitive verb form is an alternate.

    ``rule`` carries WW field codes (tense/mood/voice/person/number); they are
    mapped into the UD-ish space the discriminators use. ``third_io`` suppresses
    present-system ending validation for 3rd-io verbs. Conservative: unknown
    codes or missing stems default to canonical (not alternate).
    """
    tense = _TENSE.get(rule.get("tense", "X"))
    mood = _MOOD.get(rule.get("mood", "X"))
    voice = _VOICE.get(rule.get("voice", "X"))
    if tense is None or mood is None:
        return False
    if mood == "Inf":
        return _is_inf_alternate(surface, tense, voice or "", perf_stem)
    person = rule.get("person", "0")
    number = _NUMBER.get(rule.get("number", "X"), "")
    return _is_finite_alternate(
        surface, mood, tense, conj, pres_stem, perf_stem,
        person, number, voice or "", third_io,
    )
