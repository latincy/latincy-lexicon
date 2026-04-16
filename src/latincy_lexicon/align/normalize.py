"""Latin text normalization: v→u, j→i.

Standalone reimplementation of latincy-words/scripts/utils/normalize.py.
No external dependencies.
"""

_VJ_TRANS = str.maketrans("vjVJ", "uiUI")


def normalize_latin(text: str) -> str:
    """Normalize v→u, j→i in Latin text (all cases), then lowercase.

    This matches LatinCy's internal u-space convention.

    Examples:
        >>> normalize_latin("verbum")
        'uerbum'
        >>> normalize_latin("Juno")
        'iuno'
        >>> normalize_latin("VENUS")
        'uenus'
    """
    if not text:
        return text
    return text.translate(_VJ_TRANS).lower()


def normalize_vj(text: str) -> str:
    """Normalize v→u, j→i without case folding.

    Examples:
        >>> normalize_vj("verbum")
        'uerbum'
        >>> normalize_vj("Verbum")
        'Uerbum'
    """
    if not text:
        return text
    return text.translate(_VJ_TRANS)
