"""When DICTLINE carries two entries for the same lemma with identical
glosses but different stems (e.g. the Oxford entry for `cano` with the
reduplicated perfect stem `cecin` alongside a Whitaker-custom entry
that has `can` as stem3), the build pipeline must keep the entry from
the more authoritative source. Before this behavior was enforced, the
first-parsed entry always won, and for `cano` that happened to be the
bad custom one — emitting principal parts `cano, canere, cani, canitum`
instead of the correct `cano, canere, cecini, cantum`.
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture(scope="module")
def lexicon(tmp_path_factory):
    from latincy_lexicon.build import build

    out = tmp_path_factory.mktemp("lex")
    build(output_dir=out)
    return json.loads((out / "lexicon.json").read_text())


def _verb_entries(lexicon: dict, normalized: str) -> list[dict]:
    return [e for e in lexicon.get(normalized, []) if e.get("pos") == "V"]


def test_cano_keeps_reduplicated_perfect_stem(lexicon):
    """DICTLINE lists cano at source=S (stems can/can/can/canit) before
    source=O (stems can/can/cecin/cant); the Oxford one must survive."""
    entries = _verb_entries(lexicon, "cano")
    assert entries, "cano missing from lexicon"
    assert len(entries) == 1, (
        f"dedup should keep one verb entry; got {len(entries)}"
    )
    stems = entries[0]["principal_parts"]
    assert "cecin" in stems, f"expected 'cecin' in stems, got {stems}"
    assert "canit" not in stems, (
        f"'canit' (bad supine) leaked into stems: {stems}"
    )
    assert entries[0]["source"] == "O"


def test_dedup_preserves_cross_pos_entries(lexicon):
    """Dedup collapses exact (headword, pos, glosses) matches only —
    same-lemma entries with different POS (real polysemy) stay split."""
    entries = lexicon.get("bonus", [])
    pos_counts: dict[str, int] = {}
    for e in entries:
        pos_counts[e["pos"]] = pos_counts.get(e["pos"], 0) + 1
    assert pos_counts.get("ADJ", 0) >= 1
    assert pos_counts.get("N", 0) >= 1
