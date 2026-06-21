# Changelog

## [0.3.0] — 2026-06-20

### Added

- **Lewis & Short dictionary overlay** — new `lewis_short` spaCy component, the offline equivalent of the Perseus Latin Word Study Tool lexicon panel. A pure overlay: `whitakers_words` still owns the headword and short gloss, while `lewis_short` attaches the ranked L&S dictionary article. Includes a stdlib-only TEI P4 parser (`parsers/lewis_short.py`, zero new dependencies, 49,386 index keys), `models.LewisShortEntry`, POS-class + gender homograph disambiguation with prefix-assimilation fallback (`adcedo→accedo`, `conloco→colloco`) for 71.5% alignment coverage, lean Doc handles by default with `include_text=True` opt-in and `.get_entry(id)` on-demand fetch, and full `to_disk`/`from_disk`/`to_bytes`/`from_bytes` serialization. New CLI `build-ls` subcommand builds the L&S store. L&S data is CC BY-SA 4.0 (PerseusDL/lexica).
- `format_principal_parts(entry)` — new public API in `principal_parts.py` reconstructing textbook citation forms from Whitaker stems. Noun genitives now dispatch on `decl_which` (1–5) instead of headword-shape heuristics, fixing 4th/5th declension forms (`exercitus`, `manus`, `res`, etc.).
- `decl_which` is now included in every exported lexicon JSON entry.

## [0.2.5] — 2026-05-26

### Added

- Macron morphological filter (Class 1): `Analyzer.from_json()` and `whitakers_words` component now accept an optional `macron_path` pointing to a kaikki-derived macronized-form → UD morph index. When a macronized form is passed to `analyze()`, macrons are stripped for WW stem matching and the kaikki feature intersection is used to post-filter the returned parses. Unambiguous macronized forms (e.g. `puellā`) filter to a single case; ambiguous ones (e.g. `puellīs`) filter to the shared features across all candidates (e.g. Number=Plur). Falls back to all parses if the form is not in the index or the filter would eliminate everything.

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
