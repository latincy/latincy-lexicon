# Regression fixtures

Each `REG-*.toml` pins one fixed generator/paradigm edge case so future changes
to the freq/age filter, UNIQUES resolver, or reconstruction path can't silently
re-break it. Discovered and run by `tests/test_regressions.py` — adding a fix is
one TOML file, no new test code.

This mirrors the `data/overrides/OVR-*.toml` convention: the regression surface
grows by **data**, not code. It also pairs with the GitHub issue error-reporting
template — a reported bad form becomes a `REG-*.toml` row plus its fix.

## Schema

```toml
id     = "REG-001"              # stable id; match the filename prefix
lemma  = "puella"              # citation form passed to Generator.generate()
pos    = "N"                    # optional WW POS filter ("N", "V", "ADJ", ...)
issue  = "[lex] ..."           # provenance: the tracked OF task / GH issue
reason = "..."                  # why these forms behave as asserted

[[check]]                       # one or more; each is one parametrized case
include_variants = false        # the generate() flag under test
must_appear      = ["puella"]   # every form here MUST be generated
must_not_appear  = ["puellabus"]# none of these may be generated
lemma            = "amo"        # optional: override fixture lemma for this
pos              = "V"           #   check (assert cross-lemma no-leak guards)
```

A `[[check]]` may override `lemma`/`pos` to assert cross-lemma behavior — e.g. a
form restored to lemma X must NOT also leak into an unrelated lemma Y.

A fixture typically has two `[[check]]` blocks — one for the clean default
(`include_variants = false`) and one for the exhaustive set
(`include_variants = true`) — to pin both sides of the variant behavior.

## Conventions

- Filename: `REG-NNN-short-slug.toml`, `id` matching the `REG-NNN` prefix.
- Only assert surfaces you have **verified** are produced (or correctly absent).
  Don't assert forms the underlying WW data doesn't contain.
- Keep `reason` one line; it is printed on assertion failure.
