"""spaCy integration for latincy-lexicon.

Two pipeline components:

1. **whitakers_words** — Combined dictionary lookup + rule-based morphological
   analysis. Attaches ``token._.lexicon`` (dictionary entries by lemma),
   ``token._.ww`` (morphological parses by surface form), and
   ``token._.gloss`` (short definition from best parse).

2. **paradigm_generator** — Full paradigm generation via ``token._.paradigm``
   and reinflection via ``token._.reinflect()``. Given a token's lemma,
   generates all inflected forms and allows morphological overrides.

Both support POS-aware ranking when an upstream tagger is present.
"""

import json
from pathlib import Path
from typing import Optional

from spacy.language import Language
from spacy.tokens import Doc, Token

from latincy_lexicon.align.normalize import normalize_latin
from latincy_lexicon.build import sense_index_path, senses_path
from latincy_lexicon.glosses import (
    extract_sources,
    split_glosses,
    strip_usage_note,
)

# =============================================================================
# Whitaker's Words Component (lexicon + analyzer)
# =============================================================================


@Language.factory(
    "whitakers_words",
    default_config={"lexicon_path": None, "analyzer_path": None, "macron_path": None,
                    "ls_index_path": None, "ls_senses_path": None,
                    "use_bundled_lexicon": True},
    assigns=["token._.lexicon", "token._.ww", "token._.gloss"],
)
def create_whitakers_words(
    nlp: Language,
    name: str,
    lexicon_path: Optional[str] = None,
    analyzer_path: Optional[str] = None,
    macron_path: Optional[str] = None,
    ls_index_path: Optional[str] = None,
    ls_senses_path: Optional[str] = None,
    use_bundled_lexicon: bool = True,
) -> "WhitakersWords":
    """Create the Whitaker's Words pipeline component."""
    return WhitakersWords(
        nlp, name, lexicon_path=lexicon_path, analyzer_path=analyzer_path,
        macron_path=macron_path,
        ls_index_path=ls_index_path, ls_senses_path=ls_senses_path,
        use_bundled_lexicon=use_bundled_lexicon,
    )


class WhitakersWords:
    """Combined dictionary lookup and morphological analyzer.

    Provides three token extensions:

    - ``token._.lexicon`` — list of dictionary entry dicts (glosses, principal
      parts, POS, metadata), keyed by lemma. POS-ranked and frequency-sorted.
    - ``token._.ww`` — list of morphological parse dicts from the Words
      stem+ending engine, keyed by surface form. Multi-signal ranked.
    - ``token._.gloss`` — short definition from the top-ranked parse.

    Either data source is optional: pass only ``lexicon_path`` for dictionary
    lookups, only ``analyzer_path`` for morphological analysis, or both.
    """

    # Components whose output we use for ranking (best when all are upstream)
    _UPSTREAM_DEPS = {"tagger", "morphologizer", "parser", "ner",
                      "trainable_lemmatizer", "lemmatizer", "lookup_lemmatizer"}

    def __init__(self, nlp: Language, name: str, *,
                 lexicon_path: Optional[str] = None,
                 analyzer_path: Optional[str] = None,
                 macron_path: Optional[str] = None,
                 ls_index_path: Optional[str] = None,
                 ls_senses_path: Optional[str] = None,
                 use_bundled_lexicon: bool = True) -> None:
        self.name = name
        self._nlp = nlp
        self._lexicon: dict = {}
        self._analyzer = None
        self._lexicon_path = lexicon_path
        self._analyzer_path = analyzer_path
        self._macron_path = macron_path
        # Optional Lewis & Short gloss fallback (index: lemma → [entry ids];
        # senses: entry id → {"senses": [...]}). Loaded lazily on first use.
        self._ls_index_path = ls_index_path
        self._ls_senses_path = ls_senses_path
        self._ls_index: dict = {}
        self._ls_senses: dict = {}
        # Zero-config default: with no data source configured at all, fall back
        # to the bundled in-memory lexicon (built from DICTLINE, cached) so
        # `nlp.add_pipe("whitakers_words")` Just Works for a pip-installed user.
        # An explicit lexicon_path / analyzer_path / ls_index_path opts out, as
        # does use_bundled_lexicon=False (analyzer-only or empty component).
        self._use_bundled_lexicon = (
            use_bundled_lexicon
            and not lexicon_path
            and not analyzer_path
            and not ls_index_path
        )
        # `_loaded` is True once any configured paths have been read into
        # memory. Lazy so that pipelines that merely inspect `nlp.pipe_names`
        # or round-trip via to_disk/from_disk don't pay the ~500ms load cost.
        self._loaded = not (
            lexicon_path or analyzer_path or ls_index_path or self._use_bundled_lexicon
        )
        self._warned = False

        if not Token.has_extension("lexicon"):
            Token.set_extension("lexicon", default=None)
        if not Token.has_extension("ww"):
            Token.set_extension("ww", default=None)
        if not Token.has_extension("gloss"):
            Token.set_extension("gloss", default=None)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self._use_bundled_lexicon and not self._lexicon:
            from latincy_lexicon.build import build_lexicon

            self._lexicon = build_lexicon()
        if self._lexicon_path and not self._lexicon:
            self._load_lexicon(self._lexicon_path)
        if self._analyzer_path and self._analyzer is None:
            self._load_analyzer(self._analyzer_path)
        if self._ls_index_path and not self._ls_index:
            with open(self._ls_index_path) as f:
                self._ls_index = json.load(f)
        if self._ls_senses_path and not self._ls_senses:
            with open(self._ls_senses_path) as f:
                self._ls_senses = json.load(f)
        self._loaded = True

    def _ls_gloss(self, lemma: str) -> Optional[str]:
        """First Lewis & Short display gloss for a lemma, or None."""
        if not (self._ls_index and self._ls_senses and lemma):
            return None
        ids = self._ls_index.get(normalize_latin(lemma))
        if not ids:
            return None
        senses = self._ls_senses.get(ids[0], {}).get("senses", [])
        if not senses:
            return None
        return senses[0].get("display_gloss") or senses[0].get("gloss") or None

    def _load_lexicon(self, path) -> None:
        with open(path) as f:
            self._lexicon = json.load(f)

    def _load_analyzer(self, path: str) -> None:
        from latincy_lexicon.analyzer import Analyzer
        self._analyzer = Analyzer.from_json(path, macron_path=self._macron_path)

    def _check_pipeline_position(self) -> None:
        """Warn once if placed before components we depend on."""
        if self._warned:
            return
        self._warned = True
        pipe_names = self._nlp.pipe_names
        if self.name not in pipe_names:
            return
        my_idx = pipe_names.index(self.name)
        after_us = set(pipe_names[my_idx + 1:])

        # Lexicon needs lemmatizer upstream
        if self._lexicon:
            lemmatizers = {"trainable_lemmatizer", "lemmatizer", "lookup_lemmatizer"} & after_us
            if lemmatizers:
                import warnings
                warnings.warn(
                    f"whitakers_words is placed before {sorted(lemmatizers)} in the pipeline. "
                    f"Move it after the lemmatizer — lexicon keys are lemma-based.",
                    UserWarning,
                    stacklevel=3,
                )

        # Analyzer benefits from all upstream components
        if self._analyzer:
            misplaced = self._UPSTREAM_DEPS & after_us
            if misplaced:
                import warnings
                warnings.warn(
                    f"whitakers_words is placed before {sorted(misplaced)} in the pipeline. "
                    f"Move it after these components for better disambiguation. "
                    f"whitakers_words uses POS, morph, lemma, dep, and NER for ranking.",
                    UserWarning,
                    stacklevel=3,
                )

    def __call__(self, doc: Doc) -> Doc:
        self._ensure_loaded()
        self._check_pipeline_position()

        for token in doc:
            if token.is_punct or token.is_space:
                continue

            # Run the analyzer once and reuse — both the entry enrichment
            # below and the token._.ww extension consume the same parses.
            parses = self._analyzer.analyze(token.text) if self._analyzer else []

            # Lexicon entries: lemma-based lookup, augmented with entries
            # whose headword shows up in any morphological parse of the
            # surface form. Without this augmentation, a form like `cano`
            # (lemmatized to verb cano) would never surface the adj canus
            # entry that legitimately produces `cano` as dat/abl m/n sg.
            #
            # Dedup is content-based — (headword, pos, glosses) — so two
            # legitimate same-pos homographs (e.g. carmen 'song' freq=A
            # and carmen 'card for wool' freq=F, both NOUN) both survive,
            # while the same entry reached via lemma + inflection paths
            # collapses to one row.
            if self._lexicon:
                entries: list[dict] = []
                seen: set[tuple] = set()

                def _entry_key(e: dict) -> tuple:
                    return (
                        e["headword"],
                        e["pos"],
                        tuple(e.get("glosses") or ()),
                    )

                lemma_key = normalize_latin(token.lemma_) if token.lemma_ else None
                if lemma_key:
                    for e in self._lexicon.get(lemma_key, []):
                        key = _entry_key(e)
                        if key not in seen:
                            seen.add(key)
                            entries.append(e)

                for p in parses:
                    hw_key = normalize_latin(p.headword)
                    for e in self._lexicon.get(hw_key, []):
                        if e["pos"] != p.pos:
                            continue
                        key = _entry_key(e)
                        if key not in seen:
                            seen.add(key)
                            entries.append({**e, "match_type": "inflection"})

                if entries:
                    token._.lexicon = _rank_by_pos(entries, token.pos_)

            # Morphological parses extension (rank-aware, POS-partitioned).
            if parses:
                parse_dicts = [p.to_dict() for p in parses]
                pos_match, pos_other = _partition_by_pos(parse_dicts, token.pos_)
                if len(pos_match) > 1:
                    pos_match = _rank_by_context(pos_match, token)
                if len(pos_other) > 1:
                    pos_other = _rank_by_context(pos_other, token)
                ranked = pos_match + pos_other
                token._.ww = ranked
                # Best-fit gloss: first semicolon-delimited clause from top parse
                if ranked:
                    meaning = ranked[0].get("meaning", "")
                    parts = split_glosses(meaning) if meaning else []
                    if parts:
                        clean, _ = extract_sources(parts[0])
                        token._.gloss = strip_usage_note(clean) or None
                    else:
                        token._.gloss = None

            # Lexicon fallback: when no parse-based gloss is available (e.g.
            # 'iustitia', whose surface form the analyzer doesn't segment), fall
            # back to the top lexicon entry's first sense so the token is still
            # glossed. The entry's glosses are already split at build time.
            if token._.gloss is None and token._.lexicon:
                lex_glosses = token._.lexicon[0].get("glosses") or []
                if lex_glosses:
                    token._.gloss = strip_usage_note(lex_glosses[0])

            # Final fallback: Lewis & Short (only when configured with ls paths).
            # Fill-only — never overrides a Whitaker gloss already in place.
            if token._.gloss is None and token.lemma_:
                ls = self._ls_gloss(token.lemma_)
                if ls:
                    token._.gloss = ls

        return doc

    def to_disk(self, path: str, *, exclude: tuple = ()) -> None:
        # Force load so the lexicon bytes are available for copy-out.
        self._ensure_loaded()
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        cfg: dict = {}
        if self._lexicon:
            with open(path / "lexicon.json", "w") as f:
                json.dump(self._lexicon, f, ensure_ascii=False)
        if self._analyzer_path:
            cfg["analyzer_path"] = self._analyzer_path
        if self._macron_path:
            cfg["macron_path"] = self._macron_path
        if cfg:
            with open(path / "ww_config.json", "w") as f:
                json.dump(cfg, f)

    def from_disk(self, path: str, *, exclude: tuple = ()) -> "WhitakersWords":
        path = Path(path)
        lexicon_file = path / "lexicon.json"
        if lexicon_file.exists():
            # Defer the actual json.load until first __call__.
            self._lexicon_path = str(lexicon_file)
            self._loaded = False
        config_file = path / "ww_config.json"
        if config_file.exists():
            with open(config_file) as f:
                cfg = json.load(f)
            if cfg.get("analyzer_path"):
                self._analyzer_path = cfg["analyzer_path"]
                self._loaded = False
            if cfg.get("macron_path"):
                self._macron_path = cfg["macron_path"]
        return self

    def to_bytes(self, *, exclude: tuple = ()) -> bytes:
        # Force load so the lexicon dict is in memory for embedding.
        self._ensure_loaded()
        data: dict = {}
        if self._lexicon:
            data["lexicon"] = self._lexicon
        if self._analyzer_path:
            data["analyzer_path"] = self._analyzer_path
        if self._macron_path:
            data["macron_path"] = self._macron_path
        return json.dumps(data, ensure_ascii=False).encode("utf-8") if data else b""

    def from_bytes(self, data: bytes, *, exclude: tuple = ()) -> "WhitakersWords":
        if data:
            d = json.loads(data.decode("utf-8"))
            if "lexicon" in d:
                # Already in memory; no path to defer.
                self._lexicon = d["lexicon"]
                self._lexicon_path = None
            if d.get("analyzer_path"):
                self._analyzer_path = d["analyzer_path"]
                self._loaded = False
            if d.get("macron_path"):
                self._macron_path = d["macron_path"]
        return self


# =============================================================================
# Lewis & Short Component
# =============================================================================

# UD POS → WW POS code, used to drive L&S homograph ranking.
_UD_TO_WW_POS_LS: dict[str, str] = {
    "NOUN": "N", "PROPN": "N", "VERB": "V", "AUX": "V",
    "ADJ": "ADJ", "ADV": "ADV", "ADP": "PREP",
    "CCONJ": "CONJ", "SCONJ": "CONJ", "INTJ": "INTERJ",
    "PRON": "PRON", "DET": "PRON", "NUM": "NUM",
}


@Language.factory(
    "lewis_short",
    default_config={"ls_index_path": None, "ls_store_path": None, "include_text": False,
                    "attach_senses": False},
    assigns=["token._.lewis_short", "token._.lewis_short_senses"],
)
def create_lewis_short(
    nlp: Language,
    name: str,
    ls_index_path: Optional[str] = None,
    ls_store_path: Optional[str] = None,
    ls_senses_path: Optional[str] = None,
    include_text: bool = False,
    attach_senses: bool = False,
) -> "LewisShort":
    """Create the Lewis & Short lookup component."""
    return LewisShort(
        nlp, name, ls_index_path=ls_index_path, ls_store_path=ls_store_path,
        ls_senses_path=ls_senses_path, include_text=include_text,
        attach_senses=attach_senses,
    )


class LewisShort:
    """Attach ranked Lewis & Short entries to ``token._.lewis_short``.

    For each token, the lemma (falling back to the surface form) is normalized
    and looked up in ``lewis_short_index.json``. Homograph candidates are ranked
    best-first by part-of-speech compatibility — nothing is dropped.

    Each result is a lightweight handle: ``{"id", "key", "orth", "pos", "gen",
    "itype"}`` (the short metadata), but **not** the entry's ~tens-of-KB
    ``text`` — so a ``Doc`` stays lean and serializable. Pass
    ``include_text=True`` to inline the full article on every token, or fetch
    it on demand for a single id via :meth:`get_entry`. Headword and short
    gloss are expected to come from the ``whitakers_words`` component upstream;
    ``lewis_short`` is a pure dictionary-article overlay.

    Both files are loaded lazily on first ``__call__`` (the store is ~28 MB),
    so merely inspecting the pipeline pays no load cost.

    Pass ``attach_senses=True`` to also populate
    ``token._.lewis_short_senses`` with the top-ranked entry's structured
    senses as a lean list of ``{"level", "n", "display_gloss"}`` dicts (raw
    ``gloss``, ``citations`` and ``sameAs`` stay behind :meth:`get_senses`).
    Off by default: the sense store is ~48 MB and loads lazily on the first
    call that needs it.
    """

    # Short metadata fields kept on the lean per-token handle (text excluded).
    _HANDLE_FIELDS = ("key", "orth", "pos", "gen", "itype")
    # Sense fields kept on the lean token._.lewis_short_senses dicts.
    _SENSE_FIELDS = ("level", "n", "display_gloss")

    def __init__(self, nlp: Language, name: str, *,
                 ls_index_path: Optional[str] = None,
                 ls_store_path: Optional[str] = None,
                 ls_senses_path: Optional[str] = None,
                 include_text: bool = False,
                 attach_senses: bool = False) -> None:
        self.name = name
        self._nlp = nlp
        self._index: dict[str, list[str]] = {}
        self._store: dict[str, dict] = {}
        self._senses: dict[str, dict] = {}
        # Auto-discover bundled files when no explicit path is provided.
        if ls_index_path is None:
            bundled = sense_index_path()
            if bundled.exists():
                ls_index_path = str(bundled)
        if ls_senses_path is None:
            bundled = senses_path()
            if bundled.exists():
                ls_senses_path = str(bundled)
        self._index_path = ls_index_path
        self._store_path = ls_store_path
        self._senses_path = ls_senses_path
        self._include_text = include_text
        self._attach_senses = attach_senses
        self._loaded = not ls_index_path
        self._senses_loaded = not ls_senses_path

        if not Token.has_extension("lewis_short"):
            Token.set_extension("lewis_short", default=None)
        if not Token.has_extension("lewis_short_senses"):
            Token.set_extension("lewis_short_senses", default=None)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self._index_path and not self._index:
            with open(self._index_path) as f:
                self._index = json.load(f)
        if self._store_path and not self._store:
            with open(self._store_path) as f:
                self._store = json.load(f)
        self._loaded = True

    def _ensure_senses_loaded(self) -> None:
        """Lazily load the sense store (independent of the entry store, which the
        sense API does not require)."""
        if self._senses_loaded:
            return
        if self._senses_path and not self._senses:
            with open(self._senses_path) as f:
                self._senses = json.load(f)
        self._senses_loaded = True

    def __call__(self, doc: Doc) -> Doc:
        self._ensure_loaded()
        if not self._index:
            return doc

        from latincy_lexicon.align.assimilate import assimilated_forms
        from latincy_lexicon.align.lewis_short import rank_ls_candidates

        for token in doc:
            if token.is_punct or token.is_space:
                continue

            key = normalize_latin(token.lemma_ or token.text)
            candidate_ids = self._index.get(key)
            if not candidate_ids:
                # Retry with the classical assimilated spelling (adcedo→accedo).
                for variant in assimilated_forms(key):
                    candidate_ids = self._index.get(variant)
                    if candidate_ids:
                        break
            if not candidate_ids:
                continue

            ww_pos = _UD_TO_WW_POS_LS.get(token.pos_, "")
            ranked = rank_ls_candidates(ww_pos, candidate_ids, self._store)
            token._.lewis_short = [self._handle(cid) for cid in ranked]

            # Tier-1 sense attachment: the top-ranked entry's senses, lean.
            # No selection logic — that's the WSD bridge (tier 2). get_senses
            # lazy-loads the ~48 MB store, which is why this is opt-in.
            if self._attach_senses:
                token._.lewis_short_senses = [
                    {f: s[f] for f in self._SENSE_FIELDS if f in s}
                    for s in self.get_senses(ranked[0])
                ]

        return doc

    def _handle(self, entry_id: str) -> dict:
        """Build the per-token result for one L&S id (lean unless include_text)."""
        entry = self._store.get(entry_id)
        if entry is None:
            return {"id": entry_id}
        if self._include_text:
            return {"id": entry_id, **entry}
        return {"id": entry_id, **{f: entry[f] for f in self._HANDLE_FIELDS if f in entry}}

    def get_entry(self, entry_id: str) -> Optional[dict]:
        """Return the full L&S entry dict (incl. ``text``) for an id, or None.

        Lets a consumer fetch the heavy article on demand when displaying a
        token that carries only a lean handle. Loads the store if needed.
        """
        self._ensure_loaded()
        entry = self._store.get(entry_id)
        return {"id": entry_id, **entry} if entry is not None else None

    def get_senses(self, entry_id: str) -> list[dict]:
        """Return the structured L&S sense list for an entry id (``[]`` if absent).

        Requires the component to have been configured with ``ls_senses_path``
        (the ``lewis_short_senses.json`` build artifact); loads it on first use.
        Each sense follows ``parsers.lewis_short_senses.parse_entry`` — ``id``,
        ``level``, ``gloss``, ``display_gloss``, ``sameAs``, ``citations``,
        ``citation_tr``.
        """
        self._ensure_senses_loaded()
        return self._senses.get(entry_id, {}).get("senses", [])

    def to_disk(self, path: str, *, exclude: tuple = ()) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        cfg = self._config()
        if cfg:
            with open(path / "lewis_short_config.json", "w") as f:
                json.dump(cfg, f)

    def from_disk(self, path: str, *, exclude: tuple = ()) -> "LewisShort":
        path = Path(path)
        config_file = path / "lewis_short_config.json"
        if config_file.exists():
            with open(config_file) as f:
                self._apply_config(json.load(f))
        return self

    def to_bytes(self, *, exclude: tuple = ()) -> bytes:
        cfg = self._config()
        return json.dumps(cfg).encode("utf-8") if cfg else b""

    def from_bytes(self, data: bytes, *, exclude: tuple = ()) -> "LewisShort":
        if data:
            self._apply_config(json.loads(data.decode("utf-8")))
        return self

    def _config(self) -> dict:
        cfg: dict = {}
        if self._index_path:
            cfg["ls_index_path"] = self._index_path
        if self._store_path:
            cfg["ls_store_path"] = self._store_path
        if self._senses_path:
            cfg["ls_senses_path"] = self._senses_path
        if self._include_text:
            cfg["include_text"] = True
        if self._attach_senses:
            cfg["attach_senses"] = True
        return cfg

    def _apply_config(self, cfg: dict) -> None:
        if cfg.get("ls_index_path"):
            self._index_path = cfg["ls_index_path"]
            self._loaded = False
        if cfg.get("ls_store_path"):
            self._store_path = cfg["ls_store_path"]
        if cfg.get("ls_senses_path"):
            self._senses_path = cfg["ls_senses_path"]
            self._senses_loaded = False
        self._include_text = bool(cfg.get("include_text", self._include_text))
        self._attach_senses = bool(cfg.get("attach_senses", self._attach_senses))


# =============================================================================
# Paradigm Generator Component
# =============================================================================

# UD POS → WW POS for Generator.generate(pos=...) filtering
_UD_TO_WW_POS: dict[str, str] = {
    "VERB": "V", "AUX": "V", "NOUN": "N", "PROPN": "N",
    "ADJ": "ADJ", "ADV": "ADV", "PRON": "PRON", "DET": "PRON",
    "NUM": "NUM",
}


def _parse_feats(feats_str: str) -> dict[str, str]:
    """Parse UD feature string 'A=x|B=y' into dict."""
    if not feats_str:
        return {}
    return dict(kv.split("=") for kv in feats_str.split("|"))


def _reinflect_method(token: Token, **overrides: str) -> str | None:
    """Reinflect a token by overriding specific morphological features.

    This is a spaCy method extension: the first positional arg is the token.
    Keyword args are UD feature overrides (e.g. Number="Plur", Tense="Imp").

    Searches the token's paradigm for a form whose features contain all
    target features (token's current morph merged with overrides).

    Returns the matching surface form string, or None if no match found.
    """
    paradigm = token._.paradigm
    if paradigm is None:
        return None

    # Build target features: token morph + overrides
    target = token.morph.to_dict()
    target.update(overrides)

    for entry in paradigm:
        entry_feats = entry.get("feats", {})
        # All target features must be present in entry
        if all(entry_feats.get(k) == v for k, v in target.items()):
            return entry["form"]
    return None


@Language.factory(
    "paradigm_generator",
    default_config={"analyzer_path": None, "include_variants": False},
    assigns=["token._.paradigm", "token._.reinflect"],
)
def create_paradigm_generator(
    nlp: Language,
    name: str,
    analyzer_path: Optional[str] = None,
    include_variants: bool = False,
) -> "ParadigmGenerator":
    """Create a paradigm generator pipeline component.

    ``include_variants`` (default ``False``) controls whether ``token._.paradigm``
    carries only the clean textbook paradigm or the full set including alternate
    forms (archaic/rare/proper-sense/verb-alternate). See ``Generator.generate``.
    """
    return ParadigmGenerator(
        nlp, name, analyzer_path=analyzer_path, include_variants=include_variants,
    )


class ParadigmGenerator:
    """Paradigm generator: ``token._.paradigm`` and ``token._.reinflect()``.

    For each non-punctuation/space token, generates the full inflectional
    paradigm from the token's lemma using the WW Generator engine.
    Paradigms are cached by lemma within a single ``__call__`` invocation.

    The ``reinflect`` method extension allows morphological overrides:
    ``token._.reinflect(Number="Plur")`` returns the plural form string.
    """

    def __init__(self, nlp: Language, name: str, *,
                 analyzer_path: Optional[str] = None,
                 include_variants: bool = False) -> None:
        self.name = name
        self._nlp = nlp
        self._generator = None
        self._analyzer_path = analyzer_path
        self._include_variants = include_variants

        if not Token.has_extension("paradigm"):
            Token.set_extension("paradigm", default=None)
        if not Token.has_extension("reinflect"):
            Token.set_extension("reinflect", method=_reinflect_method)

        # Generator is loaded lazily on first __call__ — see _ensure_loaded.

    def _ensure_loaded(self) -> None:
        if self._generator is None and self._analyzer_path:
            self._load_generator(self._analyzer_path)

    def _load_generator(self, path: str) -> None:
        from latincy_lexicon.generator import Generator
        self._generator = Generator.from_json(path)

    def __call__(self, doc: Doc) -> Doc:
        self._ensure_loaded()
        if self._generator is None:
            return doc

        # Cache paradigms by (normalized lemma, ww_pos) within this doc
        cache: dict[tuple[str, str | None], list[dict] | None] = {}

        for token in doc:
            if token.is_punct or token.is_space:
                continue

            lemma = normalize_latin(token.lemma_)
            ww_pos = _UD_TO_WW_POS.get(token.pos_)
            cache_key = (lemma, ww_pos)

            if cache_key not in cache:
                forms = self._generator.generate(
                    lemma, pos=ww_pos, include_variants=self._include_variants,
                )
                if forms:
                    cache[cache_key] = [
                        {"form": f.form, "lemma": f.lemma,
                         "upos": f.upos, "feats": _parse_feats(f.feats),
                         "alternate": f.alternate}
                        for f in forms
                    ]
                else:
                    cache[cache_key] = None

            token._.paradigm = cache[cache_key]

        return doc

    def to_disk(self, path: str, *, exclude: tuple = ()) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        if self._analyzer_path:
            with open(path / "generator_config.json", "w") as f:
                json.dump({
                    "analyzer_path": self._analyzer_path,
                    "include_variants": self._include_variants,
                }, f)

    def from_disk(self, path: str, *, exclude: tuple = ()) -> "ParadigmGenerator":
        path = Path(path)
        config_file = path / "generator_config.json"
        if config_file.exists():
            with open(config_file) as f:
                cfg = json.load(f)
            if cfg.get("analyzer_path"):
                # Defer the actual Generator.from_json() until first __call__.
                self._analyzer_path = cfg["analyzer_path"]
            self._include_variants = cfg.get("include_variants", False)
        return self

    def to_bytes(self, *, exclude: tuple = ()) -> bytes:
        if self._analyzer_path:
            return json.dumps({
                "analyzer_path": self._analyzer_path,
                "include_variants": self._include_variants,
            }).encode("utf-8")
        return b""

    def from_bytes(self, data: bytes, *, exclude: tuple = ()) -> "ParadigmGenerator":
        if data:
            cfg = json.loads(data.decode("utf-8"))
            if cfg.get("analyzer_path"):
                # Defer the actual Generator.from_json() until first __call__.
                self._analyzer_path = cfg["analyzer_path"]
            self._include_variants = cfg.get("include_variants", False)
        return self


# =============================================================================
# Shared utilities
# =============================================================================

# Map Words POS → UD POS for ranking
_WORDS_TO_UD = {
    "N": {"NOUN", "PROPN"}, "V": {"VERB", "AUX"}, "ADJ": {"ADJ"},
    "ADV": {"ADV"}, "PREP": {"ADP"}, "CONJ": {"CCONJ", "SCONJ"},
    "INTERJ": {"INTJ"}, "PRON": {"PRON", "DET"}, "NUM": {"NUM"},
    "VPAR": {"VERB", "ADJ"}, "SUPINE": {"VERB"},
}

_FREQ_SCORE = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.2, "F": 0.1, "X": 0.3}


def _rank_by_pos(entries: list, token_pos: str) -> list:
    """Rank lexicon entries: POS-matching first, then lemma-matched, then by
    frequency.

    Within each POS group, entries found via the token's lemma outrank entries
    added via inflectional parses of the surface form. The lemmatizer already
    committed to a lemma; a same-POS homograph reached only through a surface
    parse (form ``dea`` also parsing under ``deus``) must not beat it on raw
    frequency, or downstream citation forms pick the wrong entry.
    """
    def _key(e: dict) -> tuple:
        return (
            e.get("match_type") == "inflection",
            -_FREQ_SCORE.get(e.get("freq", "X"), 0.3),
        )

    if not token_pos:
        return sorted(entries, key=_key)
    matching = [e for e in entries if token_pos in e.get("ud_pos", [])]
    other = [e for e in entries if token_pos not in e.get("ud_pos", [])]
    matching.sort(key=_key)
    other.sort(key=_key)
    return matching + other


def _partition_by_pos(parse_dicts: list, token_pos: str) -> tuple[list, list]:
    """Partition WW parse dicts into POS-matching and non-matching groups."""
    if not token_pos:
        return parse_dicts, []
    matching = []
    other = []
    for p in parse_dicts:
        ww_pos = p.get("pos", "")
        ud_tags = _WORDS_TO_UD.get(ww_pos, set())
        if token_pos in ud_tags:
            matching.append(p)
        else:
            other.append(p)
    return matching, other


# UD morph → WW morph mappings
_UD_TO_WW = {
    "Case":   {"Nom": "NOM", "Gen": "GEN", "Dat": "DAT", "Acc": "ACC",
               "Abl": "ABL", "Voc": "VOC", "Loc": "LOC"},
    "Number": {"Sing": "S", "Plur": "P"},
    "Gender": {"Masc": "M", "Fem": "F", "Neut": "N", "Com": "C"},
    "Tense":  {"Pres": "PRES", "Past": "PERF", "Imp": "IMPF",
               "Fut": "FUT", "Pqp": "PLUP", "Ftp": "FUTP"},
    "Mood":   {"Ind": "IND", "Sub": "SUB", "Imp": "IMP", "Inf": "INF"},
    "Voice":  {"Act": "ACTIVE", "Pass": "PASSIVE"},
    "Person": {"1": "1", "2": "2", "3": "3"},
}
_UD_FEAT_TO_WW_FIELD = {
    "Case": "case", "Number": "number", "Gender": "gender",
    "Tense": "tense", "Mood": "mood", "Voice": "voice", "Person": "person",
}

# Dependency label → expected case (Latin-specific)
_DEP_TO_CASE = {
    "nsubj": "NOM", "nsubj:pass": "NOM",
    "obj": "ACC", "iobj": "DAT",
    "obl": "ABL", "obl:arg": "ABL",
    "nmod": "GEN", "vocative": "VOC",
}


def _rank_by_context(parse_dicts: list, token: Token) -> list:
    """Rank WW parses using all available LatinCy upstream signals.

    Scoring layers (cumulative):
      1. Lemma match    (weight 4) — spaCy lemma == WW lemma (strongest signal)
      2. Morph features (weight 2) — case, number, gender, tense, mood, voice, person
      3. Dep label      (weight 1) — syntactic role → expected case
      4. NER context    (weight 1) — entity label suggests proper noun / place / group
      5. Frequency      (weight 0.5) — WW dictionary frequency as tiebreaker

    POS is already handled by the partition step (hard filter).
    """
    from latincy_lexicon.align.normalize import normalize_latin

    # --- Gather upstream signals (degrade gracefully if missing) ---
    spacy_lemma = normalize_latin(token.lemma_) if token.lemma_ else ""
    morph = token.morph.to_dict()
    dep = token.dep_ if token.dep_ else ""
    ent_type = token.ent_type_ if token.ent_type_ else ""

    # Build expected morph values
    expected_morph: dict[str, str] = {}
    for ud_key, ww_map in _UD_TO_WW.items():
        ud_val = morph.get(ud_key)
        if ud_val and ud_val in ww_map:
            expected_morph[_UD_FEAT_TO_WW_FIELD[ud_key]] = ww_map[ud_val]

    # Expected case from dependency
    dep_case = _DEP_TO_CASE.get(dep)

    scored = []
    for p in parse_dicts:
        score = 0.0

        # 1. Lemma match (weight 4)
        ww_lemma = normalize_latin(p.get("lemma", ""))
        if spacy_lemma and ww_lemma:
            if spacy_lemma == ww_lemma:
                score += 4.0

        # 2. Morph features (weight 2, distributed across features)
        if expected_morph:
            n_features = len(expected_morph)
            per_feat = 2.0 / max(n_features, 1)
            for ww_field, ww_val in expected_morph.items():
                p_val = p.get(ww_field, "X")
                if p_val == ww_val:
                    score += per_feat
                elif p_val in ("X", "C"):
                    score += per_feat * 0.25  # doesn't contradict

        # 3. Dependency → case (weight 1)
        if dep_case:
            p_case = p.get("case", "X")
            if p_case == dep_case:
                score += 1.0
            elif p_case in ("X", "C"):
                score += 0.25

        # 4. NER context (weight 1)
        if ent_type:
            ww_noun_kind = p.get("noun_kind", "X")
            # LOC entities → prefer place nouns; PER → person nouns
            if ent_type == "LOC" and ww_noun_kind == "L":
                score += 1.0
            elif ent_type in ("PER", "PERSON") and ww_noun_kind == "P":
                score += 1.0
            elif ent_type == "NORP" and ww_noun_kind == "T":
                score += 1.0
            # Proper noun entries get a boost for any entity
            if p.get("pos") == "N" and ww_noun_kind not in ("X", "S"):
                score += 0.5

        # 5. Frequency (weight 0.5)
        score += _FREQ_SCORE.get(p.get("freq", "X"), 0.3) * 0.5

        scored.append((-score, p))

    scored.sort(key=lambda x: x[0])
    return [p for _, p in scored]
