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


# =============================================================================
# Whitaker's Words Component (lexicon + analyzer)
# =============================================================================


@Language.factory(
    "whitakers_words",
    default_config={"lexicon_path": None, "analyzer_path": None},
    assigns=["token._.lexicon", "token._.ww", "token._.gloss"],
)
def create_whitakers_words(
    nlp: Language,
    name: str,
    lexicon_path: Optional[str] = None,
    analyzer_path: Optional[str] = None,
) -> "WhitakersWords":
    """Create the Whitaker's Words pipeline component."""
    return WhitakersWords(
        nlp, name, lexicon_path=lexicon_path, analyzer_path=analyzer_path,
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
                 analyzer_path: Optional[str] = None) -> None:
        self.name = name
        self._nlp = nlp
        self._lexicon: dict = {}
        self._analyzer = None
        self._lexicon_path = lexicon_path
        self._analyzer_path = analyzer_path
        # `_loaded` is True once any configured paths have been read into
        # memory. Lazy so that pipelines that merely inspect `nlp.pipe_names`
        # or round-trip via to_disk/from_disk don't pay the ~500ms load cost.
        self._loaded = not (lexicon_path or analyzer_path)
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
        if self._lexicon_path and not self._lexicon:
            self._load_lexicon(self._lexicon_path)
        if self._analyzer_path and self._analyzer is None:
            self._load_analyzer(self._analyzer_path)
        self._loaded = True

    def _load_lexicon(self, path) -> None:
        with open(path) as f:
            self._lexicon = json.load(f)

    def _load_analyzer(self, path: str) -> None:
        from latincy_lexicon.analyzer import Analyzer
        self._analyzer = Analyzer.from_json(path)

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
            # Lexicon lookup (by lemma)
            if self._lexicon:
                lemma = normalize_latin(token.lemma_)
                entries = self._lexicon.get(lemma)
                if entries:
                    token._.lexicon = _rank_by_pos(entries, token.pos_)

            # Morphological analysis (by surface form)
            if self._analyzer and not token.is_punct and not token.is_space:
                parses = self._analyzer.analyze(token.text)
                if parses:
                    parse_dicts = [p.to_dict() for p in parses]
                    # Stage 1: POS partition (hard filter)
                    pos_match, pos_other = _partition_by_pos(parse_dicts, token.pos_)
                    # Stage 2: Multi-signal scoring within each group
                    if len(pos_match) > 1:
                        pos_match = _rank_by_context(pos_match, token)
                    if len(pos_other) > 1:
                        pos_other = _rank_by_context(pos_other, token)
                    ranked = pos_match + pos_other
                    token._.ww = ranked
                    # Best-fit gloss: first semicolon-delimited clause from top parse
                    if ranked:
                        meaning = ranked[0].get("meaning", "")
                        token._.gloss = meaning.split(";")[0].strip() if meaning else None

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
        return self

    def to_bytes(self, *, exclude: tuple = ()) -> bytes:
        # Force load so the lexicon dict is in memory for embedding.
        self._ensure_loaded()
        data: dict = {}
        if self._lexicon:
            data["lexicon"] = self._lexicon
        if self._analyzer_path:
            data["analyzer_path"] = self._analyzer_path
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
        return self


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
    default_config={"analyzer_path": None},
    assigns=["token._.paradigm", "token._.reinflect"],
)
def create_paradigm_generator(
    nlp: Language,
    name: str,
    analyzer_path: Optional[str] = None,
) -> "ParadigmGenerator":
    """Create a paradigm generator pipeline component."""
    return ParadigmGenerator(nlp, name, analyzer_path=analyzer_path)


class ParadigmGenerator:
    """Paradigm generator: ``token._.paradigm`` and ``token._.reinflect()``.

    For each non-punctuation/space token, generates the full inflectional
    paradigm from the token's lemma using the WW Generator engine.
    Paradigms are cached by lemma within a single ``__call__`` invocation.

    The ``reinflect`` method extension allows morphological overrides:
    ``token._.reinflect(Number="Plur")`` returns the plural form string.
    """

    def __init__(self, nlp: Language, name: str, *,
                 analyzer_path: Optional[str] = None) -> None:
        self.name = name
        self._nlp = nlp
        self._generator = None
        self._analyzer_path = analyzer_path

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
                forms = self._generator.generate(lemma, pos=ww_pos)
                if forms:
                    cache[cache_key] = [
                        {"form": f.form, "lemma": f.lemma,
                         "upos": f.upos, "feats": _parse_feats(f.feats)}
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
                json.dump({"analyzer_path": self._analyzer_path}, f)

    def from_disk(self, path: str, *, exclude: tuple = ()) -> "ParadigmGenerator":
        path = Path(path)
        config_file = path / "generator_config.json"
        if config_file.exists():
            with open(config_file) as f:
                cfg = json.load(f)
            if cfg.get("analyzer_path"):
                # Defer the actual Generator.from_json() until first __call__.
                self._analyzer_path = cfg["analyzer_path"]
        return self

    def to_bytes(self, *, exclude: tuple = ()) -> bytes:
        if self._analyzer_path:
            return json.dumps({"analyzer_path": self._analyzer_path}).encode("utf-8")
        return b""

    def from_bytes(self, data: bytes, *, exclude: tuple = ()) -> "ParadigmGenerator":
        if data:
            cfg = json.loads(data.decode("utf-8"))
            if cfg.get("analyzer_path"):
                # Defer the actual Generator.from_json() until first __call__.
                self._analyzer_path = cfg["analyzer_path"]
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
    """Rank lexicon entries: POS-matching first, then by frequency."""
    if not token_pos:
        return sorted(entries, key=lambda e: -_FREQ_SCORE.get(e.get("freq", "X"), 0.3))
    matching = [e for e in entries if token_pos in e.get("ud_pos", [])]
    other = [e for e in entries if token_pos not in e.get("ud_pos", [])]
    # Within each group, sort by frequency (A > B > ... > X)
    matching.sort(key=lambda e: -_FREQ_SCORE.get(e.get("freq", "X"), 0.3))
    other.sort(key=lambda e: -_FREQ_SCORE.get(e.get("freq", "X"), 0.3))
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
