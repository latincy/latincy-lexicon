"""Cross-validation tests: Generator output vs. known-correct Latin paradigms.

Each test verifies that the Generator produces a SUPERSET of hand-tabulated
forms for a given lemma. We use ``assert expected <= forms`` (set subset)
so that extra generated forms (archaic variants, alternate endings) do not
cause failures.

NOTE: The Generator outputs raw stems from DICTLINE concatenated with endings.
Stems use 'v' (not 'u'), e.g. "amavi" not "amaui". The normalize_latin()
function converts v->u, but the Generator does NOT normalize its output.
"""

import pytest
from pathlib import Path


ANALYZER_JSON = Path(__file__).parent.parent / "data" / "json" / "analyzer.json"

skip_no_data = pytest.mark.skipif(
    not ANALYZER_JSON.exists(),
    reason="analyzer.json not available (run: latincy-lexicon build)",
)


@skip_no_data
class TestCrossValidation:
    """Cross-validate Generator output against known Latin paradigms."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from latincy_lexicon.generator import Generator
        self.gen = Generator.from_json(ANALYZER_JSON)

    def _form_strs(self, lemma, pos):
        """Return the set of all surface forms generated for lemma+pos."""
        return {f.form for f in self.gen.generate(lemma, pos=pos)}

    # ==================================================================
    # amo (V 1.1) — Regular 1st conjugation
    # ==================================================================

    def test_amo_present_active(self):
        """Present indicative active: amo, amas, amat, amamus, amatis, amant."""
        expected = {"amo", "amas", "amat", "amamus", "amatis", "amant"}
        forms = self._form_strs("amo", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_amo_imperfect_active(self):
        """Imperfect indicative active: amabam, amabas, amabat, ..."""
        expected = {"amabam", "amabas", "amabat", "amabamus", "amabatis", "amabant"}
        forms = self._form_strs("amo", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_amo_future_active(self):
        """Future indicative active: amabo, amabis, amabit, ..."""
        expected = {"amabo", "amabis", "amabit", "amabimus", "amabitis", "amabunt"}
        forms = self._form_strs("amo", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_amo_perfect_active(self):
        """Perfect indicative active: amavi, amavisti, amavit, ..."""
        expected = {"amavi", "amavisti", "amavit", "amavimus", "amavistis", "amaverunt"}
        forms = self._form_strs("amo", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_amo_present_subjunctive(self):
        """Present subjunctive active: amem, ames, amet, ..."""
        expected = {"amem", "ames", "amet", "amemus", "ametis", "ament"}
        forms = self._form_strs("amo", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_amo_passive_present(self):
        """Present indicative passive: amor, amaris, amatur, ..."""
        expected = {"amor", "amaris", "amatur", "amamur", "amamini", "amantur"}
        forms = self._form_strs("amo", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_amo_participles(self):
        """Participles: amans (pres act), amatus (PPP), amaturus (fut act)."""
        expected = {"amans", "amatus", "amaturus"}
        forms = self._form_strs("amo", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_amo_infinitives(self):
        """Infinitives: amare (pres act), amavisse (perf act)."""
        expected = {"amare", "amavisse"}
        forms = self._form_strs("amo", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_amo_imperative(self):
        """Imperative: ama (2s), amate (2p)."""
        expected = {"ama", "amate"}
        forms = self._form_strs("amo", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    # ==================================================================
    # sum (V 5.1) — Irregular "to be"
    # ==================================================================

    def test_sum_present(self):
        """Present indicative: sum, es, est, sumus, estis, sunt."""
        expected = {"sum", "es", "est", "sumus", "estis", "sunt"}
        forms = self._form_strs("sum", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_sum_imperfect(self):
        """Imperfect indicative: eram, eras, erat, eramus, eratis, erant."""
        expected = {"eram", "eras", "erat", "eramus", "eratis", "erant"}
        forms = self._form_strs("sum", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_sum_future(self):
        """Future indicative: ero, eris, erit, erimus, eritis, erunt."""
        expected = {"ero", "eris", "erit", "erimus", "eritis", "erunt"}
        forms = self._form_strs("sum", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_sum_perfect(self):
        """Perfect indicative: fui, fuisti, fuit, fuimus, fuistis, fuerunt."""
        expected = {"fui", "fuisti", "fuit", "fuimus", "fuistis", "fuerunt"}
        forms = self._form_strs("sum", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_sum_present_subjunctive(self):
        """Present subjunctive: sim, sis, sit, simus, sitis, sint."""
        expected = {"sim", "sis", "sit", "simus", "sitis", "sint"}
        forms = self._form_strs("sum", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_sum_infinitive(self):
        """Infinitive: esse."""
        expected = {"esse"}
        forms = self._form_strs("sum", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_sum_imperfect_subjunctive(self):
        """Imperfect subjunctive: essem, esses, esset, ..."""
        expected = {"essem", "esses", "esset", "essemus", "essetis", "essent"}
        forms = self._form_strs("sum", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_sum_future_perfect(self):
        """Future perfect: fuero, fueris, fuerit, ..."""
        expected = {"fuero", "fueris", "fuerit", "fuerimus", "fueritis", "fuerint"}
        forms = self._form_strs("sum", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    # ==================================================================
    # fero (V 3.2) — Irregular with suppletive stems
    # ==================================================================

    def test_fero_present(self):
        """Present indicative: fero, fers, fert, ferimus, fertis, ferunt."""
        expected = {"fero", "fers", "fert", "ferimus", "fertis", "ferunt"}
        forms = self._form_strs("fero", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_fero_perfect(self):
        """Perfect (suppletive stem3=tul): tuli, tulisti, tulit."""
        expected = {"tuli", "tulisti", "tulit"}
        forms = self._form_strs("fero", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_fero_ppp(self):
        """PPP (suppletive stem4=lat): latus."""
        expected = {"latus"}
        forms = self._form_strs("fero", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_fero_infinitive(self):
        """Infinitive: ferre."""
        expected = {"ferre"}
        forms = self._form_strs("fero", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_fero_passive_present(self):
        """Present passive: feror, ferris, fertur."""
        expected = {"feror", "ferris", "fertur"}
        forms = self._form_strs("fero", "V")
        assert expected <= forms, f"Missing: {expected - forms}"

    # ==================================================================
    # rex (N 3.1) — 3rd declension masculine
    # ==================================================================

    def test_rex_singular(self):
        """Singular: rex, regis, regi, regem, rege."""
        expected = {"rex", "regis", "regi", "regem", "rege"}
        forms = self._form_strs("rex", "N")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_rex_plural(self):
        """Plural: reges, regum, regibus."""
        expected = {"reges", "regum", "regibus"}
        forms = self._form_strs("rex", "N")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_rex_full_paradigm(self):
        """Full paradigm superset check (all 10 standard case-number forms)."""
        expected = {
            "rex", "regis", "regi", "regem", "rege",       # singular
            "reges", "regum", "regibus", "reges", "regibus" # plural (dat=abl)
        }
        forms = self._form_strs("rex", "N")
        assert expected <= forms, f"Missing: {expected - forms}"

    # ==================================================================
    # puella (N 1.1) — 1st declension feminine
    # ==================================================================

    def test_puella_singular(self):
        """Singular: puella, puellae, puellam."""
        expected = {"puella", "puellae", "puellam"}
        forms = self._form_strs("puella", "N")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_puella_plural(self):
        """Plural: puellae, puellarum, puellis, puellas."""
        expected = {"puellae", "puellarum", "puellis", "puellas"}
        forms = self._form_strs("puella", "N")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_puella_ablative(self):
        """Ablative singular: puella."""
        expected = {"puella"}
        forms = self._form_strs("puella", "N")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_puella_dative_singular(self):
        """Dative singular: puellae."""
        expected = {"puellae"}
        forms = self._form_strs("puella", "N")
        assert expected <= forms, f"Missing: {expected - forms}"

    # ==================================================================
    # bonus (ADJ 1.1) — 1st/2nd declension adjective
    # ==================================================================

    def test_bonus_masculine(self):
        """Masculine: bonus, boni, bono, bonum."""
        expected = {"bonus", "boni", "bono", "bonum"}
        forms = self._form_strs("bonus", "ADJ")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_bonus_feminine(self):
        """Feminine: bona, bonae, bonam."""
        expected = {"bona", "bonae", "bonam"}
        forms = self._form_strs("bonus", "ADJ")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_bonus_neuter(self):
        """Neuter: bonum, boni, bono, bona (nom/acc plural)."""
        expected = {"bonum", "boni", "bono", "bona"}
        forms = self._form_strs("bonus", "ADJ")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_bonus_vocative(self):
        """Vocative masculine singular: bone."""
        expected = {"bone"}
        forms = self._form_strs("bonus", "ADJ")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_bonus_comparative(self):
        """Comparative forms: melior (irregular stem3)."""
        expected = {"melior"}
        forms = self._form_strs("bonus", "ADJ")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_bonus_superlative(self):
        """Superlative forms: optimus (irregular stem4)."""
        expected = {"optimus"}
        forms = self._form_strs("bonus", "ADJ")
        assert expected <= forms, f"Missing: {expected - forms}"

    def test_bonus_feminine_plural(self):
        """Feminine plural: bonae (nom), bonas (acc), bonis (dat/abl), bonarum (gen)."""
        expected = {"bonae", "bonas", "bonis", "bonarum"}
        forms = self._form_strs("bonus", "ADJ")
        assert expected <= forms, f"Missing: {expected - forms}"

    # ==================================================================
    # Sanity checks: form counts
    # ==================================================================

    def test_amo_form_count(self):
        """amo (V 1.1) should produce a large number of forms (all tenses, moods, voices)."""
        forms = self._form_strs("amo", "V")
        # Regular verb: ~6 tenses × 6 persons × 2 voices + participles + infinitives
        assert len(forms) >= 80, f"Only {len(forms)} unique forms for amo"

    def test_sum_form_count(self):
        """sum (V 5.1) should produce many forms (active only, no passive)."""
        forms = self._form_strs("sum", "V")
        assert len(forms) >= 40, f"Only {len(forms)} unique forms for sum"

    def test_rex_form_count(self):
        """rex (N 3.1) should produce its core 3rd-decl surface forms.

        Note: 3rd-decl noun paradigms collapse to ~9 unique surfaces because
        case/number combinations like dat/abl/loc plural all share ``regibus``.
        """
        forms = self._form_strs("rex", "N")
        expected = {"rex", "regis", "regem", "rege", "reges", "regum", "regibus"}
        missing = expected - forms
        assert not missing, f"rex missing core forms: {missing}"

    def test_bonus_form_count(self):
        """bonus (ADJ 1.1) should produce many forms (3 genders × cases × degrees)."""
        forms = self._form_strs("bonus", "ADJ")
        assert len(forms) >= 30, f"Only {len(forms)} unique forms for bonus"

    # ==================================================================
    # No spurious empty forms
    # ==================================================================

    def test_no_empty_forms(self):
        """No generated form should be the empty string."""
        for lemma, pos in [("amo", "V"), ("sum", "V"), ("fero", "V"),
                           ("rex", "N"), ("puella", "N"), ("bonus", "ADJ")]:
            forms = self._form_strs(lemma, pos)
            assert "" not in forms, f"Empty form generated for {lemma} ({pos})"
