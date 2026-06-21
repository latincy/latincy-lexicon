"""latincy-lexicon: Whitaker's Words data for LatinCy."""

__version__ = "0.4.0"

from latincy_lexicon.models import LewisShortSense  # noqa: F401
from latincy_lexicon.parsers.lewis_short_senses import (  # noqa: F401
    parse_entry as parse_lewis_short_senses,
)
from latincy_lexicon.principal_parts import format_principal_parts  # noqa: F401
