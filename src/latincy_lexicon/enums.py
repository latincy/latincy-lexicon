"""StrEnum types mirroring Whitaker's Words Ada definitions."""

from enum import StrEnum


class PartOfSpeech(StrEnum):
    """Part of speech codes from DICTLINE."""
    N = "N"          # Noun
    PRON = "PRON"    # Pronoun
    PACK = "PACK"    # PACKON (pronoun add-on)
    ADJ = "ADJ"      # Adjective
    NUM = "NUM"      # Numeral
    ADV = "ADV"      # Adverb
    V = "V"          # Verb
    VPAR = "VPAR"    # Verb participle
    SUPINE = "SUPINE"
    PREP = "PREP"    # Preposition
    CONJ = "CONJ"    # Conjunction
    INTERJ = "INTERJ"  # Interjection
    TACKON = "TACKON"
    PREFIX = "PREFIX"
    SUFFIX = "SUFFIX"
    X = "X"          # Undefined / catch-all


class Gender(StrEnum):
    M = "M"      # Masculine
    F = "F"      # Feminine
    N = "N"      # Neuter
    C = "C"      # Common (masc or fem)
    X = "X"      # Unknown / all


class Case(StrEnum):
    NOM = "NOM"
    GEN = "GEN"
    DAT = "DAT"
    ACC = "ACC"
    ABL = "ABL"
    VOC = "VOC"
    LOC = "LOC"
    X = "X"


class Number(StrEnum):
    S = "S"      # Singular
    P = "P"      # Plural
    X = "X"


class Tense(StrEnum):
    PRES = "PRES"
    IMPF = "IMPF"
    FUT = "FUT"
    PERF = "PERF"
    PLUP = "PLUP"
    FUTP = "FUTP"
    X = "X"


class Voice(StrEnum):
    ACTIVE = "ACTIVE"
    PASSIVE = "PASSIVE"
    X = "X"


class Mood(StrEnum):
    IND = "IND"
    SUB = "SUB"
    IMP = "IMP"
    INF = "INF"
    PPL = "PPL"
    X = "X"


class Person(StrEnum):
    FIRST = "1"
    SECOND = "2"
    THIRD = "3"
    X = "0"


class Comparison(StrEnum):
    POS = "POS"
    COMP = "COMP"
    SUPER = "SUPER"
    X = "X"


class NounKind(StrEnum):
    S = "S"          # Singular only
    M = "M"          # Plural only (pluralia tantum)
    A = "A"          # Abstract
    G = "G"          # Group/collective
    N = "N"          # Proper name
    P = "P"          # Person
    T = "T"          # Thing
    L = "L"          # Locale
    W = "W"          # Place (where)
    X = "X"


class VerbKind(StrEnum):
    TO_BE = "TO_BE"
    TO_BEING = "TO_BEING"
    GEN = "GEN"
    DAT = "DAT"
    ABL = "ABL"
    TRANS = "TRANS"
    INTRANS = "INTRANS"
    IMPERS = "IMPERS"
    DEP = "DEP"
    SEMIDEP = "SEMIDEP"
    PERFDEF = "PERFDEF"
    X = "X"


class PronounKind(StrEnum):
    PERS = "PERS"      # Personal
    REL = "REL"        # Relative
    REFLEX = "REFLEX"  # Reflexive
    DEMONS = "DEMONS"  # Demonstrative
    INTERR = "INTERR"  # Interrogative
    INDEF = "INDEF"    # Indefinite
    ADJECT = "ADJECT"  # Adjectival
    X = "X"


class NumeralSort(StrEnum):
    CARD = "CARD"    # Cardinal
    ORD = "ORD"      # Ordinal
    DIST = "DIST"    # Distributive
    ADVERB = "ADVERB"  # Numeral adverb
    X = "X"


class Age(StrEnum):
    """Time period when the word was in use."""
    A = "A"  # Archaic (very early)
    B = "B"  # Early Latin (before 100 BCE)
    C = "C"  # Classical (100 BCE - 200 CE)
    D = "D"  # Late Latin (200 - 600 CE)
    E = "E"  # Early Medieval (600 - 1000 CE)
    F = "F"  # Later Medieval (1000 - 1500 CE)
    G = "G"  # Scholar (post-1500)
    H = "H"  # Modern (post-1700, scientific)
    X = "X"  # Unknown


class Frequency(StrEnum):
    """How common the word is."""
    A = "A"  # Very frequent — top 1000 words
    B = "B"  # Frequent
    C = "C"  # Common
    D = "D"  # Lesser
    E = "E"  # Uncommon
    F = "F"  # Very rare
    I = "I"  # Inscription only
    M = "M"  # Graffiti
    N = "N"  # Pliny only
    X = "X"  # Unknown


class Area(StrEnum):
    """Subject area."""
    A = "A"  # Agriculture
    B = "B"  # Biology
    D = "D"  # Art
    E = "E"  # Church/religion
    G = "G"  # Grammar
    L = "L"  # Legal
    P = "P"  # Poetic
    S = "S"  # Science
    T = "T"  # Technical
    W = "W"  # War/military
    Y = "Y"  # Mythology
    X = "X"  # Unknown


class Geo(StrEnum):
    """Geographic source."""
    A = "A"  # Africa
    B = "B"  # Britain
    C = "C"  # China
    D = "D"  # Scandinavia
    E = "E"  # Egypt
    F = "F"  # France/Gaul
    G = "G"  # Germany
    H = "H"  # Greece
    I = "I"  # Italy (non-Rome)
    J = "J"  # India
    K = "K"  # Balkans
    N = "N"  # Netherlands
    P = "P"  # Persia
    Q = "Q"  # Near East
    R = "R"  # Russia
    S = "S"  # Spain/Iberia
    U = "U"  # Eastern Europe
    X = "X"  # Unknown


class Source(StrEnum):
    """Dictionary source for the entry."""
    A = "A"
    B = "B"  # C.H.Beeson, A Primer of Medieval Latin
    C = "C"  # Cassell's
    D = "D"  # J.N.Adams, Latin Sexual Vocabulary
    E = "E"  # L.F.Stelten, Dictionary of Eccl. Latin
    F = "F"  # Roy J. Deferrari, A Latin-English Dict. of St. Thomas Aquinas
    G = "G"  # Lewis & Short
    H = "H"
    I = "I"
    J = "J"
    K = "K"  # Calepinus Novus
    L = "L"  # Lewis
    M = "M"  # Latham
    N = "N"
    O = "O"  # Oxford Latin Dictionary
    P = "P"  # Souter
    Q = "Q"  # Other
    R = "R"
    S = "S"  # Whitaker custom
    T = "T"
    U = "U"
    V = "V"  # Vademecum (De Groot)
    W = "W"  # Whitaker's Words
    X = "X"  # Unknown
    Y = "Y"
    Z = "Z"


class AddonType(StrEnum):
    PREFIX = "PREFIX"
    SUFFIX = "SUFFIX"
    TACKON = "TACKON"
    PACKON = "PACKON"


class TrickClass(StrEnum):
    """Trick categories from Words source."""
    ANY = "ANY"
    MEDIAEVAL = "MEDIAEVAL"
    SYNCOPE = "SYNCOPE"
    ARCHAIC = "ARCHAIC"
    SLUR = "SLUR"


WORDS_TO_UD_POS: dict[str, set[str]] = {
    "N": {"NOUN", "PROPN"},
    "V": {"VERB", "AUX"},
    "ADJ": {"ADJ"},
    "ADV": {"ADV"},
    "PREP": {"ADP"},
    "CONJ": {"CCONJ", "SCONJ"},
    "INTERJ": {"INTJ"},
    "PRON": {"PRON", "DET"},
    "PACK": {"PRON", "DET"},
    "NUM": {"NUM"},
    "VPAR": {"VERB", "ADJ"},
    "SUPINE": {"VERB"},
    "PREFIX": {"X"},
    "SUFFIX": {"X"},
    "TACKON": {"CCONJ", "SCONJ", "PART", "ADV"},
    "X": set(),
}
