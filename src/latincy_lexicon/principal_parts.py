"""Reconstruct textbook-style principal parts from Whitaker stems.

Whitaker's Words stores noun/verb/adjective stems (e.g., ``["scrib",
"scrib", "scrips", "script"]``) rather than citation forms like
``scribo, scribere, scripsi, scriptum``. The lexicon payload exposes
``decl_which`` (the declension/conjugation number) which drives noun
genitive formation; verb conjugation is still inferred from headword
shape and stem patterns.
"""

from __future__ import annotations

GENDER_ABBREV = {"M": "m.", "F": "f.", "N": "n.", "C": "c."}

#: Irregular three-gender citation forms for demonstratives, the relative/
#: interrogative, and pronominal adjectives whose neuter isn't ``-um``. Keyed by
#: (lowercased) headword and checked before POS dispatch so the demonstrative
#: wins even when the top lexicon homograph is an adverb (e.g. ``hic``).
_PRONOMINAL = {
    "ille": "ille, illa, illud",
    "iste": "iste, ista, istud",
    "ipse": "ipse, ipsa, ipsum",
    "is": "is, ea, id",
    "hic": "hic, haec, hoc",
    "idem": "idem, eadem, idem",
    "qui": "qui, quae, quod",
    "quis": "quis, quid",
    "alius": "alius, alia, aliud",
    "alter": "alter, altera, alterum",
    "uter": "uter, utra, utrum",
    "neuter": "neuter, neutra, neutrum",
}


def pronominal_citation(lemma: str | None) -> str | None:
    """Citation for a demonstrative/relative/pronominal-adjective by lemma.

    Whitaker stores these inconsistently (the demonstrative ``hic`` arrives as a
    PRON with headword ``"h"``), so consumers that have the spaCy lemma should
    prefer this lemma-keyed lookup over reconstructing from the lexicon entry."""
    if not lemma:
        return None
    return _PRONOMINAL.get(lemma.lower())


def format_principal_parts(entry: dict) -> str | None:
    pos = entry.get("pos")
    hw = entry.get("headword")
    stems = entry.get("principal_parts") or []
    if not hw or not stems:
        return None
    if hw.lower() in _PRONOMINAL:
        return _PRONOMINAL[hw.lower()]
    if entry.get("defective"):
        cit = _format_defective(pos, hw, stems, entry.get("verb_kind"))
        if cit is not None:
            return cit
    if pos == "V":
        return _format_verb(
            hw, stems,
            entry.get("decl_which"), entry.get("decl_var"), entry.get("verb_kind"),
        )
    if pos == "N":
        return _format_noun(hw, stems, entry.get("gender"), entry.get("decl_which"))
    if pos in ("ADJ", "NUM"):
        return _format_adj(hw, stems, entry.get("decl_which"))
    return None


# ---------- defective paradigms (Whitaker stem1 == 'zzz') ----------


def _format_defective(
    pos: str | None, hw: str, stems: list[str], verb_kind: str | None,
) -> str | None:
    """Citation for entries Whitaker stores with a 'zzz' placeholder stem1.

    These have no present/positive first stem. Verbs are perfect-system-only
    (memini, odi, novi): the headword is already the perfect 1sg, so cite it
    with the perfect infinitive (perfect stem + 'isse') and, for non-impersonal
    verbs with a supine stem, the perfect participle ('osus sum'). Comparative-
    only adjectives (deterior, ulterior) cite the neuter ('-ius').
    """
    if pos == "V":
        perf_stem = stems[0]
        parts = [hw, perf_stem + "isse"]
        if verb_kind != "IMPERS" and len(stems) >= 2 and stems[1]:
            parts.append(stems[1] + "us sum")
        return ", ".join(parts)
    if pos in ("ADJ", "NUM"):
        return f"{hw}, -ius"
    return None


# ---------- verbs ----------

#: Whitaker (decl_which, decl_var) → conjugation number. The infinitive ending
#: only needs 1st/4th vs. the rest, and is built from stem2, so 3rd-io verbs
#: (capio → cap+ere) and plain 3rd (rego → reg+ere) share conj 3 cleanly.
_CONJ_BY_CODE = {(1, 1): 1, (8, 1): 1, (2, 1): 2, (3, 1): 3, (8, 3): 3, (3, 4): 4}

#: Closed-set irregular verbs whose citation can't be reconstructed from stems.
_IRREG_VERB = {
    "sum": "sum, esse, fui",
    "possum": "possum, posse, potui",
    "prosum": "prosum, prodesse, profui",
    "volo": "volo, velle, volui",
    "nolo": "nolo, nolle, nolui",
    "malo": "malo, malle, malui",
    "fio": "fio, fieri, factus sum",
    # eo's own entry is miscoded (1,1) like a denominal; its compounds are (6,1).
    "eo": "eo, ire, ii, itum",
}

#: Deponents whose Whitaker participle stem differs from the classical one.
_DEP_IRREG = {
    "morior": "morior, mori, mortuus sum",
    "orior": "orior, oriri, ortus sum",
}

#: Active present-infinitive ending by conjugation (2nd/3rd both -ere).
_INF_ACTIVE = {1: "are", 2: "ere", 3: "ere", 4: "ire"}
#: Deponent present-infinitive ending by conjugation.
_INF_DEPONENT = {1: "ari", 2: "eri", 3: "i", 4: "iri"}


def _stem2(stems: list[str]) -> str:
    return stems[1] if len(stems) >= 2 and stems[1] else stems[0]


def _perfect_and_supine(stems: list[str], conj: int, parts: list[str]) -> None:
    """Append the 3rd (perfect) and 4th (supine) principal parts in place."""
    if len(stems) >= 3 and stems[2]:
        perf = stems[2]
        # Whitaker stores the 1st-conj perfect syncopated ('amass'); restore '-av'.
        if conj == 1 and perf.endswith("ass"):
            perf = perf[:-3] + "av"
        parts.append(perf + "i")
    if len(stems) >= 4 and stems[3]:
        parts.append(stems[3] + "um")
    elif conj == 1 and len(stems) >= 3 and stems[2]:
        parts.append(stems[0] + "atum")  # regular 1st-conj supine (amatum)


def _format_verb(
    hw: str,
    stems: list[str],
    which: int | None = None,
    var: int | None = None,
    verb_kind: str | None = None,
) -> str | None:
    # Irregulars and productive irregular families first.
    if hw in _IRREG_VERB:
        return _IRREG_VERB[hw]
    if hw in _DEP_IRREG:
        return _DEP_IRREG[hw]
    if verb_kind in ("TO_BE", "TO_BEING"):
        return _format_esse(hw, stems)
    if hw.endswith("fero"):
        return _format_fero(hw, stems)
    if (which, var) == (6, 1):  # eo + compounds, queo/nequeo
        return _format_eo(hw, stems)

    conj = _CONJ_BY_CODE.get((which, var))
    if conj is None:
        # No usable Whitaker codes (e.g. synthetic callers): fall back to the
        # headword-shape heuristic + legacy construction.
        return _format_verb_legacy(hw, stems)

    if verb_kind == "DEP":
        parts = [hw, _stem2(stems) + _INF_DEPONENT[conj]]
        if len(stems) >= 3 and stems[2]:
            parts.append(stems[2] + "us sum")
        return ", ".join(parts)
    if verb_kind == "SEMIDEP":
        parts = [hw, _stem2(stems) + _INF_ACTIVE[conj]]
        if len(stems) >= 3 and stems[2]:
            parts.append(stems[2] + "us sum")
        return ", ".join(parts)

    parts = [hw, _stem2(stems) + _INF_ACTIVE[conj]]
    _perfect_and_supine(stems, conj, parts)
    return ", ".join(parts)


def _format_esse(hw: str, stems: list[str]) -> str:
    """``sum`` compounds: ``absum, abesse, afui`` (sum/possum/prosum hardcoded)."""
    parts = [hw, hw[:-3] + "esse"]
    if len(stems) >= 3 and stems[2]:
        parts.append(stems[2] + "i")
    return ", ".join(parts)


def _format_fero(hw: str, stems: list[str]) -> str:
    """``fero`` + compounds: athematic infinitive ``-ferre`` (not ``-ferere``)."""
    parts = [hw, hw[:-4] + "ferre"]
    if len(stems) >= 3 and stems[2]:
        parts.append(stems[2] + "i")
    if len(stems) >= 4 and stems[3]:
        parts.append(stems[3] + "um")
    return ", ".join(parts)


def _format_eo(hw: str, stems: list[str]) -> str:
    """``eo`` + compounds (Whitaker 6,1): infinitive ``-ire`` from stem2 + 're'."""
    parts = [hw, _stem2(stems) + "re"]
    if len(stems) >= 3 and stems[2]:
        parts.append(stems[2] + "i")
    if len(stems) >= 4 and stems[3]:
        parts.append(stems[3] + "um")
    return ", ".join(parts)


def _format_verb_legacy(hw: str, stems: list[str]) -> str | None:
    conj = _detect_conj(hw, stems)
    if conj is None:
        return None
    pres = stems[0]
    parts = [hw]

    # 2nd pp: infinitive
    if conj == 1:
        parts.append(pres + "are")
    elif conj == 2:
        parts.append(hw[:-2] + "ere")
    elif conj == 4:
        parts.append(hw[:-2] + "ire")
    else:  # 3
        parts.append(pres + "ere")

    # 3rd pp: perfect + 'i'
    if len(stems) >= 3 and stems[2]:
        perf = stems[2]
        # Whitaker stores 1st conj perfect as syncopated '-ass-' (from
        # amasse/amassem family). Rewrite back to the standard '-av-'.
        if conj == 1 and perf.endswith("ass"):
            perf = perf[:-3] + "av"
        parts.append(perf + "i")

    # 4th pp: supine + 'um' (or synthesize for regular 1st conj)
    if len(stems) >= 4 and stems[3]:
        parts.append(stems[3] + "um")
    elif conj == 1:
        # Regular 1st conj supine: pres-stem + 'atum' (amatum, portatum)
        parts.append(pres + "atum")

    return ", ".join(parts)


def _detect_conj(hw: str, stems: list[str]) -> int | None:
    """Return 1, 2, 3, or 4 for the detected conjugation, or None if
    the headword doesn't look like a verb first-person form.
    """
    if hw.endswith("eo"):
        return 2
    if hw.endswith("io"):
        # audio vs capio (3rd-io) can't be split reliably without class
        # metadata. Default to 4th — most common and makes audire, etc.
        return 4
    if hw.endswith("o"):
        pres = stems[0] if stems else ""
        perf = stems[2] if len(stems) >= 3 else ""
        if perf and _is_first_conj_perfect(pres, perf):
            return 1
        return 3
    return None


def _is_first_conj_perfect(pres: str, perf: str) -> bool:
    """1st conj perfect is typically pres + 'av' (amav) or pres + 'ass'
    (syncopated, what Whitaker stores as 'amass'). 3rd conj perfects
    either repeat the present stem, add '-s-' (sigmatic: scrib→scrips),
    or lengthen the stem vowel.
    """
    if perf == pres:
        return False
    if perf.startswith(pres):
        suffix = perf[len(pres):]
        return suffix in {"av", "ass", "at"}
    return False


# ---------- nouns ----------


def _format_noun(hw: str, stems: list[str], gender: str | None, decl: int | None) -> str:
    gen = _noun_genitive(hw, stems, decl)
    gender_tag = GENDER_ABBREV.get(gender) if gender else None
    if gender_tag:
        return f"{hw}, {gen}, {gender_tag}"
    return f"{hw}, {gen}"


def _noun_genitive(hw: str, stems: list[str], decl: int | None) -> str:
    stem2 = stems[1] if len(stems) >= 2 else stems[0]
    if decl == 1:
        return hw[:-1] + "ae" if hw.endswith("a") else hw + "ae"
    if decl == 2:
        if hw.endswith("us") or hw.endswith("um"):
            return hw[:-2] + "i"
        if hw.endswith("er") or hw.endswith("ir"):
            if stem2 and not stem2.endswith("er") and stem2.endswith("r"):
                return stem2 + "i"
            return hw + "i"
        return stem2 + "i"
    if decl == 3:
        return stem2 + "is"
    if decl == 4:
        if hw.endswith("u"):
            return hw + "s"   # genu → genus
        return hw[:-2] + "us" if hw.endswith("us") else stem2 + "us"
    if decl == 5:
        return hw[:-2] + "ei" if hw.endswith("es") else stem2 + "ei"
    # Fallback: headword-shape heuristics (no decl_which available)
    if hw.endswith("a"):
        return hw + "e"
    if hw.endswith("us") or hw.endswith("um"):
        return hw[:-2] + "i"
    if hw.endswith("er") or hw.endswith("ir"):
        if stem2 and not stem2.endswith("er") and stem2.endswith("r"):
            return stem2 + "i"
        return hw + "i"
    return stem2 + "is"


# ---------- adjectives ----------


def _format_adj(hw: str, stems: list[str], decl_which: int | None = None) -> str:
    if decl_which == 9:
        return hw
    if hw.endswith("us"):
        return f"{hw}, -a, -um"
    if hw.endswith("er"):
        # pulcher → pulchra, pulchrum (drops e) or liber → libera, liberum.
        # Heuristic: use stem2 to decide.
        stem2 = stems[1] if len(stems) >= 2 else stems[0]
        if stem2 and not stem2.endswith("er") and stem2.endswith("r"):
            return f"{hw}, {stem2}a, {stem2}um"
        return f"{hw}, {hw}a, {hw}um"
    if hw.endswith("is"):
        return f"{hw}, -e"
    # 1-ending 3rd decl adj: felix → felix, felicis
    stem2 = stems[1] if len(stems) >= 2 else stems[0]
    return f"{hw}, {stem2}is"
