<img src="https://raw.githubusercontent.com/latincy/latincy-lexicon/main/assets/latincy-lexicon-logo.jpg" alt="LatinCy Lexicon" width="400">

[![PyPI version](https://img.shields.io/pypi/v/latincy-lexicon.svg)](https://pypi.org/project/latincy-lexicon/)
[![Python versions](https://img.shields.io/pypi/pyversions/latincy-lexicon.svg)](https://pypi.org/project/latincy-lexicon/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Whitaker's Words as LatinCy pipeline components for Latin NLP.**

`latincy-lexicon` makes the lexical data and morphological analysis engine from [Whitaker's Words](https://mk270.github.io/whitakers-words/) available as spaCy pipeline components, designed for use with [LatinCy](https://huggingface.co/latincy) language models.

## Quick Start

```python
import spacy

nlp = spacy.load("la_core_web_lg")
nlp.add_pipe("whitakers_words")   # zero-config: bundled lexicon, no data files to build

doc = nlp("Poeta bonus carmina pulchra scribit.")

# Dictionary glosses — work out of the box
for token in doc:
    if token._.gloss:
        print(f"{token.text:12} {token._.gloss}")
# Poeta        poet
# bonus        good, honest, brave, noble, kind, pleasant, right, useful
# carmina      song/music
# pulchra      pretty
# scribit      write
```

Morphological analysis (`token._.ww`), reinflection, and paradigms use the analyzer, which you build once from the bundled data (`latincy-lexicon build` writes `analyzer.json` — see [Data Setup](#data-setup)):

```python
nlp.add_pipe("paradigm_generator", config={"analyzer_path": "data/json/analyzer.json"})

# Reinflection: change morphological features, get the right Latin form
scribit = nlp("Poeta bonus carmina pulchra scribit.")[4]
print(scribit._.reinflect(Number="Plur"))    # scribunt
print(scribit._.reinflect(Tense="Imp"))      # scribebat
print(scribit._.reinflect(Voice="Pass"))     # scribitur
```

## Features

- **`whitakers_words`** — Single pipeline component providing dictionary glosses (`token._.lexicon`), rule-based morphological analysis (`token._.ww`), and short definitions (`token._.gloss`)
- **`paradigm_generator`** — Generates complete inflectional paradigms for any lemma, with reinflection support (`token._.paradigm`, `token._.reinflect`)
- **Standalone `Generator` API** — Produce all inflected forms for a lemma, or build form-to-lemma lookup tables, without requiring spaCy
- **POS-aware ranking** — Uses upstream tagger/morphologizer output to rank ambiguous entries and parses
- **Multi-signal disambiguation** — Scores candidates using lemma match, morphological features, dependency labels, NER context, and dictionary frequency
- **Clean glosses, originals preserved** — dictionary glosses are stripped of Whitaker's inline formatting (pipe markers, `- ` prefixes) and syntactic usage notes (`(w/DAT)`, `(ne + SUB = …)`, `=>` cross-references); bibliographic citations are surfaced in a `source_refs` field, and the verbatim original senses are kept in `gloss_orig` on any entry the cleanup changed

## Installation

```bash
pip install latincy-lexicon
```

Or for development:

```bash
git clone https://github.com/latincy/latincy-lexicon.git
cd latincy-lexicon
uv venv && source .venv/bin/activate
uv pip install -e ".[dev,spacy]"
```

## Data Setup

Dictionary glosses need **no setup** — `whitakers_words` loads the bundled lexicon on first use (see [Quick Start](#quick-start)).

Morphological analysis (`token._.ww`), reinflection, and paradigm generation use the **analyzer**, which you build once from the bundled data:

```bash
latincy-lexicon build
```

This parses the bundled DICTLINE, INFLECTS, UNIQUES, and ADDONS files, applies patches (sum/esse, pronoun endings), reconstructs headwords, and writes `analyzer.json` and `lexicon.json` to `data/json/`. Pass `analyzer_path="data/json/analyzer.json"` to the components to enable these features.

## Usage

```python
import spacy

nlp = spacy.load("la_core_web_lg")
nlp.add_pipe("whitakers_words")   # bundled lexicon; add analyzer_path for token._.ww

doc = nlp("Gallia est omnis divisa in partes tres.")

for token in doc:
    print(f"{token.text:12} {token._.gloss}")
```

## Pipeline Components

### `whitakers_words`

A single component that provides three token extensions:

- `token._.lexicon` — list of dictionary entries matching the token's lemma, with glosses, part of speech, principal parts, and age/frequency metadata. Each entry's `glosses` are cleaned of Whitaker's inline formatting and syntactic notes; an entry may also carry `source_refs` (bibliographic citations such as *L+S* or *Souter*, extracted from the gloss text) and `gloss_orig` (the verbatim original Whitaker senses, present only when the cleanup changed them)
- `token._.ww` — full morphological parse list from the Words stem+ending engine, ranked by POS match, morphological features, dependency labels, NER context, and frequency
- `token._.gloss` — short definition from the top-ranked parse, with Whitaker's inline usage notes and citations removed

With no configuration the component loads the **bundled lexicon** (glosses + citation forms) — no data files required. Pass `analyzer_path` (from `latincy-lexicon build`) to add the morphological parse engine (`token._.ww`), or `lexicon_path` to override the bundled lexicon. Best results when placed after all LatinCy pipeline components.

**Macron filter (optional):** pass `macron_path` pointing to a kaikki-derived macronized-form → UD morph index (built by `latincy-words`). When a macronized form is analyzed, the index constrains which parses are returned — e.g. `puellā` → ABL only. Falls back gracefully when a form is not in the index.

### `paradigm_generator`

Generates complete inflectional paradigms for Latin words. The inverse of the analyzer: given a lemma, it produces all inflected forms with UD morphological features.

```python
nlp.add_pipe("paradigm_generator", config={
    "analyzer_path": "data/json/analyzer.json",
})

doc = nlp("Amat puellam.")
for token in doc:
    if token._.paradigm:
        print(f"{token.text}: {len(token._.paradigm)} forms")
```

Token extensions:

- `token._.paradigm` — list of inflected forms for the token's lemma, each with `form`, `lemma`, `upos`, `feats` (dict of UD features), and `alternate` (bool). `None` for punctuation or unknown lemmas. By default only the clean paradigm is exposed; pass `config={"include_variants": True}` to `add_pipe` to include alternate forms.
- `token._.reinflect(**overrides)` — returns a surface form matching the token's current morphology merged with the provided UD feature overrides, or `None` if no match exists.

```python
doc = nlp("amat")
doc[0]._.reinflect(Number="Plur")           # "amant"
doc[0]._.reinflect(Tense="Imp")             # "amabat"
doc[0]._.reinflect(Tense="Imp", Number="Plur")  # "amabant"
```

### Standalone Generator API

The `Generator` class can be used independently of spaCy:

```python
from latincy_lexicon.generator import Generator

gen = Generator.from_json("data/json/analyzer.json")

# Generate all forms of a lemma. sort="paradigm" gives traditional
# pedagogical order (present → imperfect → future, …); the default
# sort="ud" preserves rule-traversal order for downstream NLP.
forms = gen.generate("amo", sort="paradigm")
rex_forms = gen.generate("rex", pos="N")     # nouns only (POS filter)

for f in forms[:5]:
    print(f"{f.form:15} {f.upos:6} {f.feats}")
# amo             VERB   Aspect=Imp|Mood=Ind|Number=Sing|Person=1|Tense=Pres|VerbForm=Fin|Voice=Act
# amas            VERB   Aspect=Imp|Mood=Ind|Number=Sing|Person=2|Tense=Pres|VerbForm=Fin|Voice=Act
# amat            VERB   Aspect=Imp|Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin|Voice=Act
# amamus          VERB   Aspect=Imp|Mood=Ind|Number=Plur|Person=1|Tense=Pres|VerbForm=Fin|Voice=Act
# amatis          VERB   Aspect=Imp|Mood=Ind|Number=Plur|Person=2|Tense=Pres|VerbForm=Fin|Voice=Act

# Build form→lemma lookup tables for batch processing
lookup = gen.to_lookup_dict(["rex", "puella"])
# {"rex": "rex", "regis": "rex", "regi": "rex", ..., "puella": "puella", ...}
```

Each `Form` has five fields: `form` (surface), `lemma` (citation), `upos` (UD POS), `feats` (UD feature string), and `alternate` (bool).

### Canonical vs. alternate forms

By default `generate()` returns the **clean textbook paradigm**. Forms outside the standard paradigm — archaic/rare nominal forms (`puellabus`, `puellai`), redundant frequency siblings (`regium`), and proper-sense capitalizations (`Deus` under the common noun `deus`) — are flagged `alternate=True` and filtered out. Pass `include_variants=True` for the exhaustive set:

```python
clean = gen.generate("puella")                         # textbook paradigm
full  = gen.generate("puella", include_variants=True)  # + puellabus, puellai, …
```

Every `Form` still carries the `alternate` flag, so a consumer can inspect or re-filter as needed. `to_lookup_dict()` uses the exhaustive set automatically, so form→lemma coverage stays maximal for NLP.

**Note on verbs:** verb forms are currently returned exhaustively even by default (`include_variants` does not yet filter them). The verb-alternate detector over-flags the standard forms of *irregular* verbs — `esse`, `posse`, the present system of `eo`, `fers`/`fert` — so filtering verb alternates is not yet reliable and is deferred to a future release. The `alternate` flag on verb forms should therefore be treated as advisory.

## Acknowledgments

This project is built on [**Whitaker's Words**](https://mk270.github.io/whitakers-words/), a Latin dictionary and morphological analysis program created by Colonel William A. Whitaker (USAF, Retired). The WORDS system — including its lexicon (DICTLINE), inflection tables (INFLECTS), and morphological analysis logic — is the foundation of `latincy-lexicon`. Whitaker made all parts of the WORDS system freely available for any purpose ("Permission is hereby freely given for any and all use of program and data.", cf. [here](https://mk270.github.io/whitakers-words/introduction.html)); this project exists because of that generosity. 

The WORDS data files used by this project are maintained at [mk270/whitakers-words](https://github.com/mk270/whitakers-words). Thank you to [Martin Keegan](https://mk270.github.io/whitakers-words/plan.html) for continuing Whitaker's work and sharing that work in the same spirit.

## License

The original Python code in this project is released under the [MIT License](LICENSE).

The Whitaker's Words data and analysis logic incorporated in this project are copyright William A. Whitaker (1936–2010) and distributed under his original permissive license (see [LICENSE](LICENSE) for full text).
