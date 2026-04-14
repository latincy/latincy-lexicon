"""Tests for the Generator class."""

import json
import pytest
from pathlib import Path


ANALYZER_JSON = Path(__file__).parent.parent / "data" / "json" / "analyzer.json"

skip_no_data = pytest.mark.skipif(
    not ANALYZER_JSON.exists(),
    reason="analyzer.json not available (run: latincy-lexicon build)",
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _feats_dict(feats_str: str) -> dict[str, str]:
    """Parse UD feature string 'A=x|B=y' into dict."""
    if not feats_str:
        return {}
    return dict(kv.split("=") for kv in feats_str.split("|"))


def _find_form(forms, surface: str, **kw) -> bool:
    """Return True if *forms* contains *surface* with matching feats.

    Keyword args are UD feature key=value pairs that must all appear in
    the form's feats string.  Keys not mentioned are ignored (partial match).
    """
    for f in forms:
        if f.form != surface:
            continue
        fd = _feats_dict(f.feats)
        if all(fd.get(k) == v for k, v in kw.items()):
            return True
    return False


@skip_no_data
class TestGeneratorLookup:
    """Generator finds DICTLINE entries by lemma."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from latincy_lexicon.generator import Generator
        self.gen = Generator.from_json(ANALYZER_JSON)

    def test_lookup_amo(self):
        """Regular 1st conjugation verb."""
        entries = self.gen.lookup("amo")
        assert len(entries) >= 1
        verb_entries = [e for e in entries if e["pos"] == "V"]
        assert len(verb_entries) >= 1
        # Find the 1st conjugation entry (there may also be an 8.1 variant)
        v1_entries = [e for e in verb_entries if e["decl_which"] == 1]
        assert len(v1_entries) >= 1
        e = v1_entries[0]
        assert e["stem1"] == "am"
        assert e["decl_which"] == 1

    def test_lookup_rex(self):
        """3rd declension noun."""
        entries = self.gen.lookup("rex")
        noun_entries = [e for e in entries if e["pos"] == "N"]
        assert len(noun_entries) >= 1
        e = noun_entries[0]
        assert e["stem2"] == "reg"
        assert e["decl_which"] == 3

    def test_lookup_sum(self):
        """Irregular verb (V 5.1)."""
        entries = self.gen.lookup("sum")
        verb_entries = [e for e in entries if e["pos"] == "V"]
        assert len(verb_entries) >= 1
        e = verb_entries[0]
        assert e["decl_which"] == 5

    def test_lookup_fero(self):
        """Irregular verb (V 3.2) with suppletive stems."""
        entries = self.gen.lookup("fero")
        verb_entries = [e for e in entries if e["pos"] == "V"]
        assert len(verb_entries) >= 1
        e = verb_entries[0]
        assert e["stem3"] == "tul"
        assert e["stem4"] == "lat"

    def test_lookup_unknown(self):
        """Unknown lemma returns empty list."""
        entries = self.gen.lookup("xyzzyplugh")
        assert entries == []

    def test_lookup_normalizes(self):
        """Lookup normalizes v→u, j→i."""
        entries_v = self.gen.lookup("verbum")
        entries_u = self.gen.lookup("uerbum")
        assert len(entries_v) > 0
        assert entries_v == entries_u


@skip_no_data
class TestGenerateVerb:
    """Generator produces correct verb paradigm forms."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from latincy_lexicon.generator import Generator
        self.gen = Generator.from_json(ANALYZER_JSON)

    # -- Regular 1st conjugation: amo --

    def test_amo_present_1s(self):
        """amo 1s pres ind act = 'amo'."""
        forms = self.gen.generate("amo")
        assert _find_form(
            forms, "amo",
            Mood="Ind", Tense="Pres", Number="Sing",
            Person="1", Voice="Act",
        )

    def test_amo_imperfect_3s(self):
        """amabat 3s impf ind act."""
        forms = self.gen.generate("amo")
        assert _find_form(
            forms, "amabat",
            Mood="Ind", Tense="Imp", Number="Sing",
            Person="3", Voice="Act",
        )

    def test_amo_perfect_1s(self):
        """amavi 1s perf ind act (stem3 = amav, generic V 0.0)."""
        forms = self.gen.generate("amo")
        assert _find_form(
            forms, "amavi",
            Mood="Ind", Tense="Past", Number="Sing",
            Person="1", Voice="Act", Aspect="Perf",
        )

    def test_amo_ppp_nom_s_m(self):
        """amatus NOM.S.M PPP (stem4 via VPAR 0.0)."""
        forms = self.gen.generate("amo")
        assert _find_form(
            forms, "amatus",
            VerbForm="Part", Tense="Past", Voice="Pass",
            Case="Nom", Number="Sing", Gender="Masc",
        )

    def test_amo_supine_acc(self):
        """amatum supine ACC (stem4 via SUPINE 0.0)."""
        forms = self.gen.generate("amo")
        assert _find_form(
            forms, "amatum",
            VerbForm="Sup", Case="Acc",
        )

    def test_amo_present_participle(self):
        """amans pres act participle NOM.S (VPAR 1.0, stem1)."""
        forms = self.gen.generate("amo")
        assert _find_form(
            forms, "amans",
            VerbForm="Part", Tense="Pres", Voice="Act",
            Case="Nom", Number="Sing",
        )

    def test_amo_upos_is_verb(self):
        """Regular verb → UPOS = VERB."""
        forms = self.gen.generate("amo")
        verb_forms = [f for f in forms if f.upos == "VERB"]
        assert len(verb_forms) > 0

    # -- Irregular: sum (V 5.1, verb_kind=TO_BE) --

    def test_sum_present_1s(self):
        """sum 1s pres ind act (V 5.1, stem1='s')."""
        forms = self.gen.generate("sum")
        assert _find_form(
            forms, "sum",
            Mood="Ind", Tense="Pres", Number="Sing",
            Person="1", Voice="Act",
        )

    def test_sum_upos_is_aux(self):
        """sum verb_kind=TO_BE → UPOS = AUX."""
        forms = self.gen.generate("sum")
        aux_forms = [f for f in forms if f.upos == "AUX"]
        assert len(aux_forms) > 0
        # All finite forms should be AUX
        verb_forms = [f for f in forms if f.upos == "VERB"]
        assert len(verb_forms) == 0

    # -- Irregular: fero (V 3.2, suppletive stems) --

    def test_fero_perfect_1s(self):
        """tuli 1s perf ind act (stem3='tul', generic V 0.0)."""
        forms = self.gen.generate("fero")
        assert _find_form(
            forms, "tuli",
            Mood="Ind", Tense="Past", Number="Sing",
            Person="1", Voice="Act", Aspect="Perf",
        )

    def test_fero_ppp_nom_s_m(self):
        """latus NOM.S.M PPP (stem4='lat', VPAR 0.0)."""
        forms = self.gen.generate("fero")
        assert _find_form(
            forms, "latus",
            VerbForm="Part", Tense="Past", Voice="Pass",
            Case="Nom", Number="Sing", Gender="Masc",
        )


@skip_no_data
class TestGenerateNoun:
    """Generator produces correct noun paradigm forms.

    NOTE on Gender: WW inflection rules encode gender as "X" (any) or
    "C" (common) for most noun rules. The entry itself carries the
    lexical gender (M/F/N), but ``_build_feats()`` reads gender from the
    *rule*, not the entry. So generated noun forms may show Gender=Com
    or omit Gender entirely. This is a known limitation — the generator
    is form-correct but gender-underspecified for nouns.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        from latincy_lexicon.generator import Generator
        self.gen = Generator.from_json(ANALYZER_JSON)

    # -- 1st declension feminine: puella --

    def test_puella_nom_s(self):
        """puella NOM.S (N 1.1, stem1='puell')."""
        forms = self.gen.generate("puella", pos="N")
        assert _find_form(forms, "puella", Case="Nom", Number="Sing")

    def test_puella_gen_s(self):
        """puellae GEN.S."""
        forms = self.gen.generate("puella", pos="N")
        assert _find_form(forms, "puellae", Case="Gen", Number="Sing")

    def test_puella_acc_s(self):
        """puellam ACC.S."""
        forms = self.gen.generate("puella", pos="N")
        assert _find_form(forms, "puellam", Case="Acc", Number="Sing")

    def test_puella_abl_s(self):
        """puella ABL.S."""
        forms = self.gen.generate("puella", pos="N")
        assert _find_form(forms, "puella", Case="Abl", Number="Sing")

    def test_puella_nom_p(self):
        """puellae NOM.P."""
        forms = self.gen.generate("puella", pos="N")
        assert _find_form(forms, "puellae", Case="Nom", Number="Plur")

    def test_puella_acc_p(self):
        """puellas ACC.P."""
        forms = self.gen.generate("puella", pos="N")
        assert _find_form(forms, "puellas", Case="Acc", Number="Plur")

    def test_puella_upos(self):
        """1st declension noun → UPOS = NOUN."""
        forms = self.gen.generate("puella", pos="N")
        assert all(f.upos == "NOUN" for f in forms)

    # -- 2nd declension neuter: bellum --

    def test_bellum_nom_s(self):
        """bellum NOM.S (N 2.1, neuter)."""
        forms = self.gen.generate("bellum", pos="N")
        assert _find_form(forms, "bellum", Case="Nom", Number="Sing")

    def test_bellum_gen_s(self):
        """belli GEN.S."""
        forms = self.gen.generate("bellum", pos="N")
        assert _find_form(forms, "belli", Case="Gen", Number="Sing")

    def test_bellum_nom_p(self):
        """bella NOM.P (neuter plural -a)."""
        forms = self.gen.generate("bellum", pos="N")
        assert _find_form(forms, "bella", Case="Nom", Number="Plur")

    def test_bellum_acc_equals_nom(self):
        """Neuter nom and acc singular are identical (bellum)."""
        forms = self.gen.generate("bellum", pos="N")
        assert _find_form(forms, "bellum", Case="Nom", Number="Sing")
        assert _find_form(forms, "bellum", Case="Acc", Number="Sing")

    # -- 3rd declension masculine: rex --

    def test_rex_nom_s(self):
        """rex NOM.S (N 3.1, stem1='rex')."""
        forms = self.gen.generate("rex", pos="N")
        assert _find_form(forms, "rex", Case="Nom", Number="Sing")

    def test_rex_gen_s(self):
        """regis GEN.S (stem2='reg')."""
        forms = self.gen.generate("rex", pos="N")
        assert _find_form(forms, "regis", Case="Gen", Number="Sing")

    def test_rex_acc_s(self):
        """regem ACC.S."""
        forms = self.gen.generate("rex", pos="N")
        assert _find_form(forms, "regem", Case="Acc", Number="Sing")

    def test_rex_dat_p(self):
        """regibus DAT.P."""
        forms = self.gen.generate("rex", pos="N")
        assert _find_form(forms, "regibus", Case="Dat", Number="Plur")

    def test_rex_upos(self):
        """3rd declension noun → UPOS = NOUN."""
        forms = self.gen.generate("rex", pos="N")
        assert all(f.upos == "NOUN" for f in forms)

    # -- Pos filter --

    def test_pos_filter_excludes_other_pos(self):
        """pos='N' should not include verb entries for the same lemma."""
        # 'bellum' may also have adjective entries
        forms = self.gen.generate("bellum", pos="N")
        assert all(f.upos == "NOUN" for f in forms)

    def test_form_count_sanity(self):
        """A regular noun should produce a reasonable number of forms."""
        forms = self.gen.generate("rex", pos="N")
        # At least 6 case forms × 2 numbers = 12, likely more with archaic
        assert len(forms) >= 10


@skip_no_data
class TestGenerateAdj:
    """Generator produces correct adjective paradigm forms."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from latincy_lexicon.generator import Generator
        self.gen = Generator.from_json(ANALYZER_JSON)

    # -- 1st/2nd declension: bonus (ADJ 1.1) --

    def test_bonus_nom_s_m(self):
        """bonus NOM.S.M (ADJ 1.1, stem1='bon')."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert _find_form(
            forms, "bonus",
            Case="Nom", Number="Sing", Gender="Masc", Degree="Pos",
        )

    def test_bonus_nom_s_f(self):
        """bona NOM.S.F."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert _find_form(
            forms, "bona",
            Case="Nom", Number="Sing", Gender="Fem", Degree="Pos",
        )

    def test_bonus_nom_s_n(self):
        """bonum NOM.S.N."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert _find_form(
            forms, "bonum",
            Case="Nom", Number="Sing", Gender="Neut", Degree="Pos",
        )

    def test_bonus_gen_s_m(self):
        """boni GEN.S.M."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert _find_form(
            forms, "boni",
            Case="Gen", Number="Sing", Gender="Masc", Degree="Pos",
        )

    def test_bonus_acc_s_m(self):
        """bonum ACC.S.M."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert _find_form(
            forms, "bonum",
            Case="Acc", Number="Sing", Gender="Masc", Degree="Pos",
        )

    def test_bonus_voc_s_m(self):
        """bone VOC.S.M (distinct form for -us adjectives)."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert _find_form(
            forms, "bone",
            Case="Voc", Number="Sing", Gender="Masc", Degree="Pos",
        )

    def test_bonus_nom_p_m(self):
        """boni NOM.P.M."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert _find_form(
            forms, "boni",
            Case="Nom", Number="Plur", Gender="Masc", Degree="Pos",
        )

    def test_bonus_nom_p_n(self):
        """bona NOM.P.N (neuter plural -a)."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert _find_form(
            forms, "bona",
            Case="Nom", Number="Plur", Gender="Neut", Degree="Pos",
        )

    def test_bonus_upos(self):
        """1st/2nd decl adjective → UPOS = ADJ."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert all(f.upos == "ADJ" for f in forms)

    # -- Comparative and superlative (bonus → melior, optimus) --

    def test_bonus_comparative_nom_s(self):
        """melior NOM.S comparative (stem3='meli', ADJ 0.0 comp rules)."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert _find_form(
            forms, "melior",
            Case="Nom", Number="Sing", Degree="Cmp",
        )

    def test_bonus_superlative_nom_s_m(self):
        """optimus NOM.S.M superlative (stem4='opti', ADJ 0.0 sup rules)."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert _find_form(
            forms, "optimus",
            Case="Nom", Number="Sing", Gender="Masc", Degree="Sup",
        )

    # -- 3rd declension: ingens (ADJ 3.1) --

    def test_ingens_nom_s(self):
        """ingens NOM.S (ADJ 3.1, stem1='ingens')."""
        forms = self.gen.generate("ingens", pos="ADJ")
        assert _find_form(
            forms, "ingens",
            Case="Nom", Number="Sing", Degree="Pos",
        )

    def test_ingens_gen_s(self):
        """ingentis GEN.S (stem2='ingent')."""
        forms = self.gen.generate("ingens", pos="ADJ")
        assert _find_form(
            forms, "ingentis",
            Case="Gen", Number="Sing", Degree="Pos",
        )

    def test_ingens_acc_s(self):
        """ingentem ACC.S (common gender form)."""
        forms = self.gen.generate("ingens", pos="ADJ")
        assert _find_form(forms, "ingentem", Case="Acc", Number="Sing")

    def test_ingens_abl_s(self):
        """ingenti ABL.S."""
        forms = self.gen.generate("ingens", pos="ADJ")
        assert _find_form(forms, "ingenti", Case="Abl", Number="Sing")

    def test_ingens_nom_p(self):
        """ingentes NOM.P."""
        forms = self.gen.generate("ingens", pos="ADJ")
        assert _find_form(forms, "ingentes", Case="Nom", Number="Plur")

    # -- Pos filter --

    def test_pos_filter(self):
        """pos='ADJ' excludes non-adjective entries."""
        forms = self.gen.generate("bonus", pos="ADJ")
        assert all(f.upos == "ADJ" for f in forms)

    def test_form_count_sanity(self):
        """A regular 1/2 decl adjective should produce many forms (3 genders × cases × degrees)."""
        forms = self.gen.generate("bonus", pos="ADJ")
        # 3 genders × ~6 cases × 2 numbers × 3 degrees = ~108, minus dedup
        assert len(forms) >= 30


@skip_no_data
class TestGenerateUniques:
    """Generator includes unique/irregular forms from UNIQUES data."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from latincy_lexicon.generator import Generator
        self.gen = Generator.from_json(ANALYZER_JSON)

    def test_uniques_index_populated(self):
        """_uniques_index should be built and non-empty."""
        assert hasattr(self.gen, "_uniques_index")
        assert len(self.gen._uniques_index) > 0

    def test_absum_unique_forms_included(self):
        """absum (V 5.1) should include unique irregular forms like 'aforem'.

        ``aforem``, ``afores``, etc. are imperfect subjunctive forms of
        ``absum`` stored in UNIQUES. They share the ``af-`` prefix with
        absum's ``afu``/``afut`` stems (length 2), so the resolver attaches
        them to absum specifically — not to every V 5.1 verb.
        """
        forms = self.gen.generate("absum")
        surfaces = {f.form for f in forms}
        assert "aforem" in surfaces, f"absum missing UNIQUE 'aforem'"
        assert "afores" in surfaces, f"absum missing UNIQUE 'afores'"

    def test_unique_forms_have_feats(self):
        """Unique forms should have UD feature strings, not empty."""
        forms = self.gen.generate("absum")
        unique_surfaces = {"aforem", "afores", "aforet", "aforemus", "aforetis",
                           "aforent", "afore"}
        unique_forms = [f for f in forms if f.form in unique_surfaces]
        assert unique_forms, "Expected at least one unique form to be present"
        for f in unique_forms:
            assert f.feats, f"Unique form '{f.form}' has empty feats"

    def test_uniques_deduplicated(self):
        """Unique forms should be deduplicated with entry-generated forms."""
        forms = self.gen.generate("sum")
        keys = [(f.form, f.feats) for f in forms]
        assert len(keys) == len(set(keys)), "Duplicate (form, feats) pairs found"

    # -- UNIQUES contamination regression tests --
    # These guard against the bug where every UNIQUE form in a class was
    # attached to every lemma in that class, producing nonsense like
    # ``bobus → rex`` (bobus is an irregular form of bos, not rex).

    def test_rex_excludes_unrelated_uniques(self):
        """rex paradigm must NOT contain bos/rus uniques."""
        forms = self.gen.generate("rex", pos="N")
        surfaces = {f.form for f in forms}
        assert "bobus" not in surfaces
        assert "boum" not in surfaces
        assert "rusi" not in surfaces

    def test_bos_keeps_own_uniques(self):
        """bos paradigm must still contain its own UNIQUE forms."""
        forms = self.gen.generate("bos", pos="N")
        surfaces = {f.form for f in forms}
        assert "bobus" in surfaces, "bos should retain its irregular bobus"
        assert "boum" in surfaces, "bos should retain its irregular boum"

    def test_volo_keeps_irregular_present(self):
        """volo must contain vis/vult/vultis (irregular present indicative)."""
        forms = self.gen.generate("volo", pos="V")
        surfaces = {f.form for f in forms}
        assert "vis" in surfaces, "volo missing 2sg present 'vis'"
        assert "vult" in surfaces, "volo missing 3sg present 'vult'"
        assert "vultis" in surfaces, "volo missing 2pl present 'vultis'"

    def test_malo_excludes_volo_forms(self):
        """malo must contain mavis/mavult, NOT vis/vult."""
        forms = self.gen.generate("malo", pos="V")
        surfaces = {f.form for f in forms}
        assert "mavis" in surfaces
        assert "mavult" in surfaces
        assert "vis" not in surfaces, "vis is volo's form, not malo's"
        assert "vult" not in surfaces, "vult is volo's form, not malo's"

    def test_nolo_excludes_volo_forms(self):
        """nolo must not contain vis/vult."""
        forms = self.gen.generate("nolo", pos="V")
        surfaces = {f.form for f in forms}
        assert "vis" not in surfaces
        assert "vult" not in surfaces

    def test_lookup_dict_no_cross_contamination(self):
        """to_lookup_dict for rex must not pull in bos/rus forms."""
        result = self.gen.to_lookup_dict(["rex"])
        assert "bobus" not in result
        assert "boum" not in result
        assert "rusi" not in result


@skip_no_data
class TestLocativeFilter:
    """Locative case is suppressed except for place names and known common nouns."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from latincy_lexicon.generator import Generator
        self.gen = Generator.from_json(ANALYZER_JSON)

    def test_rex_no_locative(self):
        """rex (common noun, noun_kind=T) must not produce Loc forms."""
        forms = self.gen.generate("rex", pos="N")
        loc = [f for f in forms if "Case=Loc" in f.feats]
        assert not loc, f"Unexpected locative forms for rex: {[f.form for f in loc]}"

    def test_puella_no_locative(self):
        """puella (common noun) must not produce Loc forms."""
        forms = self.gen.generate("puella", pos="N")
        loc = [f for f in forms if "Case=Loc" in f.feats]
        assert not loc

    def test_bonus_adj_no_locative(self):
        """Adjectives never produce Loc forms."""
        forms = self.gen.generate("bonus", pos="ADJ")
        loc = [f for f in forms if "Case=Loc" in f.feats]
        assert not loc

    def test_roma_keeps_locative(self):
        """Roma (proper place name, noun_kind=L) must produce Romae locative."""
        forms = self.gen.generate("Roma", pos="N")
        loc_singulars = [
            f for f in forms
            if "Case=Loc" in f.feats and "Number=Sing" in f.feats
        ]
        assert any(f.form == "Romae" for f in loc_singulars), (
            f"Expected Romae locative singular; got {[f.form for f in loc_singulars]}"
        )

    def test_domus_keeps_locative(self):
        """domus (noun_kind=W) must produce domi locative."""
        forms = self.gen.generate("domus", pos="N")
        assert any(
            f.form == "domi" and "Case=Loc" in f.feats and "Number=Sing" in f.feats
            for f in forms
        ), "Expected domi locative singular for domus"

    def test_humus_keeps_locative(self):
        """humus (allowlisted common noun) must produce humi locative."""
        forms = self.gen.generate("humus", pos="N")
        assert any(
            f.form == "humi" and "Case=Loc" in f.feats and "Number=Sing" in f.feats
            for f in forms
        ), "Expected humi locative singular for humus"


@skip_no_data
class TestNounParadigmCleanup:
    """Pedagogical paradigm cleanup: age + smart freq filters."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from latincy_lexicon.generator import Generator
        self.gen = Generator.from_json(ANALYZER_JSON)

    def test_rex_no_redundant_alt_forms(self):
        """rex (consonant-stem 3rd decl) must not have i-stem alt forms.

        ``regium`` (gen pl alt to ``regum``) is freq=B in WW data — a
        redundant alternate to the standard freq=A form. The smart freq
        filter drops it.
        """
        forms = self.gen.generate("rex", pos="N")
        surfaces = {f.form for f in forms}
        assert "regum" in surfaces, "rex must have standard regum gen pl"
        assert "regium" not in surfaces, "regium is i-stem alt that shouldn't appear for rex"

    def test_rex_no_archaic_dat_singular(self):
        """rex must not have rege as dative singular (early Latin variant).

        ``rege`` is the ablative singular; the early-Latin ``rege`` dative
        is age='B' freq='B' in WW data and would mislead readers into
        thinking the dative is rege rather than regi.
        """
        forms = self.gen.generate("rex", pos="N")
        rege_dats = [
            f for f in forms
            if f.form == "rege" and "Case=Dat" in f.feats
        ]
        assert not rege_dats, (
            f"Expected no Dat=rege; got {[f.feats for f in rege_dats]}"
        )

    def test_rex_keeps_standard_forms(self):
        """rex must keep all standard 3rd-decl masculine forms."""
        forms = self.gen.generate("rex", pos="N")
        surfaces = {f.form for f in forms}
        for expected in ("rex", "regis", "regi", "regem", "rege",
                         "reges", "regum", "regibus"):
            assert expected in surfaces, f"rex missing standard form {expected!r}"

    def test_civis_keeps_istem_genitive_plural(self):
        """civis (i-stem 3rd decl) must have civium as standard gen pl."""
        forms = self.gen.generate("civis", pos="N")
        gen_pl = [
            f for f in forms
            if "Case=Gen" in f.feats and "Number=Plur" in f.feats
        ]
        surfaces = {f.form for f in gen_pl}
        assert "civium" in surfaces, (
            f"civis must have standard civium gen pl; got {surfaces}"
        )


@skip_no_data
class TestParadigmSort:
    """Pedagogical sort='paradigm' produces traditional Latin reading order."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from latincy_lexicon.generator import Generator
        self.gen = Generator.from_json(ANALYZER_JSON)

    def test_invalid_sort_raises(self):
        with pytest.raises(ValueError, match="sort must be"):
            self.gen.generate("amo", sort="bogus")

    def test_default_sort_is_ud(self):
        """Default sort='ud' preserves insertion order — no behavior change."""
        a = self.gen.generate("amo")
        b = self.gen.generate("amo", sort="ud")
        assert [(f.form, f.feats) for f in a] == [(f.form, f.feats) for f in b]

    def test_amo_present_indicative_pedagogical(self):
        """Pres ind active reads 1sg, 2sg, 3sg, 1pl, 2pl, 3pl."""
        forms = self.gen.generate("amo", sort="paradigm")
        present = [
            f for f in forms
            if all(x in f.feats for x in (
                "Mood=Ind", "Tense=Pres", "Voice=Act", "VerbForm=Fin",
            ))
        ]
        surfaces = [f.form for f in present]
        assert surfaces == ["amo", "amas", "amat", "amamus", "amatis", "amant"], (
            f"Got {surfaces}"
        )

    def test_amo_imperfect_before_future(self):
        """Imperfect tense forms come before future forms."""
        forms = self.gen.generate("amo", sort="paradigm")
        impf_idx = next(
            i for i, f in enumerate(forms)
            if f.form == "amabam" and "Tense=Imp" in f.feats
        )
        fut_idx = next(
            i for i, f in enumerate(forms)
            if f.form == "amabo" and "Tense=Fut" in f.feats
        )
        assert impf_idx < fut_idx

    def test_bonus_pos_masc_paradigm(self):
        """Positive masculine bonus reads nom→gen→dat→acc→abl→voc, sing→plur."""
        forms = self.gen.generate("bonus", pos="ADJ", sort="paradigm")
        masc_pos_sing = [
            f for f in forms
            if "Degree=Pos" in f.feats and "Gender=Masc" in f.feats
            and "Number=Sing" in f.feats
        ]
        surfaces = [f.form for f in masc_pos_sing]
        # Expected sequence (allowing duplicates from rule cascades)
        expected = ["bonus", "boni", "bono", "bonum", "bono", "bone"]
        assert surfaces == expected, f"Got {surfaces}, expected {expected}"


@skip_no_data
class TestLookupDict:
    """Generator.to_lookup_dict() export."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from latincy_lexicon.generator import Generator
        self.gen = Generator.from_json(ANALYZER_JSON)

    def test_single_lemma(self):
        """to_lookup_dict for a single noun returns form→lemma mapping."""
        result = self.gen.to_lookup_dict(["rex"], pos="N")
        assert isinstance(result, dict)
        assert result.get("rex") == "rex"
        assert result.get("regis") == "rex"
        assert result.get("regem") == "rex"
        assert result.get("regibus") == "rex"

    def test_batch_first_lemma_wins(self):
        """When two lemmas produce the same form, the first lemma wins."""
        result = self.gen.to_lookup_dict(["rex", "puella"], pos="N")
        # Both should be present
        assert result.get("rex") == "rex"
        assert result.get("puella") == "puella"
        assert result.get("regis") == "rex"
        assert result.get("puellae") == "puella"


# ---------------------------------------------------------------------------
# spaCy paradigm_generator component
# ---------------------------------------------------------------------------


@skip_no_data
class TestSpacyComponent:
    """Tests for the paradigm_generator spaCy pipeline component."""

    @pytest.fixture(autouse=True)
    def setup(self):
        import spacy
        self.nlp = spacy.blank("la")
        self.nlp.add_pipe(
            "paradigm_generator",
            config={"analyzer_path": str(ANALYZER_JSON)},
        )

    def test_paradigm_extension_exists(self):
        from spacy.tokens import Token
        assert Token.has_extension("paradigm")
        assert Token.has_extension("reinflect")

    def test_paradigm_returns_forms(self):
        doc = self.nlp.make_doc("amat")
        doc[0].lemma_ = "amo"
        doc[0].pos_ = "VERB"
        doc = self.nlp.get_pipe("paradigm_generator")(doc)
        paradigm = doc[0]._.paradigm
        assert paradigm is not None
        assert len(paradigm) > 0
        form_strs = [f["form"] for f in paradigm]
        assert "amo" in form_strs
        assert "amat" in form_strs

    def test_reinflect_number(self):
        from spacy.tokens import MorphAnalysis
        doc = self.nlp.make_doc("amat")
        doc[0].lemma_ = "amo"
        doc[0].pos_ = "VERB"
        doc[0].morph = MorphAnalysis(
            self.nlp.vocab,
            {
                "Aspect": "Imp", "Mood": "Ind", "Number": "Sing",
                "Person": "3", "Tense": "Pres", "VerbForm": "Fin",
                "Voice": "Act",
            },
        )
        doc = self.nlp.get_pipe("paradigm_generator")(doc)
        result = doc[0]._.reinflect(Number="Plur")
        assert result == "amant"

    def test_reinflect_tense(self):
        from spacy.tokens import MorphAnalysis
        doc = self.nlp.make_doc("amat")
        doc[0].lemma_ = "amo"
        doc[0].pos_ = "VERB"
        doc[0].morph = MorphAnalysis(
            self.nlp.vocab,
            {
                "Aspect": "Imp", "Mood": "Ind", "Number": "Sing",
                "Person": "3", "Tense": "Pres", "VerbForm": "Fin",
                "Voice": "Act",
            },
        )
        doc = self.nlp.get_pipe("paradigm_generator")(doc)
        result = doc[0]._.reinflect(Tense="Imp", Aspect="Imp")
        assert result == "amabat"

    def test_unknown_lemma_returns_none(self):
        doc = self.nlp.make_doc("xyzzy")
        doc[0].lemma_ = "xyzzyplugh"
        doc = self.nlp.get_pipe("paradigm_generator")(doc)
        assert doc[0]._.paradigm is None

    def test_reinflect_no_match_returns_none(self):
        from spacy.tokens import MorphAnalysis
        doc = self.nlp.make_doc("amat")
        doc[0].lemma_ = "amo"
        doc[0].pos_ = "VERB"
        doc[0].morph = MorphAnalysis(
            self.nlp.vocab,
            {
                "Mood": "Ind", "Number": "Sing", "Person": "3",
                "Tense": "Pres", "VerbForm": "Fin", "Voice": "Act",
            },
        )
        doc = self.nlp.get_pipe("paradigm_generator")(doc)
        result = doc[0]._.reinflect(Person="4")
        assert result is None

    def test_paradigm_cached_by_lemma(self):
        doc = self.nlp.make_doc("amo amas")
        doc[0].lemma_ = "amo"
        doc[1].lemma_ = "amo"
        doc = self.nlp.get_pipe("paradigm_generator")(doc)
        assert doc[0]._.paradigm is doc[1]._.paradigm
