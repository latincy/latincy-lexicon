"""Utilities for parsing DICTLINE meaning fields into glosses."""

from __future__ import annotations

import re

# WW grammar codes: subjunctive/infinitive constructions and case-government
# markers. A trailing paren whose content contains one of these is a syntactic
# usage note, not lexical content — stripped from the display gloss.
_WW_SYNTAX_RE = re.compile(r"\b(ACC|GEN|DAT|ABL|NOM|VOC|LOC|SUB|SUBJ|INF)\b")

# Bibliographic / lexicographic source markers WW appends to glosses, usually
# in a trailing parenthesis: "epitomize (Souter)", "copious (L+S, Late Latin)".
# These are citations, not lexical content — extracted into entry metadata and
# stripped from the display gloss. Curated allowlist (case-sensitive): period /
# register codes like (Ecc), (Cal) and the L:/W:/E: prefixes are deliberately
# excluded — they mark usage, not a source.
_SOURCE_TOKENS = [
    "L+S", "L&S", "Du Cange", "Souter", "Plinius", "Pliny", "Latham",
    "Erasmus", "Collins", "Vulgate", "Douay", "Nelson", "Whitaker",
    "Bee", "Cas", "Def", "OLD", "OED", "TLL",
]
# Longest-first so multi-word / overlapping tokens match before substrings.
_SOURCE_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(s) for s in sorted(_SOURCE_TOKENS, key=len, reverse=True))
    + r")\b"
)
_PAREN_GROUP_RE = re.compile(r"\(([^()]*)\)")


def _clean_piece(piece: str) -> str:
    """Strip WW leading formatting artifacts from a single gloss piece.

    Removes a leading pipe (``|``) marker and a leading dash-space (``- ``)
    prefix that WW prepends to some prefix/preposition glosses. A leading dash
    that is *not* followed by whitespace (``-ing``, ``-able``) is a genuine
    suffix gloss and is preserved.
    """
    piece = piece.strip()
    if piece.startswith("|"):
        piece = piece.lstrip("|").strip()
    if piece.startswith("- "):
        piece = piece[2:].strip()
    return piece


def split_glosses(meaning: str, clean: bool = True) -> list[str]:
    """Split a DICTLINE meaning into gloss pieces on bracket/paren-aware ``;``.

    With ``clean=True`` (default) each piece is run through ``_clean_piece`` to
    drop WW leading artifacts (pipe markers, dash-space). Pass ``clean=False``
    for the raw, verbatim original senses — used to capture ``gloss_orig``.
    """
    if not meaning:
        return []

    def _finish(raw: str) -> str:
        return _clean_piece(raw) if clean else raw.strip()

    pieces: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(meaning):
        if ch in "[(":
            depth += 1
        elif ch in "])":
            if depth > 0:
                depth -= 1
        elif ch == ";" and depth == 0:
            piece = _finish(meaning[start:i])
            if piece:
                pieces.append(piece)
            start = i + 1
    tail = _finish(meaning[start:])
    if tail:
        pieces.append(tail)
    return pieces


def extract_sources(gloss: str) -> tuple[str, list[str]]:
    """Split a gloss into (clean_gloss, sources).

    Pulls bibliographic source citations (see ``_SOURCE_TOKENS``) out of a
    trailing parenthesis. Two shapes are handled:

    - whole-paren citation — ``"epitomize (Souter)"`` → ``("epitomize",
      ["Souter"])`` — the entire paren is dropped.
    - embedded citation — ``"song-bird (thistle/gold finch L+S)"`` →
      ``("song-bird (thistle/gold finch)", ["L+S"])`` — only the source token
      is removed, the remaining content kept and re-punctuated.

    Every parenthesis group is scanned, so mid-gloss citations
    (``"parable (L+S), allegory"`` → ``("parable, allegory", ["L+S"])``) and
    inner groups of nested parens are handled too. Source tokens are only
    extracted from inside parentheses — a bare ``"Pliny"`` (the gloss of the
    proper noun *Plinius*) is content and left untouched. Brackets ``[...]``
    are not scanned. Sources are de-duplicated in first-seen order.
    """
    sources: list[str] = []

    def _replace(m: "re.Match[str]") -> str:
        inner = m.group(1)
        found = _SOURCE_RE.findall(inner)
        if not found:
            return m.group(0)
        for s in found:
            if s not in sources:
                sources.append(s)
        remainder = _SOURCE_RE.sub("", inner)
        remainder = re.sub(r"\s+", " ", remainder).strip(" ,;")
        return f"({remainder})" if remainder else ""

    clean = _PAREN_GROUP_RE.sub(_replace, gloss)
    if not sources:
        return gloss, []

    # Tidy artifacts left by dropped groups: stray spaces, space-before-punct,
    # doubled separators.
    clean = re.sub(r"\s+", " ", clean)
    clean = re.sub(r"\s+([,;)])", r"\1", clean)
    clean = re.sub(r"\(\s+", "(", clean)
    clean = re.sub(r"([,;])\s*\1", r"\1", clean)
    clean = clean.strip().strip(" ,;")
    return clean, sources


def strip_usage_note(gloss: str) -> str:
    """Strip a trailing WW syntax/cross-reference paren from a gloss string.

    Whitaker appends non-lexical annotations to the end of meaning fields:

    - syntactic usage — ``(ne + SUB = lest; ...)``, case government ``(w/DAT)``,
      restrictions ``(only NOM S)`` — flagged by a grammar code (see
      ``_WW_SYNTAX_RE``);
    - derivational cross-references — ``(adeo => go to)`` — flagged by an
      ``=>`` / ``->`` arrow.

    Such a trailing ``(...)`` group is removed. Nothing is stripped when there
    is no gloss content before the paren (a whole-paren note — category E) or
    when the paren is a domain/register annotation like ``(of)`` / ``(gram.)``.
    """
    m = re.match(r"^(.*\S)\s+\(([^)]+)\)\s*$", gloss)
    if m:
        content = m.group(2)
        if _WW_SYNTAX_RE.search(content) or "=>" in content or "->" in content:
            return m.group(1)
    return gloss
