"""Data-driven regression harness for generator paradigm fixes.

Each fixed edge-case bug is pinned by one declarative TOML fixture under
``tests/fixtures/regressions/REG-*.toml`` — no new test code per fix. This
mirrors the ``OVR-*.toml`` override convention (see ``test_overrides.py``): the
regression surface grows by data, not by code. To pin a new fix, drop a TOML
file; the parametrized test below discovers and runs it automatically.

Fixture schema (see ``tests/fixtures/regressions/README.md``)::

    id     = "REG-001"                 # stable id, matches filename prefix
    lemma  = "puella"                  # citation form passed to generate()
    pos    = "N"                        # optional WW POS filter
    issue  = "[lex] ..."               # provenance: the tracked task/issue
    reason = "..."                      # why this form behaves as asserted

    [[check]]
    include_variants = false            # generate() flag for this check
    must_appear      = ["puella"]       # every form here MUST be generated
    must_not_appear  = ["puellabus"]    # none of these may be generated

Each ``[[check]]`` becomes one parametrized test case, so a single fixture can
assert both the clean-default and the ``include_variants=True`` behavior.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

ANALYZER_JSON = Path(__file__).parent.parent / "data" / "json" / "analyzer.json"
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "regressions"

skip_no_data = pytest.mark.skipif(
    not ANALYZER_JSON.exists(),
    reason="analyzer.json not available (run: latincy-lexicon build)",
)


def _load_fixtures() -> list[dict]:
    """Parse every REG-*.toml into a dict, sorted for deterministic order."""
    fixtures: list[dict] = []
    for toml_path in sorted(FIXTURES_DIR.glob("REG-*.toml")):
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        data["_path"] = toml_path.name
        fixtures.append(data)
    return fixtures


def _cases() -> list[tuple]:
    """Flatten fixtures into one (fixture, check, id) tuple per [[check]]."""
    out: list[tuple] = []
    for fx in _load_fixtures():
        checks = fx.get("check", [])
        for i, check in enumerate(checks):
            variants = check.get("include_variants", False)
            case_id = f"{fx.get('id', fx['_path'])}[{i}]-{'variants' if variants else 'clean'}"
            out.append((fx, check, case_id))
    return out


_CASES = _cases()


@pytest.fixture(scope="module")
def generator():
    from latincy_lexicon.generator import Generator

    return Generator.from_json(ANALYZER_JSON)


@skip_no_data
@pytest.mark.parametrize(
    "fixture,check",
    [(c[0], c[1]) for c in _CASES],
    ids=[c[2] for c in _CASES],
)
def test_regression(fixture: dict, check: dict, generator) -> None:
    """Assert a fixed edge case still behaves as its fixture records."""
    # A check may override the fixture-level lemma to assert cross-lemma
    # behavior — e.g. that a form restored to lemma X does NOT also leak into
    # unrelated lemma Y.
    lemma = check.get("lemma", fixture["lemma"])
    pos = check.get("pos", fixture.get("pos"))
    include_variants = check.get("include_variants", False)

    forms = {
        f.form
        for f in generator.generate(
            lemma, pos=pos, include_variants=include_variants,
        )
    }

    provenance = f"{fixture.get('id', fixture['_path'])} ({fixture.get('issue', '')})"

    for want in check.get("must_appear", []):
        assert want in forms, (
            f"{provenance}: expected {want!r} in generate({lemma!r}, "
            f"include_variants={include_variants}) but it was absent. "
            f"reason: {fixture.get('reason', '')}"
        )

    for unwanted in check.get("must_not_appear", []):
        assert unwanted not in forms, (
            f"{provenance}: {unwanted!r} must NOT appear in generate({lemma!r}, "
            f"include_variants={include_variants}) but it did. "
            f"reason: {fixture.get('reason', '')}"
        )


def test_fixtures_exist() -> None:
    """Guard: the harness must actually discover fixtures (catches a broken
    glob / empty dir that would make every regression silently un-tested)."""
    assert _CASES, f"no REG-*.toml fixtures discovered under {FIXTURES_DIR}"
