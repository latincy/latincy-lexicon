from latincy_lexicon import format_principal_parts, pronominal_citation


def test_pronominal_citation_by_lemma():
    assert pronominal_citation("hic") == "hic, haec, hoc"
    assert pronominal_citation("ille") == "ille, illa, illud"
    assert pronominal_citation("Qui") == "qui, quae, quod"  # case-insensitive
    assert pronominal_citation("amo") is None
    assert pronominal_citation(None) is None

# ---------- verbs ----------


def test_verb_scribo_3rd_conj_full_four_parts():
    entry = {
        "pos": "V",
        "headword": "scribo",
        "principal_parts": ["scrib", "scrib", "scrips", "script"],
    }
    assert format_principal_parts(entry) == "scribo, scribere, scripsi, scriptum"


def test_verb_amo_1st_conj_detected_via_perfect_suffix():
    entry = {
        "pos": "V",
        "headword": "amo",
        "principal_parts": ["am", "am", "amav", "amat"],
    }
    assert format_principal_parts(entry) == "amo, amare, amavi, amatum"


def test_verb_moneo_2nd_conj_from_eo_ending():
    entry = {
        "pos": "V",
        "headword": "moneo",
        "principal_parts": ["mon", "mon", "monu", "monit"],
    }
    assert format_principal_parts(entry) == "moneo, monere, monui, monitum"


def test_verb_audio_4th_conj_from_io_ending():
    entry = {
        "pos": "V",
        "headword": "audio",
        "principal_parts": ["audi", "aud", "audiv", "audit"],
    }
    assert format_principal_parts(entry) == "audio, audire, audivi, auditum"


def test_verb_lego_3rd_conj_no_perfect_suffix():
    entry = {
        "pos": "V",
        "headword": "lego",
        "principal_parts": ["leg", "leg", "leg", "lect"],
    }
    # Perfect stem == present stem → "legi" (not "legii")
    assert format_principal_parts(entry) == "lego, legere, legi, lectum"


def test_verb_missing_supine_gives_three_parts():
    entry = {
        "pos": "V",
        "headword": "capio",
        "principal_parts": ["capi", "cap", "caps"],
    }
    result = format_principal_parts(entry)
    # Either 3-part reconstruction or graceful partial
    assert result is not None
    assert "capio" in result
    assert result.count(",") == 2  # three parts


def test_verb_amo_whitaker_syncopated_perfect_reconstructed_to_standard():
    """Whitaker stores amo's perfect stem as the syncopated 'amass' and
    has no supine. Reconstruct the standard classical 4 parts.
    """
    entry = {
        "pos": "V",
        "headword": "amo",
        "principal_parts": ["am", "am", "amass"],
    }
    assert format_principal_parts(entry) == "amo, amare, amavi, amatum"


def test_verb_first_conj_synthesizes_supine_when_missing():
    """1st conj with perfect in -av but no supine → regular -atum supine."""
    entry = {
        "pos": "V",
        "headword": "porto",
        "principal_parts": ["port", "port", "portav"],
    }
    assert format_principal_parts(entry) == "porto, portare, portavi, portatum"


def test_verb_no_stems_returns_none():
    entry = {"pos": "V", "headword": "foo", "principal_parts": []}
    assert format_principal_parts(entry) is None


# ---------- verbs: conjugation from Whitaker (decl_which, decl_var) ----------
# Production entries now carry decl_which/decl_var; the infinitive is built from
# stem2 + ending, so 3rd-io verbs (capio→capere) stop being mis-classed as 4th.


def _v(hw, stems, which, var, **kw):
    return {"pos": "V", "headword": hw, "principal_parts": stems,
            "decl_which": which, "decl_var": var, **kw}


def test_verb_capio_3rd_io_infinitive_ere_not_ire():
    # (8,3) = 3rd-io; infinitive must be capere, not capire.
    assert format_principal_parts(_v("capio", ["capi", "cap", "cep", "capt"], 8, 3)) \
        == "capio, capere, cepi, captum"


def test_verb_facio_3rd_io():
    assert format_principal_parts(_v("facio", ["faci", "fac", "fec", "fact"], 8, 3)) \
        == "facio, facere, feci, factum"


def test_verb_fugio_3rd_io_coded_3_1():
    assert format_principal_parts(_v("fugio", ["fugi", "fug", "fug", "fugit"], 3, 1)) \
        == "fugio, fugere, fugi, fugitum"


def test_verb_audio_true_4th_coded_3_4():
    assert format_principal_parts(_v("audio", ["audi", "aud", "audiv", "audit"], 3, 4)) \
        == "audio, audire, audivi, auditum"


def test_verb_rego_3rd_with_codes():
    assert format_principal_parts(_v("rego", ["reg", "reg", "rex", "rect"], 3, 1)) \
        == "rego, regere, rexi, rectum"


def test_verb_amo_1st_coded_8_1():
    assert format_principal_parts(_v("amo", ["am", "am", "amav", "amat"], 8, 1)) \
        == "amo, amare, amavi, amatum"


# irregulars (closed set)


def test_verb_sum():
    assert format_principal_parts(_v("sum", ["s", "fu", "fut"], 5, 1, verb_kind="TO_BE")) \
        == "sum, esse, fui"


def test_verb_possum():
    assert format_principal_parts(_v("possum", ["poss", "pot", "potu"], 5, 2, verb_kind="TO_BEING")) \
        == "possum, posse, potui"


def test_verb_absum_esse_compound():
    assert format_principal_parts(_v("absum", ["abs", "ab", "afu"], 5, 1, verb_kind="TO_BEING")) \
        == "absum, abesse, afui"


def test_verb_fero_irregular_infinitive_ferre():
    assert format_principal_parts(_v("fero", ["fer", "fer", "tul", "lat"], 3, 2)) \
        == "fero, ferre, tuli, latum"


def test_verb_confero_fero_compound():
    assert format_principal_parts(_v("confero", ["confer", "confer", "contul", "collat"], 3, 2)) \
        == "confero, conferre, contuli, collatum"


def test_verb_eo_irregular_ire():
    # eo's own entry is miscoded; hardcoded citation.
    assert format_principal_parts(_v("eo", ["e", "e", "ev", "et"], 1, 1)) \
        == "eo, ire, ii, itum"


def test_verb_abeo_eo_compound_6_1():
    assert format_principal_parts(_v("abeo", ["ab", "abi", "abi", "abit"], 6, 1)) \
        == "abeo, abire, abii, abitum"


def test_verb_redeo_eo_compound():
    assert format_principal_parts(_v("redeo", ["rede", "redi", "redi", "redit"], 6, 1)) \
        == "redeo, redire, redii, reditum"


def test_verb_volo_velle():
    assert format_principal_parts(_v("volo", ["vol", "vel", "volu"], 6, 2)) \
        == "volo, velle, volui"


def test_verb_nolo_nolle():
    assert format_principal_parts(_v("nolo", ["nol", "nol", "nolu"], 6, 2)) \
        == "nolo, nolle, nolui"


def test_verb_fio_semidep_irregular():
    assert format_principal_parts(_v("fio", ["fi", "f", "fact"], 3, 3, verb_kind="SEMIDEP")) \
        == "fio, fieri, factus sum"


# deponents & semi-deponents


def test_verb_hortor_deponent_1st():
    assert format_principal_parts(_v("hortor", ["hort", "hort", "hortat"], 1, 1, verb_kind="DEP")) \
        == "hortor, hortari, hortatus sum"


def test_verb_sequor_deponent_3rd():
    assert format_principal_parts(_v("sequor", ["sequ", "sequ", "secut"], 3, 1, verb_kind="DEP")) \
        == "sequor, sequi, secutus sum"


def test_verb_patior_deponent_3rd_io():
    assert format_principal_parts(_v("patior", ["pati", "pat", "pass"], 3, 1, verb_kind="DEP")) \
        == "patior, pati, passus sum"


def test_verb_vereor_deponent_2nd():
    assert format_principal_parts(_v("vereor", ["ver", "ver", "verit"], 2, 1, verb_kind="DEP")) \
        == "vereor, vereri, veritus sum"


def test_verb_morior_deponent_irregular_participle():
    # Whitaker stem gives 'moritus'; the classical participle is mortuus.
    assert format_principal_parts(_v("morior", ["mori", "mor", "morit"], 3, 4, verb_kind="DEP")) \
        == "morior, mori, mortuus sum"


def test_verb_audeo_semideponent_2nd():
    assert format_principal_parts(_v("audeo", ["aud", "aud", "aus", "aus"], 2, 1, verb_kind="SEMIDEP")) \
        == "audeo, audere, ausus sum"


def test_verb_soleo_semideponent_2nd():
    assert format_principal_parts(_v("soleo", ["sol", "sol", "solit"], 2, 1, verb_kind="SEMIDEP")) \
        == "soleo, solere, solitus sum"


# ---------- defective verbs (Whitaker stem1 == 'zzz' placeholder) ----------
# These are perfect-system-only verbs: Whitaker has no present stem, so it
# parks the 'zzz' placeholder in stem1/stem2 and the real stems sit in 3/4.
# The lexicon flags them ``defective`` so the citation is the perfect 1sg +
# perfect infinitive (memini, meminisse), not a fabricated present.


def _dv(hw, stems, which, var, **kw):
    return {"pos": "V", "headword": hw, "principal_parts": stems,
            "decl_which": which, "decl_var": var, "defective": True, **kw}


def test_verb_odi_perfdef_perfect_only_citation():
    assert format_principal_parts(
        _dv("odi", ["od", "os"], 3, 1, verb_kind="PERFDEF")
    ) == "odi, odisse, osus sum"


def test_verb_memini_perfdef_two_parts_no_supine():
    assert format_principal_parts(
        _dv("memini", ["memin"], 2, 1, verb_kind="PERFDEF")
    ) == "memini, meminisse"


def test_verb_novi_perfdef():
    assert format_principal_parts(
        _dv("novi", ["nov", "not"], 3, 1, verb_kind="PERFDEF")
    ) == "novi, novisse, notus sum"


def test_verb_perodi_perfdef():
    assert format_principal_parts(
        _dv("perodi", ["perod", "peros"], 3, 1, verb_kind="PERFDEF")
    ) == "perodi, perodisse, perosus sum"


def test_verb_collibuit_impersonal_perfdef_no_supine():
    # Impersonals are cited as the 3sg perfect; no participle.
    assert format_principal_parts(
        _dv("collibuit", ["collibu", "collibit"], 2, 1, verb_kind="IMPERS")
    ) == "collibuit, collibuisse"


def test_verb_memordi_defective_without_verb_kind():
    # 'memord' is verb_kind X (dropped from the entry); the defective flag
    # alone must still route it to the perfect-only citation.
    assert format_principal_parts(
        _dv("memordi", ["memord"], 2, 1)
    ) == "memordi, memordisse"


def test_adj_deterior_comparative_only():
    assert format_principal_parts(
        {"pos": "ADJ", "headword": "deterior",
         "principal_parts": ["deteri", "deterri"],
         "decl_which": 1, "decl_var": 1, "defective": True}
    ) == "deterior, -ius"


def test_adj_ulterior_comparative_only():
    assert format_principal_parts(
        {"pos": "ADJ", "headword": "ulterior",
         "principal_parts": ["ulteri", "ulti"],
         "decl_which": 3, "decl_var": 1, "defective": True}
    ) == "ulterior, -ius"


# ---------- pronominals & numerals ----------


def test_pron_ille_three_gender():
    assert format_principal_parts(
        {"pos": "PRON", "headword": "ille", "principal_parts": ["ill", "ill"]}
    ) == "ille, illa, illud"


def test_pron_is_three_gender():
    assert format_principal_parts(
        {"pos": "PRON", "headword": "is", "principal_parts": ["i", "e"]}
    ) == "is, ea, id"


def test_pron_qui_relative():
    assert format_principal_parts(
        {"pos": "PRON", "headword": "qui", "principal_parts": ["qu", "cu"]}
    ) == "qui, quae, quod"


def test_pron_hic_table_wins_over_adv_homograph():
    # The top lexicon homograph for 'hic' is the adverb; the demonstrative
    # citation should still win by headword.
    assert format_principal_parts(
        {"pos": "ADV", "headword": "hic", "principal_parts": ["hic"]}
    ) == "hic, haec, hoc"


def test_pron_alius_irregular_neuter():
    # alius via the table, not the plain -a/-um adjective formatter (neuter -ud).
    assert format_principal_parts(
        {"pos": "ADJ", "headword": "alius", "principal_parts": ["ali", "ali"]}
    ) == "alius, alia, aliud"


def test_num_unus_shows_a_um():
    assert format_principal_parts(
        {"pos": "NUM", "headword": "unus", "principal_parts": ["un", "un"]}
    ) == "unus, -a, -um"


def test_adj_totus_pronominal_plain_a_um():
    assert format_principal_parts(
        {"pos": "ADJ", "headword": "totus", "principal_parts": ["tot", "tot"]}
    ) == "totus, -a, -um"


def test_pron_unknown_personal_returns_none():
    # ego is excluded from the vocab card anyway; no bogus citation.
    assert format_principal_parts(
        {"pos": "PRON", "headword": "ego", "principal_parts": ["eg", "me"]}
    ) is None


# ---------- nouns ----------


def test_noun_1st_decl_puella():
    entry = {
        "pos": "N",
        "headword": "puella",
        "principal_parts": ["puell", "puell"],
        "gender": "F",
        "decl_which": 1,
    }
    assert format_principal_parts(entry) == "puella, puellae, f."


def test_noun_2nd_decl_m_servus():
    entry = {
        "pos": "N",
        "headword": "servus",
        "principal_parts": ["serv", "serv"],
        "gender": "M",
        "decl_which": 2,
    }
    assert format_principal_parts(entry) == "servus, servi, m."


def test_noun_2nd_decl_n_bellum():
    entry = {
        "pos": "N",
        "headword": "bellum",
        "principal_parts": ["bell", "bell"],
        "gender": "N",
        "decl_which": 2,
    }
    assert format_principal_parts(entry) == "bellum, belli, n."


def test_noun_common_gender_shows_c():
    entry = {
        "pos": "N",
        "headword": "civis",
        "principal_parts": ["civis", "civ"],
        "gender": "C",
        "decl_which": 3,
    }
    assert format_principal_parts(entry) == "civis, civis, c."


def test_noun_3rd_decl_rex_uses_stem2():
    entry = {
        "pos": "N",
        "headword": "rex",
        "principal_parts": ["rex", "reg"],
        "gender": "M",
        "decl_which": 3,
    }
    assert format_principal_parts(entry) == "rex, regis, m."


def test_noun_puer_2nd_decl_in_er():
    entry = {
        "pos": "N",
        "headword": "puer",
        "principal_parts": ["puer", "puer"],
        "gender": "M",
        "decl_which": 2,
    }
    assert format_principal_parts(entry) == "puer, pueri, m."


def test_noun_no_gender_falls_back_without_gender_suffix():
    entry = {
        "pos": "N",
        "headword": "puella",
        "principal_parts": ["puell", "puell"],
        "decl_which": 1,
    }
    assert format_principal_parts(entry) == "puella, puellae"


def test_noun_4th_decl_exercitus():
    entry = {
        "pos": "N",
        "headword": "exercitus",
        "principal_parts": ["exercit", "exercit"],
        "gender": "M",
        "decl_which": 4,
    }
    assert format_principal_parts(entry) == "exercitus, exercitus, m."


def test_noun_4th_decl_manus():
    entry = {
        "pos": "N",
        "headword": "manus",
        "principal_parts": ["man", "man"],
        "gender": "F",
        "decl_which": 4,
    }
    assert format_principal_parts(entry) == "manus, manus, f."


def test_noun_5th_decl_res():
    entry = {
        "pos": "N",
        "headword": "res",
        "principal_parts": ["r", "r"],
        "gender": "F",
        "decl_which": 5,
    }
    assert format_principal_parts(entry) == "res, rei, f."


def test_noun_no_decl_which_falls_back_to_heuristic():
    """Without decl_which, shape-based heuristic still works for common cases."""
    entry = {
        "pos": "N",
        "headword": "puella",
        "principal_parts": ["puell", "puell"],
        "gender": "F",
    }
    assert format_principal_parts(entry) == "puella, puellae, f."


# ---------- adjectives ----------


def test_adj_bonus_us_a_um():
    entry = {
        "pos": "ADJ",
        "headword": "bonus",
        "principal_parts": ["bon", "bon", "meli", "opti"],
    }
    assert format_principal_parts(entry) == "bonus, -a, -um"


def test_adj_fortis_is_e():
    entry = {
        "pos": "ADJ",
        "headword": "fortis",
        "principal_parts": ["fort", "fort", "forti", "fortissi"],
    }
    assert format_principal_parts(entry) == "fortis, -e"


def test_adj_felix_one_ending_uses_stem2_for_gen():
    entry = {
        "pos": "ADJ",
        "headword": "felix",
        "principal_parts": ["felix", "felic", "felici", "felicissi"],
    }
    assert format_principal_parts(entry) == "felix, felicis"


# ---------- fallback ----------


def test_unknown_pos_returns_none():
    entry = {
        "pos": "ADV",
        "headword": "valde",
        "principal_parts": ["valde"],
    }
    assert format_principal_parts(entry) is None


def test_missing_headword_returns_none():
    entry = {"pos": "V", "principal_parts": ["am", "am"]}
    assert format_principal_parts(entry) is None
