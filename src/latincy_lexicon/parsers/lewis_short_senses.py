"""Perseus L&S TEI → structured **sense tree** parser.

The companion to ``parsers/lewis_short.py``: where that parser flattens each
``<entryFree>`` to a single article-text blob (the dictionary-panel view), this one
reconstructs the entry's **sense structure**. Perseus L&S TEI is P4 (no XML
namespace): ``<sense>`` elements are flat siblings whose tree position is encoded in
``level`` (int depth) + ``n`` (label: ``I``/``II`` → ``A``/``B`` → ``1`` → Greek
``(a)(b)``). We rebuild the tree with a level-stack, collapse purely-syntactic
subdivisions, mint sense IRIs, and keep the Perseus xml:id (``sameAs``) and CTS
``bibl`` citations (``evidence``).

Construction (syntactic-only) subdivisions are dropped from the label space: the
Greek-letter variants ``(a)(b)(g)(d)…`` and nodes whose own gloss is a bare
grammatical marker (``inf.``, ``gen.``, ``dat.``, ``absol.``, ``perf.``…). A
structural node with an *empty* gloss is kept (it carries meaning children).

Stdlib only (``re`` + ``xml.etree``); no runtime dependency added. Parsing is
build-time (the built sense store is consumed at runtime), but this module ships in
the wheel so the ``lewis_short`` component and downstream packages can parse on demand.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

#: Capital letters that are also Roman numerals — genuinely ambiguous depth.
_AMBIGUOUS_CAPS = set("IVXLCDM")


def sense_depth(n: str, level_attr: int) -> int:
    """Depth of a sense from its label's character class (L&S nesting convention:
    Roman ``I``/``II`` → 1, capital ``A``/``B`` → 2, arabic ``1``/``2`` → 3,
    lowercase ``a``/``b`` → 4).

    The Perseus TEI ``level`` attribute is sometimes wrong — e.g. *pater*'s F/G/H
    are tagged ``level=1`` though they continue II's A–E at level 2, and *appello*'s
    ``A. 1.`` is tagged ``level=1`` though A is a capital sub-sense — so the label
    class is the more reliable signal. ``level_attr`` only breaks the genuine
    Roman/Capital ambiguity (``I V X L C D M`` are both numerals and letters).
    """
    tok = re.split(r"[\s.()]+", (n or "").strip(), maxsplit=1)[0]
    if not tok:
        return level_attr
    if tok.isdigit():
        return 3
    if len(tok) == 1 and tok.islower():
        return 4
    if len(tok) == 1 and tok.isupper():
        return level_attr if tok in _AMBIGUOUS_CAPS else 2
    if re.fullmatch(r"[IVXLCDM]+", tok):  # multi-char Roman (II, III, IV, …)
        return 1
    return level_attr

#: Greek-letter labels L&S uses for construction/government variants.
GREEK_LETTERS = {f"({x})" for x in ("a", "b", "g", "d", "e", "z", "h", "th")}

#: Bare grammatical markers that signal a syntactic (not semantic) subdivision.
CONSTRUCTION_MARKERS = {
    "inf", "gen", "dat", "acc", "abl", "voc", "nom", "absol", "impers", "perf",
    "praes", "fut", "subj", "imp", "part", "sup", "ger", "pass", "act", "neutr",
    "pred", "adv", "sing", "plur", "constr", "trans", "intrans", "reflex",
    # positional / tense markers that lead a sense without giving its meaning
    "pres", "fin",
}

SENSE_IRI = "https://w3id.org/latincy/lemma/{slug}/sense/{path}"
#: Perseus Hopper L&S edition (1879 Lewis & Short). entry= takes the headword key
#: (with homograph digit, e.g. dico1). Resolves to the real L&S article today.
PERSEUS_ENTRY_URL = "https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0059:entry={key}"


def perseus_entry_url(entry_key: str) -> str:
    """Resolvable Perseus L&S entry URL for a headword key (e.g. ``narro``, ``dico1``)."""
    return PERSEUS_ENTRY_URL.format(key=entry_key)


#: LiLa Knowledge Base resource for the Lewis & Short LLOD edition (cf. Mambrini &
#: Passarotti, "Linking the Lewis & Short Dictionary to the LiLa KB", CEUR Vol-3033,
#: paper27). SPARQL-verified scheme (endpoint
#: https://lila-erc.eu/sparql/lila_knowledge_base/sparql): nodes live under an
#: ``…/id/{class}/`` path. The per-SENSE node keeps the FULL Perseus id including the
#: ``.k`` suffix — ``…/id/LexicalSense/n30406.0`` — while the entry node drops it —
#: ``…/id/LexicalEntry/n30406``. We hold per-sense ids, so we attach the sense node.
LILA_LS_BASE = "http://lila-erc.eu/data/lexicalResources/LewisShort/id/"


def lila_sense_iri(perseus_ls_id: str) -> str | None:
    """Resolving LiLa L&S *sense*-node IRI for a Perseus L&S sense xml:id (or ``None``).

    The Perseus sense id ``n30406.0`` maps to the LiLa LexicalSense node
    ``…/LewisShort/id/LexicalSense/n30406.0`` (the FULL id, including the ``.k``
    suffix, is kept). SPARQL-verified against the LiLa KB endpoint.
    """
    if not perseus_ls_id:
        return None
    return LILA_LS_BASE + "LexicalSense/" + perseus_ls_id


#: Backward-compatible alias — call sites historically used ``lila_entry_iri``.
lila_entry_iri = lila_sense_iri


def sense_tree_orphans(levels: list[str]) -> list[str]:
    """Return sense levels whose parent path is missing — an L&S-tree validator.

    A well-formed tree has every non-root level (e.g. ``II.F``) preceded by its
    parent (``II``). Orphans signal a depth bug like the *pater* F/G/H regression
    (capital-letter senses stranded at the root). Returns ``[]`` when orderly.
    """
    present = set(levels)
    return [
        lv for lv in levels
        if "." in lv and ".".join(lv.split(".")[:-1]) not in present
    ]


def _norm_marker(gloss: str) -> str:
    return gloss.strip().lower().rstrip(".").strip()


def is_construction(n: str, gloss: str) -> bool:
    """True if a sense is a purely-syntactic subdivision to collapse."""
    if n in GREEK_LETTERS:
        return True
    g = _norm_marker(gloss)
    if not g:
        return False  # empty structural node — keep (carries children)
    first = g.replace(".", " ").split(",")[0].split()[0] if g else ""
    return (g in CONSTRUCTION_MARKERS or first in CONSTRUCTION_MARKERS) and len(g) <= 14


def _own_gloss(sense: ET.Element) -> str:
    """The sense's lead italic gloss — the first ``<hi rend="ital">`` in the
    sense's own text (sub-senses and example-quote italics excluded). In L&S the
    headword definition leads; later italics are example translations."""
    found: list[str] = []

    def rec(el: ET.Element) -> None:
        for c in el:
            if found or c.tag == "sense":  # stop at first hit; skip sub-senses
                continue
            if c.tag == "hi" and c.get("rend") == "ital" and (c.text or "").strip():
                found.append(c.text.strip())
                return
            rec(c)

    rec(sense)
    return found[0].strip(" ,;:") if found else ""


def _citations(sense: ET.Element) -> list[str]:
    """CTS citation IRIs (bibl @n) attached to this sense, sub-senses excluded."""
    out: list[str] = []

    def rec(el: ET.Element) -> None:
        for c in el:
            if c.tag == "sense":
                continue
            if c.tag == "bibl":
                n = c.get("n") or ""
                if n.startswith("urn:cts:"):
                    out.append(n)
            rec(c)

    rec(sense)
    return out


def _citation_trs(sense: ET.Element) -> dict[str, str]:
    """``{bibl-urn: per-citation translation}`` from ``<cit>`` blocks under this
    sense (sub-senses excluded). L&S pairs a cited ``<quote>`` with its
    ``<trans><tr>`` English rendering — the gloss that fits *that* attestation, not
    the sense head (e.g. latus II.A Lael. 1.1 → "never left his side", not the head
    "to attack the sides")."""
    out: dict[str, str] = {}

    def rec(el: ET.Element) -> None:
        for c in el:
            if c.tag == "sense":
                continue
            if c.tag == "cit":
                bibl = c.find("bibl")
                tr = c.find(".//tr")
                if bibl is not None and tr is not None:
                    urn = bibl.get("n") or ""
                    txt = "".join(tr.itertext()).strip(" ,;:")
                    if urn.startswith("urn:cts:") and txt:
                        out[urn] = txt
                continue  # cit fully handled; don't double-walk its children
            rec(c)

    rec(sense)
    return out


#: Latin function words + markers that don't constitute a display *meaning*.
_LATIN_FUNC = {"ab", "ex", "de", "in", "ad", "cum", "e", "a", "ob", "per", "pro",
               "sub", "sine", "ut", "ne", "et", "que", "ac", "aut"}
#: Grammatical / part-of-speech abbreviations L&S leads entries with (e.g.
#: "v. n. irreg.", "adj.", "freq.") — markers, never a display meaning.
_POS_ABBREV = {"irreg", "freq", "dep", "adj", "adv", "conj", "prep", "interj",
               "num", "pron", "collat", "contr", "abbrev", "prop", "propr",
               "demonstr", "relat", "indef", "interrog", "voc", "dim", "patr"}
_DISPLAY_STOP = (CONSTRUCTION_MARKERS | _LATIN_FUNC | _POS_ABBREV
                 | {"med", "sync", "imper", "id", "ib"})
_ABBREV_RE = re.compile(r"^[A-Z][A-Za-z]{0,4}\.$")  # citation/author abbrev: Aes., Cic.


def _is_meaning(gloss: str) -> bool:
    """True if a gloss reads as an English *meaning*, not a marker/abbreviation."""
    g = (gloss or "").strip()
    if not g or _ABBREV_RE.match(g):
        return False
    words = [w.rstrip(".") for w in re.split(r"[\s,;:]+", g.lower()) if w]
    return any(len(w) >= 3 and w not in _DISPLAY_STOP for w in words)


def _meaning_gloss(sense: ET.Element) -> str:
    """First *substantive* lead italic (skipping markers), for display."""
    found: list[str] = []

    def rec(el: ET.Element) -> None:
        for c in el:
            if c.tag == "sense":  # the sense's own italics, not sub-senses'
                continue
            if c.tag == "hi" and c.get("rend") == "ital" and (c.text or "").strip():
                found.append(c.text.strip(" ,;:"))
            rec(c)

    rec(sense)
    return next((g for g in found if _is_meaning(g)), "")


def parse_entry(entry_xml: str, lemma_slug: str, perseus_url: str | None = None) -> list[dict]:
    """Parse one ``<entryFree>`` into a filtered, IRI-minted list of sense dicts.

    Each sense's ``sameAs`` carries: ``perseus_ls_id`` (the L&S xml:id),
    ``perseus`` (the resolvable Hopper entry URL, if given), and ``lila`` (the
    LiLa L&S sense node).
    """
    root = ET.fromstring(entry_xml)
    # entry's primary meaning — first substantive gloss anywhere (even in a
    # collapsed head-note), the display fallback for weak top-level senses.
    entry_primary = next(
        (m for s in root.iter("sense") if (m := _meaning_gloss(s))), ""
    )

    senses: list[dict] = []
    by_path: dict[str, dict] = {}
    stack: list[tuple[int, str]] = []  # (level, label) of kept meaning ancestors
    for s in root.iter("sense"):
        n = (s.get("n") or "").strip()
        level = sense_depth(n, int(s.get("level") or 1))  # label class > buggy TEI level
        gloss = _own_gloss(s)
        # pop to this depth so the path reflects current nesting
        while stack and stack[-1][0] >= level:
            stack.pop()
        if is_construction(n, gloss):
            continue  # collapse: children attach to the current parent
        # path segment = the label's leading token, so malformed n like "A. 1."
        # (appello) yields a clean "A" rather than a spaced, period-laden segment.
        label = n.split()[0].rstrip(".") if n.split() else n
        stack.append((level, label))
        path = ".".join(x[1] for x in stack)
        meaning = _meaning_gloss(s)
        if path in by_path:
            # L&S splits one sense across repeated <sense n="…"> siblings (e.g.
            # deduco's three "I"s); merge rather than emit duplicate paths. The
            # stack already points here, so later sub-senses nest correctly.
            ex = by_path[path]
            if not _is_meaning(ex["gloss"]) and gloss:
                ex["gloss"] = gloss
            if meaning and not ex["_meaning"]:
                ex["_meaning"] = meaning
            ex["citations"].extend(c for c in _citations(s) if c not in ex["citations"])
            ex["citation_tr"].update(_citation_trs(s))
            continue
        d = {
            "id": SENSE_IRI.format(slug=lemma_slug, path=path),
            "level": path,
            "n": n,
            "gloss": gloss,
            "_meaning": meaning,
            "sameAs": {
                "perseus_ls_id": s.get("id") or "",
                "perseus": perseus_url,
                "lila": lila_entry_iri(s.get("id") or ""),  # resolving LiLa L&S sense node
            },
            "citations": _citations(s),
            "citation_tr": _citation_trs(s),  # {urn: per-citation gloss} for the WSD rung
        }
        by_path[path] = d
        senses.append(d)

    # display_gloss: own meaning; else (leaves only) inherit the nearest substantive
    # ancestor; else the entry's primary meaning. Structural parents stay empty so
    # the reader shows "(structural — meaning in sub-senses)".
    paths = {d["level"] for d in senses}
    meaning_of = {d["level"]: d["_meaning"] for d in senses}  # snapshot for lookups
    def _has_children(p):
        return any(o != p and o.startswith(p + ".") for o in paths)

    for d in senses:
        if d["_meaning"]:
            d["display_gloss"] = d["_meaning"]
        elif not d["gloss"] and _has_children(d["level"]):
            d["display_gloss"] = ""  # truly empty structural node (no own italic)
        else:
            # a weak gloss (markers/preps like "ab, ex") or an empty leaf inherits
            # the nearest substantive ancestor, else the entry's primary meaning.
            dg = ""
            segs = d["level"].split(".")
            for i in range(len(segs) - 1, 0, -1):
                anc = meaning_of.get(".".join(segs[:i]))
                if anc:
                    dg = anc
                    break
            d["display_gloss"] = dg or entry_primary
    for d in senses:
        d.pop("_meaning", None)
    return senses
