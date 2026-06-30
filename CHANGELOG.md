# Changelog

## [0.7.0] — 2026-06-30

### Added

- **`source_refs` lexicon field** — bibliographic citations Whitaker appended to gloss text (e.g. *"epitomize (Souter)"*, *"copious (L+S, Late Latin)"*) are extracted into a per-entry `source_refs` list and removed from the gloss itself. Covers the curated authority vocabulary (L+S, Souter, Pliny, Latham, Erasmus, Bee, Collins, Cas, Vulgate, OLD, OED, Douay, Def, Nelson, Whitaker, Du Cange); 2,756 entries annotated. Register/period codes (`(Ecc)`, `(Cal)`) and `L:`/`W:`/`E:` prefixes are deliberately kept as usage labels. Purely additive — `glosses` stays `list[str]`.
- **`gloss_orig` lexicon field** — on the 4,150 entries whose glosses the cleanup below changed, the verbatim original Whitaker senses are preserved in `gloss_orig`, so nothing from the source is discarded and every edit is reversible. Unchanged entries omit the field (their `glosses` already matches the original).

### Changed

- **Cleaner gloss outputs.** A punctuation audit of ~81.5k gloss strings drove a four-part cleanup, centralized in `build._clean_glosses()` and applied identically to dictionary and addon (prefix/suffix/tackon) entries and to the `whitakers_words` component's `token._.gloss`:
  - leading Whitaker formatting artifacts stripped — pipe markers including multi-pipe sense-numbering (`||`, `|||`) and dash-space (`- `) prefixes; suffix glosses (`-ing`, `-able`) preserved;
  - trailing syntactic usage notes stripped — subjunctive/infinitive constructions and case-government codes (`(ne + SUB = lest…)`, `(w/DAT)`, `(only NOM S)`), so *timeo* now glosses `fear, dread, be afraid` and *auxilio* `help`;
  - trailing derivational cross-references stripped — `(adeo => go to)` and similar `=>` / `->` pointers;
  - bracketed example blocks (`[…]`) and `(= x)` equivalence notes are left in place for downstream filtering.

### Fixed

- **Headword case normalized.** The reconstructed `headword` field is now lowercased (`deus`, not `Deus`; likewise the `II`/`V`/`X` numeral addons), matching classical-lexicon convention. `normalized_headword` (used for lookup, with v/j folding) is unchanged.
- **Generator no longer over-generates noun forms across genders.** `Generator.generate(lemma, pos="N")` applied every gender variant of a declension class to each noun, emitting spurious forms — e.g. neuter *carmen* (`carmen, carminis`) produced a common-gender `carmines` and a duplicate `Gender=Com` ablative. A gender-compatibility filter now restricts noun forms to the entry's inherent gender, while masculine/feminine nouns still keep their shared common-gender endings (`reges`, `cives`).

Both new fields are additive and the version-keyed build cache auto-invalidates, so installed consumers rebuild cleaned glosses on upgrade.

## [0.6.0] — 2026-06-29

### Added

- **Lewis & Short sense store ships in the wheel.** `lewis_short_senses.json` (~48 MB) and `lewis_short_index.json` (~1.2 MB) are now bundled under `latincy_lexicon/data/json/`, so the structured L&S senses are available on install — no local `build-ls` step. The `lewis_short` component auto-discovers the bundled files when no explicit `ls_senses_path` / `ls_index_path` is given.
- **`senses_path()` and `sense_index_path()`** — new path accessors in `build.py`, exported from the package root, returning the locations of the bundled L&S sense store and index.

### Changed

- CLI `build-ls` now defaults `--output-dir` to `src/latincy_lexicon/data/json/` (the bundled-data location) instead of `data/json/`.

## [0.5.0] — 2026-06-24

### Added

- **`build_lexicon()`** — public in-memory build of the lexicon dict from the bundled DICTLINE, returning the same structure `build()` writes to `lexicon.json` (keyed by normalized headword; glosses, principal parts, POS, metadata) without touching disk. This is the path downstream consumers use to get glosses + citation forms without a prebuilt `lexicon.json` (which is a build artifact, not shipped in the wheel). Exposed from the package root.
- **Disk cache for `build_lexicon()`** — the ~5s build (≈39k entries) is cached under an XDG-style user cache dir (`LATINCY_LEXICON_CACHE_DIR` → `XDG_CACHE_HOME` → `~/.cache`), keyed by package version + DICTLINE content hash. Dependency-free; cache read/write failures degrade to a plain rebuild. `use_cache=False` forces a rebuild.
- **`whitakers_words` works with zero configuration** — when no `lexicon_path`/`analyzer_path`/`ls_index_path` is given, the component now defaults to the bundled in-memory lexicon (via cached `build_lexicon()`), so `nlp.add_pipe("whitakers_words")` sets `token._.lexicon` and `token._.gloss` out of the box. Purely additive; pass `use_bundled_lexicon=False` to opt out (analyzer-only / empty component). Explicit-path behavior is unchanged.

### Fixed

- **Defective-verb `zzz` placeholder no longer leaks into lemmas or citation forms.** Whitaker stores perfect-only verbs (e.g. *ōdī*, *meminī*, *nōvī*), comparative-only adjectives/adverbs, the reflexive pronoun, and some pluralia tantum with `zzz` in stem1 (no first principal part). Headword reconstruction used to append a present ending to that placeholder, producing junk lemmas like `zzzo` and citation forms like `zzzo, osere`. `_reconstruct_defective_headword` now builds the lemma from the first real stem (verbs → perfect 1sg; comparatives → `deterior`/`deterius`; reflexive → `sui`; pluralia → `multi`), `_export_lexicon` marks such entries `defective`, and `principal_parts._format_defective` renders proper perfect-only citations (`odi, odisse, osus sum`; `memini, meminisse`). Regression test asserts no lexicon key ever contains `zzz`.

## [0.4.0] — 2026-06-20

### Added

- **Lewis & Short sense-tree parsing** — new `parsers/lewis_short_senses.py` reconstructs each entry's structured `<sense>` hierarchy (the `I.A.2.a` nesting), where `parsers/lewis_short.py` only flattens the article to text. It rebuilds the tree from the TEI `level`/`n` labels (correcting buggy source levels, e.g. *pater*'s F/G/H now nest under II instead of stranding at the root), collapses purely-syntactic subdivisions, mints sense IRIs, and keeps the Perseus xml:id and CTS `<bibl>` citations. Stdlib-only; ships in the wheel. Exposed as `parse_lewis_short_senses` and the `LewisShortSense` model.
- `lewis_short` component gains `.get_senses(entry_id)` (and an `ls_senses_path` config) — an opt-in, lazily-loaded accessor returning an entry's structured senses. Per-token `token._.lewis_short` handles stay lean.
- CLI `build-ls` now also builds **`lewis_short_senses.json`** (`{id: {key, slug, senses[]}}`); `--no-senses` skips it. Like `lewis_short.json`, this is a **build artifact — not bundled in the wheel**; build it locally and point `ls_senses_path` at it.

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
