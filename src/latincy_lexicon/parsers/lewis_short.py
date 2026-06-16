"""Parser for the Perseus Lewis & Short TEI (``lat.ls.perseus-eng2.xml``).

The file is TEI P4 (CC BY-SA 4.0): a flat sequence of ``<entryFree>`` elements,
each with a stable ``id`` and a homograph-numbered ``key``. Entries are
independently well-formed and use only standard XML entities, so the whole
document need not be parsed at once — we scan for entry blocks and parse each
with the stdlib ``xml.etree`` (no lxml, no new runtime dependency).

Parsing is build-time only; end users consume the exported JSON.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator

from latincy_lexicon.models import LewisShortEntry

# Each <entryFree ...> ... </entryFree> block, non-greedy so adjacent entries
# don't merge. entryFree elements are not nested in this source.
_ENTRY_RE = re.compile(r"<entryFree\b.*?</entryFree>", re.DOTALL)

# Collapse runs of whitespace introduced by flattening mixed content.
_WS_RE = re.compile(r"\s+")


def _first_text(elem: ET.Element, tag: str) -> str:
    """Return the flattened text of the first ``tag`` child, or ""."""
    child = elem.find(tag)
    if child is None:
        return ""
    return _flatten(child)


def _flatten(elem: ET.Element) -> str:
    """Flatten an element's mixed content to whitespace-normalized plain text."""
    return _WS_RE.sub(" ", "".join(elem.itertext())).strip()


def _parse_entry(block: str) -> LewisShortEntry | None:
    try:
        elem = ET.fromstring(block)
    except ET.ParseError:
        return None
    key = elem.get("key")
    entry_id = elem.get("id")
    if not key or not entry_id:
        return None
    return LewisShortEntry(
        id=entry_id,
        key=key,
        orth=_first_text(elem, "orth"),
        pos=_first_text(elem, "pos"),
        gen=_first_text(elem, "gen"),
        itype=_first_text(elem, "itype"),
        text=_flatten(elem),
    )


def iter_lewis_short(xml_text: str) -> Iterator[LewisShortEntry]:
    """Yield :class:`LewisShortEntry` for each ``<entryFree>`` in ``xml_text``."""
    for match in _ENTRY_RE.finditer(xml_text):
        entry = _parse_entry(match.group(0))
        if entry is not None:
            yield entry


def parse_lewis_short(path: str | Path) -> list[LewisShortEntry]:
    """Parse the Lewis & Short TEI file into a list of entries."""
    xml_text = Path(path).read_text(encoding="utf-8")
    return list(iter_lewis_short(xml_text))
