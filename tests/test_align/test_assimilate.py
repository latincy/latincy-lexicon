"""Prefix-assimilation variants for WW → L&S alignment.

WW stores etymological, un-assimilated prefixes (``adcedo``, ``conloco``,
``inludo``), while L&S indexes the classical assimilated spelling
(``accedo``, ``colloco``, ``illudo``). ``assimilated_forms`` bridges the gap.
"""

from latincy_lexicon.align.assimilate import assimilated_forms


def test_ad_assimilates_to_following_consonant():
    assert assimilated_forms("adcedo") == ["accedo"]
    assert assimilated_forms("adfero") == ["affero"]
    assert assimilated_forms("adgredior") == ["aggredior"]
    assert assimilated_forms("adpono") == ["appono"]
    assert assimilated_forms("adrideo") == ["arrideo"]
    assert assimilated_forms("adtineo") == ["attineo"]


def test_ad_before_q_becomes_acq():
    assert assimilated_forms("adquiro") == ["acquiro"]


def test_con_assimilates_l_r_m():
    assert assimilated_forms("conloco") == ["colloco"]
    assert assimilated_forms("conrumpo") == ["corrumpo"]
    assert assimilated_forms("conmoveo") == ["commoveo"]


def test_in_assimilates_l_r_and_labials():
    assert assimilated_forms("inludo") == ["illudo"]
    assert assimilated_forms("inrumpo") == ["irrumpo"]
    assert assimilated_forms("inmitto") == ["immitto"]
    assert assimilated_forms("inpono") == ["impono"]


def test_sub_ob_assimilation():
    assert assimilated_forms("subfero") == ["suffero"]
    assert assimilated_forms("subpono") == ["suppono"]
    assert assimilated_forms("obcurro") == ["occurro"]
    assert assimilated_forms("obfero") == ["offero"]


def test_ex_dis_assimilation():
    assert assimilated_forms("exfero") == ["effero"]
    assert assimilated_forms("disfero") == ["differo"]


def test_no_prefix_no_variant():
    assert assimilated_forms("amo") == []
    assert assimilated_forms("virtus") == []


def test_already_assimilated_no_variant():
    # An already-classical spelling shouldn't be re-transformed.
    assert assimilated_forms("accedo") == []
    assert assimilated_forms("colloco") == []
