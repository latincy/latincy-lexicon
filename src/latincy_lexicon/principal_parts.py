"""Reconstruct textbook-style principal parts from Whitaker stems.

Whitaker's Words stores noun/verb/adjective stems (e.g., ``["scrib",
"scrib", "scrips", "script"]``) rather than citation forms like
``scribo, scribere, scripsi, scriptum``. The lexicon payload exposes
``decl_which`` (the declension/conjugation number) which drives noun
genitive formation; verb conjugation is still inferred from headword
shape and stem patterns.
"""

from __future__ import annotations

GENDER_ABBREV = {"M": "m.", "F": "f.", "N": "n."}


def format_principal_parts(entry: dict) -> str | None:
    pos = entry.get("pos")
    hw = entry.get("headword")
    stems = entry.get("principal_parts") or []
    if not hw or not stems:
        return None
    if pos == "V":
        return _format_verb(hw, stems)
    if pos == "N":
        return _format_noun(hw, stems, entry.get("gender"), entry.get("decl_which"))
    if pos == "ADJ":
        return _format_adj(hw, stems)
    return None


# ---------- verbs ----------


def _format_verb(hw: str, stems: list[str]) -> str | None:
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


def _format_adj(hw: str, stems: list[str]) -> str:
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
