"""Build the Lewis & Short JSON stores from the Perseus TEI.

Produces files kept separate from ``lexicon.json`` (and lazily loaded at runtime)
because the entry/sense data is large:

- ``lewis_short.json``        — ``{id: {key, orth, pos, itype, text}}`` (entry store)
- ``lewis_short_index.json``  — ``{normalized_headword: [id, ...]}`` for lookup,
  grouping homographs under one normalized key.
- ``lewis_short_senses.json`` — ``{id: {key, slug, iri_slug, senses: [sense, ...]}}`` (sense
  store; see ``parsers.lewis_short_senses`` for the per-sense shape).
"""

from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

from latincy_lexicon.align.normalize import normalize_latin
from latincy_lexicon.parsers.lewis_short import (
    _ENTRY_RE,
    _parse_entry,
    parse_lewis_short,
)
from latincy_lexicon.parsers.lewis_short_senses import (
    parse_entry_full,
    perseus_entry_url,
)

STORE_FILENAME = "lewis_short.json"
INDEX_FILENAME = "lewis_short_index.json"
SENSES_FILENAME = "lewis_short_senses.json"

# Provenance header written under the reserved ``_meta`` key of the sense store, so
# the licence and source travel with the file if it is redistributed on its own.
# ``load_senses`` strips it, so consumers going through the loader never see it.
SENSES_META_KEY = "_meta"
SENSES_SOURCE = {
    "title": "A Latin Dictionary",
    "authors": ["Charlton T. Lewis", "Charles Short"],
    "original_publication": "Oxford: Clarendon Press, 1879",
    "digital_edition": "Perseus Project, Tufts University (Trustees of Tufts University)",
    "url": "https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0059",
    "file": "lat.ls.perseus-eng2.xml",
    "license": "CC-BY-SA-4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
}


def build_lewis_short_store(
    tei_path: str | Path,
    output_dir: str | Path,
) -> dict:
    """Parse the L&S TEI and write the store + normalized index.

    Returns a stats dict: ``{"entries": int, "index_keys": int}``.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    entries = parse_lewis_short(tei_path)

    store: dict[str, dict] = {}
    index: dict[str, list[str]] = defaultdict(list)
    for e in entries:
        store[e.id] = {
            "key": e.key,
            "orth": e.orth,
            "pos": e.pos,
            "gen": e.gen,
            "itype": e.itype,
            "text": e.text,
        }
        index[normalize_latin(e.headword)].append(e.id)

    (output_dir / STORE_FILENAME).write_text(
        json.dumps(store, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / INDEX_FILENAME).write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8"
    )

    return {"entries": len(store), "index_keys": len(index)}


def build_lewis_short_senses(
    tei_path: str | Path,
    output_dir: str | Path,
    lemmas: set[str] | None = None,
) -> dict:
    """Parse the L&S TEI sense trees and write ``lewis_short_senses.json``.

    Keyed by entry id: ``{id: {"key", "slug", "senses": [sense_dict, ...],
    "entry_citations": [record, ...]}}`` — ``entry_citations`` are the bibls outside
    any ``<sense>`` (``<etym>`` / entry head), same record shape as a sense's
    ``citation_records``. Sense IRIs are minted with the entry's headword slug
    (``normalize_latin(headword)``), so the store is corpus-independent; when several
    sense-bearing entries share a slug (homographs: *cum* prep. / *cum* conj.), each
    mints under ``{slug}{n}`` — ``n`` its 1-based position among those entries in L&S
    order, recorded as ``iri_slug`` — so every homograph's senses get distinct IRIs.
    Entries with no extractable senses are omitted. Pass ``lemmas`` (a set of
    normalized headword slugs) to scope a smaller store.

    Returns a stats dict: ``{"entries": int, "senses": int}``.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    xml_text = Path(tei_path).read_text(encoding="utf-8")
    parsed: list[tuple] = []
    for match in _ENTRY_RE.finditer(xml_text):
        block = match.group(0)
        entry = _parse_entry(block)
        if entry is None:
            continue
        slug = normalize_latin(entry.headword)
        if lemmas is not None and slug not in lemmas:
            continue
        senses, entry_citations = parse_entry_full(
            block, slug, perseus_url=perseus_entry_url(entry.key)
        )
        if senses:
            parsed.append((entry, slug, block, senses, entry_citations))

    per_slug = Counter(slug for _, slug, *_ in parsed)
    seen: Counter = Counter()
    store: dict[str, dict] = {}
    n_senses = 0
    for entry, slug, block, senses, entry_citations in parsed:
        iri_slug = slug
        if per_slug[slug] > 1:
            seen[slug] += 1
            iri_slug = f"{slug}{seen[slug]}"
            senses, entry_citations = parse_entry_full(
                block, iri_slug, perseus_url=perseus_entry_url(entry.key)
            )
        store[entry.id] = {
            "key": entry.key, "slug": slug, "iri_slug": iri_slug, "senses": senses,
            "entry_citations": entry_citations,
        }
        n_senses += len(senses)

    # Compact JSON: the 0.12 store with citation records is ~150 MB pretty-printed;
    # the gzip twin (~17 MB) is what ships in the wheel — see build.senses_path().
    from latincy_lexicon import __version__

    meta = {
        "source": SENSES_SOURCE,
        "license": SENSES_SOURCE["license"],
        "modified": True,
        "generator": f"latincy-lexicon {__version__}",
    }
    payload = json.dumps(
        {SENSES_META_KEY: meta, **store}, ensure_ascii=False, separators=(",", ":")
    )
    (output_dir / SENSES_FILENAME).write_text(payload, encoding="utf-8")
    with gzip.open(output_dir / (SENSES_FILENAME + ".gz"), "wt", encoding="utf-8") as f:
        f.write(payload)

    return {"entries": len(store), "senses": n_senses}
