# Changelog

## [0.2.4] — 2026-04-27

### Fixed

- Dedup lexicon enrichment by content rather than position; preserves same-POS homographs that share a surface form but differ in meaning.

## [0.2.3] — 2026-04-27

### Changed

- `token._.lexicon` entries enriched with inflection-derived headwords: for verbs like `cano`, principal-parts forms are now represented in the lexicon entries.

## [0.2.2] — 2026-04-23

### Fixed

- Prefer authoritative source on dedup collision in principal-parts generation (`cano`). Less-authoritative source could previously overwrite a correctly deduced form.

## [0.2.1] — 2026-04-21

### Fixed

- Depth-aware gloss splitter: DICTLINE meanings with `;` inside `[...]` or `(...)` (e.g. `[neque..neque=>neither..nor; neque solum..sed etiam=>not only..but also]`) now split at top-level semicolons only, preserving bracketed/parenthetical annotations. Affected ~80 entries.
- PACKON pronouns (`quisquam`, `quisque`, `quidam`, `quispiam`, `quilibet`, `quivis`, `quicumque`) now have lexicon entries. Their paradigms are assembled from pronoun stem + TACKON and have no DICTLINE record, so `token._.lexicon` returned empty for all forms. Build now synthesizes a DictEntry per lemma, with glosses sourced verbatim from ADDONS.LAT PACKON comments.

## [0.2.0] — 2026-04-16

### Performance

- Lazy-load lexicon and analyzer in spaCy components — `add_pipe` drops from ~500ms to <1ms; data is loaded on first document processing
- Use `str.translate` for v→u / j→i normalization instead of chained `.replace()` calls
- Pre-lowercase inflection endings and unique forms at build/export time, removing redundant `.lower()` calls at runtime

### Internal

- Prune dev-only modules from package surface

## [0.1.0] — 2026-04-14

Initial release.

- `whitakers_words` spaCy component with context-aware glosses and morphological analysis
- `paradigm_generator` spaCy component with full inflectional paradigms and reinflection
- Standalone `Generator` API for form generation and lookup table building
- CLI: `latincy-lexicon build` to parse bundled Whitaker's Words files into JSON
- 39K+ dictionary entries with POS-aware ranking and multi-signal disambiguation
