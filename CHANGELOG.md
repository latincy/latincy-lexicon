# Changelog

## [0.11.0] — 2026-07-28

Fixes silently-dropped glosses on lemmatizer misses in `whitakers_words`, by
shipping the morphological analyzer **on by default** — built in memory from the
already-bundled WW data, with no 15 MB `analyzer.json` added to the wheel.

Previously the default (lexicon-only) component keyed its lookup solely on
`token.lemma_`. When an upstream spaCy model mis-lemmatized a form — even one
Whitaker's own analyzer parses correctly, e.g. `contemplemur` (pres. pass. subj.
of deponent `contemplor`) — the lemma lookup missed and the token was left with
no gloss. The analyzer, which segments the surface form and lets the component
recover the entry by headword, only ran when an `analyzer_path` was configured,
which the default pipeline never did.

### Added
- **`build_analyzer()`** (`latincy_lexicon.build`, re-exported from the package
  root): builds a ready-to-use `Analyzer` in memory from the bundled WW data,
  mirroring `build_lexicon()`. Disk-cached under `~/.cache/latincy-lexicon`
  (`analyzer-` prefix) keyed by package version + DICTLINE hash; ~5 s first
  call, then loaded from cache.
- **whitakers_words**: new `use_bundled_analyzer` config flag, **default
  `True`**. The default component now populates `token._.ww` and recovers
  `token._.gloss` on forms the lemmatizer misses, with no data files on disk.
  An explicit `analyzer_path` still takes precedence; `use_bundled_analyzer=False`
  restores the lighter lexicon-only mode. The flag round-trips through
  `to_disk`/`from_disk`/`to_bytes`/`from_bytes`.

### Changed
- **whitakers_words**: default behavior now builds the analyzer on first use
  (~5 s, cached) and carries its stem/ending indexes in memory. `token.lemma_`
  is never overwritten — the corrected citation form surfaces via
  `token._.lexicon[0]["headword"]` and `token._.ww[0]["lemma"]`.
- Refactor: extracted `_analyzer_payload()` in `build.py`, shared by the
  `analyzer.json` export and the in-memory `build_analyzer()` so both stay
  identical.

## [0.10.0] — 2026-07-11

Surfaces the Lewis & Short sense store (84,091 senses / 42,982 entries) from
the token API — tier 1 of the senses roadmap. Also fixes two citation-form
bugs surfaced during a latincy-viewer run.

### Added
- **lewis_short**: new opt-in `attach_senses` config flag. When enabled, each
  matched token gets `token._.lewis_short_senses` — the **top-ranked** entry's
  structured senses as a lean list of `{"level", "n", "display_gloss"}` dicts.
  Raw `gloss`, `citations`, and `sameAs` linked-data ids stay behind
  `get_senses(entry_id)`. Default `False`: the sense store is ~48 MB and only
  loads lazily when a component that needs it runs.
- **lewis_short**: `attach_senses` round-trips through
  `to_disk`/`from_disk`/`to_bytes`/`from_bytes` alongside `include_text`.
- README: `lewis_short` component documentation (previously undocumented).
- **overrides**: `[change]` may now be an array-of-tables (`[[change]]`) so one
  override edits several fields of an entry as a single attributable record;
  `[target]` accepts optional `decl_which`/`decl_var` to disambiguate
  homographs sharing (stem1, pos).

### Fixed
- **build**: the (headword, pos, glosses) dedup now breaks source-priority ties
  by frequency, so the canonical high-frequency homograph wins over a rarer
  duplicate. `pario` (bear/give birth) shipped as both a freq-A entry
  (`peperi`/`partum`) and a freq-E entry (`parire`/`paritum`) from the same
  source; first-seen kept the freq-E stub, citing `pario, pariare, pariavi,
  pariatum` (conflated with the rare 1st-conj denominal). It now cites the
  classical `pario, parere, peperi, partum`.
- **lexicon data (OVR-003)**: the medieval i-spelling `intelligo` shipped as a
  present-only stub (stem3/stem4 = Whitaker `zzz`), truncating its citation to
  `intelligo, intelligere`. Its perfect + supine stems are backfilled from the
  canonical `intellego`, giving `intelligo, intelligere, intellexi,
  intellectum`. (LatinCy lemmatizes `intellig-` forms to the i-spelling, so the
  stub is what reached vocab cards.)

### Not a bug (documented)
- `revertor`: the lexicon returns the correct citation for whichever lemma it
  is given (deponent lemma → `revertor, reverti, reversus sum`; active lemma →
  `reverto, revertere, reverti`, both u/v spellings). A viewer showing the
  active citation for a deponent form is a LatinCy model lemmatization issue,
  not a lexicon one.

### Unchanged
- `token._.gloss` still comes from Whitaker's top parse (upgrading it to a
  contextually *selected* L&S sense is tier 2).

## [0.9.1] — 2026-07-11

GitHub tag only (not published to PyPI; the fix ships to PyPI with 0.10.0).

### Fixed
- **whitakers_words**: lemma-matched lexicon entries now outrank entries added
  via inflectional parses of the surface form in `token._.lexicon` ranking.
  Previously a same-POS homograph reached only through a surface parse could
  win on raw frequency — form `dea` (lemma `dea`, freq C) also parses under
  `deus` (freq A), so `token._.lexicon[0]` was the `deus` entry and downstream
  citation forms came out as `deus, dei, m.` instead of `dea, deae, f.`
  Inflection-matched homographs remain available lower in the list.

## [0.9.0] — 2026-07-09

Makes `Form.alternate` load-bearing: the generator now routes real-but-nonstandard
nominal forms into that flag instead of dropping them, and `generate()` returns
the clean textbook paradigm by default while keeping the full exhaustive set one
argument away. Also fixes two paradigm-pollution bugs in `deus` and restores
`iusiurandum`.

### Added

- **`Generator.generate(..., include_variants=False)`** — new keyword. The
  default returns the clean paradigm (nominal archaisms, frequency siblings, and
  proper-sense capitalizations filtered out); `include_variants=True` returns the
  full exhaustive set, best for NLP consumers that want every attested surface.
  `to_lookup_dict` uses `include_variants=True` so form→lemma coverage is
  unchanged.
- **`paradigm_generator` spaCy component** gains an `include_variants` config
  option (default `False`), persisted across `to_disk`/`to_bytes`.
- **Regression-fixture harness** (`tests/test_regressions.py` +
  `tests/fixtures/regressions/REG-*.toml`) — each fixed paradigm edge case is one
  declarative TOML fixture and one parametrized test, mirroring the `OVR-*.toml`
  override convention. The regression surface grows by data, not code.

### Changed

- Non-verb archaic/rare forms (1st-decl `-abus` `puellabus`, poetic `-ai`
  `puellai`, `-ium` frequency siblings like `regium`) are now emitted with
  `Form.alternate=True` and hidden from the default paradigm, rather than being
  discarded outright. They are fully recoverable via `include_variants=True`.
- `deus`: WW stores a single capitalized entry (`De`→`Deus`) that conflates the
  Christian-God proper sense with the common noun. The common paradigm now emits
  lowercase forms (`deus`, `dei`, `deo`, …) as standard, with the capitalized
  deity form flagged alternate (recoverable via `include_variants`).
- Default filtering applies to **non-verb** alternates only. The verb-alternate
  discriminator currently over-flags the standard forms of irregular verbs
  (`esse`, `posse`, the present system of `eo`/`edo`, `fers`/`fert`), so verb
  forms remain exhaustive by default until that discriminator is corrected.

### Fixed

- **`iusiurandum` no longer leaks into every 2nd-declension noun.** Its UNIQUES
  are stored `N 2 1` while the DICTLINE entry `jusjurand` is `N 2 2`, so prefix
  resolution orphaned them and they cascaded into `deus`, `amicus`, and every
  other N 2 1 noun. The four i-spelled forms (`iusiurandum`, `iurisiurandi`,
  `iureiurando`) are now bound explicitly to the `iusiurandum` lemma
  (POS-matched across the class mismatch), and a supplementary entry-id→UNIQUES
  index lets a unique attach to its resolved entry even when its declared class
  differs. This both stops the leak and restores `iusiurandum`'s own paradigm.
- **`memento`/`mementote` restored to `memini`.** These future imperatives of
  the perfect-only defective `memini` were stored under `V 0 0` and dropped to
  avoid cascading into every verb's paradigm. They now bind explicitly to
  `memini` (via the same POS-matched override + by-source attachment), so they
  appear in `memini`'s paradigm and nowhere else.

### Repo

- **GitHub issue template** (`.github/ISSUE_TEMPLATE/bad-form-report.yml`) — a
  structured "bad or missing form" report whose fields map directly onto a
  `REG-*.toml` regression fixture.

## [0.8.0] — 2026-06-30

Upstreams the paradigm corrections that the `latincy-lexicon-site` viewer
previously applied post-hoc, so the library — not each consumer — owns the
linguistic judgement. The site can now read the new metadata and stay
presentational.

### Added

- **`Form.alternate`** — new boolean field on generated forms. It marks a form
  that is real Latin but outside the canonical textbook paradigm: Plautine
  sigmatic forms (`amasso`, `amasseram`, `amassim` off the syncopated `amass-`
  stem), archaic infinitives (`amarier`), the spurious perfect-passive
  participle of verbs with no PPP (`sum` → `futus`), and wrong-stem/wrong-conj
  artefacts (`audio` → `audbam`). Additive and non-breaking — `generate()`
  still emits every form (exhaustive for downstream NLP); build a clean
  paradigm by filtering `not f.alternate`. New `canonical.py` reconstructs each
  verb's canonical stems (rewriting the syncopated `-ass` perfect back to
  `-av`) to make the judgement; age/frequency codes cannot — many sigmatic
  forms are `age='X'`.

### Changed

- **Future perfect is now distinguishable from the future.** Perfect-system
  tenses (perfect, pluperfect, future-perfect) carry `Aspect=Perf`, so
  `amavero` (`Tense=Fut|Aspect=Perf`) is no longer conflated with `amabo`
  (`Tense=Fut`). UD-conformant — no non-standard tense value introduced.
- **`generate()` output is cleaner.** Byte-identical duplicate forms and
  empty-surface forms are dropped; synthetic comparative/superlative rows that
  don't actually compare are removed (`cum` no longer yields a spurious
  comparative), while real comparatives with distinct surfaces (`celerius`,
  `melior`) survive.

### Fixed

- **Noun gender no longer reads `Com` for single-gender nouns.** A declension
  rule tagged `Gender=Com` (1st-decl serves masc `agricola` and fem `cura`) is
  overridden by the noun's own lexicon gender, so `cura` reads `Fem`.
  Genuinely common-gender nouns (`civis`) keep `Com`.

### Validated

- The canonical (non-`alternate`) `amo` paradigm is asserted against the
  reference first-conjugation tables on
  [Wikipedia](https://en.wikipedia.org/wiki/Latin_conjugation) — 78 finite
  forms plus infinitives and imperatives.

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
