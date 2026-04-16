# Changelog

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
