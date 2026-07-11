"""latincy-lexicon: Whitaker's Words data for LatinCy."""

__version__ = "0.10.0"

from latincy_lexicon.build import build_lexicon, senses_path, sense_index_path  # noqa: F401
from latincy_lexicon.models import LewisShortSense  # noqa: F401
from latincy_lexicon.parsers.lewis_short_senses import (  # noqa: F401
    parse_entry as parse_lewis_short_senses,
)
from latincy_lexicon.principal_parts import (  # noqa: F401
    format_principal_parts,
    pronominal_citation,
)
