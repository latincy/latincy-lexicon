from latincy_lexicon import format_principal_parts

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
