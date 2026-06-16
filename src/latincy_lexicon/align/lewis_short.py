"""Align latincy-lexicon lemmas to Lewis & Short entries.

For each lexicon entry (already keyed by ``normalized_headword``) we look up the
candidate L&S ids in ``lewis_short_index.json``. Most keys have a single
candidate (a trivial join); ~2,000 keys are homographs with several candidates,
which we *rank* — never drop — by part-of-speech compatibility.

L&S exposes part-of-speech inconsistently: ``<pos>`` is populated mainly for
adjectives/verbs/adverbs, while nouns are marked only by ``<gen>`` (m./f./n.).
We fold both into a coarse class set and score candidates against the WW POS.

Macron-based disambiguation (``<orth>`` vowel length vs a macronized surface
form) is a planned second signal; this module degrades gracefully without it.
"""

from __future__ import annotations

from latincy_lexicon.align.assimilate import assimilated_forms

# Coarse POS classes shared by both sides of the join.
# An L&S abbreviation may map to several classes (e.g. "num. adj." → num + adj).
_LS_POS_TO_CLASSES: dict[str, set[str]] = {
    "adj.": {"adj"},
    "P. a.": {"adj", "verb"},          # participial adjective
    "num. adj.": {"num", "adj"},
    "pron. adj.": {"pron", "adj"},
    "adv.": {"adv"},
    "adv. num.": {"adv", "num"},
    "prep.": {"prep"},
    "interj.": {"interj"},
    "v. a.": {"verb"},
    "v. n.": {"verb"},
    "v. dep.": {"verb"},
    "v. n. and a.": {"verb"},
    "v. a. and n.": {"verb"},
    "v. freq. a.": {"verb"},
    "v. freq. a. and n.": {"verb"},
}

_GEN_VALUES = {"m.", "f.", "n.", "comm.", "com.", "m. and f.", "f. and m."}

_WW_POS_TO_CLASSES: dict[str, set[str]] = {
    "N": {"noun"},
    "V": {"verb"},
    "ADJ": {"adj"},
    "ADV": {"adv"},
    "PREP": {"prep"},
    "INTERJ": {"interj"},
    "CONJ": {"conj"},
    "PRON": {"pron"},
    "NUM": {"num"},
    "VPAR": {"adj", "verb"},
    "SUPINE": {"verb"},
}


def ls_pos_classes(entry: dict) -> set[str]:
    """Coarse POS class set for an L&S store entry (from ``pos``, then ``gen``)."""
    classes = set(_LS_POS_TO_CLASSES.get((entry.get("pos") or "").strip(), set()))
    if not classes and (entry.get("gen") or "").strip() in _GEN_VALUES:
        classes.add("noun")
    return classes


def ww_pos_classes(pos: str) -> set[str]:
    """Coarse POS class set for a WW part-of-speech code."""
    return set(_WW_POS_TO_CLASSES.get((pos or "").strip(), set()))


def _score(ww_classes: set[str], entry: dict) -> int:
    """Compatibility score: 2 = POS classes intersect, 1 = candidate POS unknown, 0 = conflict."""
    ls_classes = ls_pos_classes(entry)
    if ww_classes & ls_classes:
        return 2
    if not ls_classes:
        return 1  # L&S gives no usable POS signal — don't penalize, don't reward
    return 0


def rank_ls_candidates(ww_pos: str, candidate_ids: list[str], store: dict) -> list[str]:
    """Rank candidate L&S ids best-first for a given WW POS. Drops nothing.

    Stable on ties, preserving document/homograph order so identical scores keep
    their natural L&S numbering.
    """
    ww_classes = ww_pos_classes(ww_pos)
    return sorted(
        candidate_ids,
        key=lambda cid: -_score(ww_classes, store.get(cid, {})),
    )


def align_lexicon_to_ls(
    lexicon: dict[str, list[dict]],
    ls_index: dict[str, list[str]],
    ls_store: dict[str, dict],
) -> tuple[dict[str, list[dict]], dict]:
    """Attach a ranked ``ls_ids`` list to every lexicon entry in place.

    Returns ``(lexicon, stats)``.
    """
    stats = {
        "entries_total": 0,
        "entries_aligned": 0,
        "entries_unmatched": 0,
        "entries_disambiguated": 0,  # had >1 candidate
        "entries_assimilated": 0,    # matched only via an assimilated variant
    }
    for key, entries in lexicon.items():
        for entry in entries:
            stats["entries_total"] += 1
            norm = entry.get("normalized_headword", key)
            candidates = ls_index.get(norm, [])
            assimilated = False
            if not candidates:
                # Fall back to the classical assimilated spelling (adcedo→accedo).
                for variant in assimilated_forms(norm):
                    if variant in ls_index:
                        candidates = ls_index[variant]
                        assimilated = True
                        break
            ranked = rank_ls_candidates(entry.get("pos", ""), candidates, ls_store)
            entry["ls_ids"] = ranked
            if ranked:
                stats["entries_aligned"] += 1
                if assimilated:
                    stats["entries_assimilated"] += 1
                if len(ranked) > 1:
                    stats["entries_disambiguated"] += 1
            else:
                stats["entries_unmatched"] += 1
    return lexicon, stats
