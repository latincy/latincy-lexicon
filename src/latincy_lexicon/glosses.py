"""Utilities for parsing DICTLINE meaning fields into glosses."""

from __future__ import annotations


def split_glosses(meaning: str) -> list[str]:
    if not meaning:
        return []

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
            piece = meaning[start:i].strip()
            if piece:
                pieces.append(piece)
            start = i + 1
    tail = meaning[start:].strip()
    if tail:
        pieces.append(tail)
    return pieces
