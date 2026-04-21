# Overrides — Whitaker's Words Archaeology

This directory holds **curated corrections and enhancements** applied on top of the canonical Whitaker's Words source data (`DICTLINE.GEN`, `INFLECTS.LAT`, `ADDONS.LAT`, `UNIQUES.LAT`). Canonical files are never mutated; every divergence is a first-class, numbered, reviewable record that stacks on top at build time.

## Principles

1. **Canonical data is immutable.** The raw WW files are treated as the ground truth. We layer on top, we do not edit.
2. **Every change is attributable.** Each override carries its own ID, author, date, and reason.
3. **Nothing is ever deleted.** Reverted or superseded overrides stay in the tree with updated `status`. The archaeological record is preserved so that old commits and issues referencing an OVR ID still resolve.
4. **Declarative, not imperative.** Every build re-derives output from canonical + active overrides. No migration history table, no order-dependence, no forward/backward ops — just a merge.

## File layout

One TOML file per override, named `OVR-NNN-short-slug.toml`:

```
overrides/
├── README.md                       # this file
├── OVR-001-neque-conj.toml         # first override
└── OVR-NNN-<slug>.toml             # subsequent, monotonically numbered
```

## Schema

```toml
id = "OVR-NNN"                      # stable, never reused
date = 2026-04-21                   # TOML date literal
author = "patrick@diyclassics.org"
status = "active"                   # active | superseded | reverted

# Optional — set when this override replaces an earlier one
# supersedes = "OVR-MMM"

[target]
lemma = "neque"                     # headword to match
pos = "CONJ"                        # POS to disambiguate homographs

[change]
field = "meaning"                   # the DictEntry field to replace

# Pick ONE of the following two forms:

# Form A — borrow value from another canonical entry
[change.borrow_from]
lemma = "nec"
pos = "CONJ"
field = "meaning"

# Form B — literal replacement
# [change]
# field = "meaning"
# to = "nor, and..not; not..either, not even;"

reason = """
Prose explanation of why this override exists. Use triple-quoted
multi-line strings. Should be explicit enough that a reader a year
from now (or Claude in a future session) can judge whether the
override still makes sense.
"""

# Optional — GitHub issue, paper citation, etc.
refs = [
    "https://github.com/latincy/latincy-lexicon/issues/NN",
]
```

## ID scheme

- `OVR-001`, `OVR-002`, … monotonically assigned, never reused, never renumbered.
- If the override count grows past a few hundred, add subdirs (`overrides/glosses/`, `overrides/inflections/`) — IDs stay stable.
- Zero-padding to 3 digits is fine for now; expand to 4 when needed.

## Statuses

| status        | Applied at build? | Notes                                                           |
|---------------|-------------------|-----------------------------------------------------------------|
| `active`      | yes               | normal state                                                    |
| `superseded`  | no                | replaced by a newer OVR (set `supersedes` on the replacement)   |
| `reverted`    | no                | intentionally undone (stays in tree for archaeology)            |

## Provenance in exported data

Each entry touched by one or more active overrides is annotated in `lexicon.json` with an `_overrides` list:

```json
{
  "headword": "neque",
  "pos": "CONJ",
  "glosses": ["nor, and..not", "not..either, not even"],
  "_overrides": [
    {
      "id": "OVR-001",
      "field": "meaning",
      "original_value": "nor [neque..neque=>neither..nor; neque solum..sed etiam=>not only..but also];",
      "source": {"kind": "borrow", "lemma": "nec", "pos": "CONJ", "field": "meaning"},
      "date": "2026-04-21",
      "reason_short": "Clean up polluted WW gloss; borrow nec CONJ equivalent."
    }
  ]
}
```

Downstream UIs can surface this as a "(curated)" indicator with tooltip access to the canonical value.

## Recovery playbook

| Question                                    | How to answer                                                    |
|---------------------------------------------|------------------------------------------------------------------|
| What did WW originally say for entry X?     | Read `_overrides[].original_value` on the exported entry         |
| Which overrides are live?                   | `ls OVR-*.toml`, grep `status = "active"`                        |
| When/why did we change X?                   | `git log src/latincy_lexicon/data/overrides/OVR-NNN-*.toml`      |
| Give me a pristine build                    | (planned) `latincy-lexicon build --no-overrides`                 |
| Revert override N                           | Set `status = "reverted"` in the TOML, commit. Do not delete.    |
