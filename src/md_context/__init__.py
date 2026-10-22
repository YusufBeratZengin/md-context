"""Local Markdown retrieval with a strict output token budget."""

from .index import Index, build_index, load_index, save_index
from .pack import BudgetError, Pack, build_pack, estimate_tokens
from .ranking import SearchResult, search

__version__ = "0.1.0"
__all__ = [
    "BudgetError",
    "Index",
    "Pack",
    "SearchResult",
    "build_index",
    "build_pack",
    "estimate_tokens",
    "load_index",
    "save_index",
    "search",
]
