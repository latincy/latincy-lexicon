"""Latin prefix-assimilation variants.

Whitaker's Words records compound verbs/nouns with their etymological,
*un-assimilated* prefixes (``adcedo`` = ad + cedo), whereas Lewis & Short
indexes the classical *assimilated* spelling (``accedo``). When a direct
headword join misses, we retry with the assimilated form produced here.

The table maps an un-assimilated word-initial cluster (prefix-final consonant
+ stem-initial consonant) to its assimilated spelling. It is intentionally
conservative — only well-established assimilations — and is used purely as a
fallback, so a spurious variant simply fails to match and costs nothing.
"""

from __future__ import annotations

# Word-initial cluster (un-assimilated) → assimilated cluster.
_ASSIMILATIONS: dict[str, str] = {
    # ad-
    "adc": "acc",
    "adf": "aff",
    "adg": "agg",
    "adl": "all",
    "adn": "ann",
    "adp": "app",
    "adq": "acq",
    "adr": "arr",
    "ads": "ass",
    "adt": "att",
    # con-
    "conl": "coll",
    "conr": "corr",
    "conm": "comm",
    # in-
    "inl": "ill",
    "inr": "irr",
    "inm": "imm",
    "inb": "imb",
    "inp": "imp",
    # sub-
    "subc": "succ",
    "subf": "suff",
    "subg": "sugg",
    "subm": "summ",
    "subp": "supp",
    "subr": "surr",
    # ob-
    "obc": "occ",
    "obf": "off",
    "obg": "ogg",
    "obp": "opp",
    # ex-, dis-
    "exf": "eff",
    "disf": "diff",
}


def assimilated_forms(word: str) -> list[str]:
    """Return assimilated spelling variants of ``word`` (empty if none apply).

    Assumes a normalized (u/i-folded, lowercase) input. At most one cluster
    matches a given word start, so the result holds zero or one variant.
    """
    variants: list[str] = []
    for cluster, assimilated in _ASSIMILATIONS.items():
        if len(word) > len(cluster) and word.startswith(cluster):
            variants.append(assimilated + word[len(cluster):])
    return variants
