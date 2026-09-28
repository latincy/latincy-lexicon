"""latincy-lexicon: Whitaker's Words data for LatinCy."""

__version__ = "0.12.0"

from latincy_lexicon.build import (  # noqa: F401
    build_analyzer,
    build_lexicon,
    build_lexicon_and_analyzer,
    load_senses,
    sense_index_path,
    senses_path,
)
from latincy_lexicon.models import LewisShortSense  # noqa: F401
from latincy_lexicon.parsers.lewis_short_senses import (  # noqa: F401
    parse_entry as parse_lewis_short_senses,
)
from latincy_lexicon.parsers.lewis_short_senses import (
    parse_entry_full as parse_lewis_short_entry_full,  # noqa: F401
)
from latincy_lexicon.principal_parts import (  # noqa: F401
    format_principal_parts,
    pronominal_citation,
)
