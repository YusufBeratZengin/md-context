"""Choose heading chunks while accounting for the entire serialized output."""

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace

from .index import Index
from .ranking import search
from .text import tokenize

TokenEstimator = Callable[[str], int]


def estimate_tokens(text: str) -> int:
    """Conservative rounding of the default character-count / 4 heuristic."""
    return (len(text) + 3) // 4


class BudgetError(ValueError):
    """The requested budget cannot fit even the empty pack envelope."""


@dataclass(frozen=True)
class Source:
    path: str
    title: str
    heading: str
    content: str
    score: float
    truncated: bool = False


@dataclass
class Pack:
    query: str
    budget: int
    sources: list[Source] = field(default_factory=list)
    estimated_tokens: int = 0

    def to_markdown(self) -> str:
        query = " ".join(self.query.splitlines())
        lines = ["# Context pack", "", f"Query: {query}"]
        for source in self.sources:
            path = source.path.replace("`", "\\`")
            heading = " ".join((source.heading or source.title).splitlines())
            lines.extend(["", f"## {heading}", "", f"Source: `{path}`", "", source.content])
            if source.truncated:
                lines.extend(["", "[Truncated to fit token budget.]"])
        return "\n".join(lines) + "\n"

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, allow_nan=False) + "\n"

    def render(self, output_format: str = "md") -> str:
        if output_format not in {"md", "json"}:
            raise ValueError("format must be md or json")
        return self.to_markdown() if output_format == "md" else self.to_json()


def _measure(pack: Pack, output_format: str, estimator: TokenEstimator) -> int:
    # JSON includes the estimate itself. Reserve a budget-width number so its
    # digits cannot make the measured envelope grow on the final pass.
    pack.estimated_tokens = pack.budget

    def count_output() -> int:
        count = estimator(pack.render(output_format))
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("token estimator must return a nonnegative integer")
        return count

    count = count_output()
    # Real tokenizers can count different digit strings differently, even at
    # equal character lengths. Verify the actual final representation as well.
    for _ in range(16):
        pack.estimated_tokens = count
        actual = count_output()
        if actual <= count:
            return count
        count = actual
    raise ValueError("token estimator cannot produce a stable output estimate")


def build_pack(
    index: Index,
    query: str,
    budget: int = 4000,
    *,
    output_format: str = "md",
    estimator: TokenEstimator = estimate_tokens,
) -> Pack:
    """Greedily select relevant chunks; an oversized chunk may be prefix-trimmed.

    Custom estimators must be deterministic. Monotone prefix counts give the
    fullest packs; other counters can underfill. The final output is measured.
    The returned estimate is conservative for JSON's estimate field.
    """
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise ValueError("budget must be a positive integer")
    pack = Pack(query, budget)
    if _measure(pack, output_format, estimator) > budget:
        raise BudgetError("budget is too small for the output envelope; increase --budget")
    terms = set(tokenize(query, index.strip_diacritics))
    candidates: list[tuple[float, str, int, Source]] = []
    for result in search(index, query):
        note = result.note
        for position, chunk in enumerate(note.chunks):
            heading_terms = set(tokenize(chunk.heading, index.strip_diacritics))
            content_terms = set(tokenize(chunk.content, index.strip_diacritics))
            overlap = len(terms & content_terms) + 2 * len(terms & heading_terms)
            score = result.score * (1 + overlap / max(1, len(terms)))
            candidates.append(
                (
                    score,
                    note.path,
                    position,
                    Source(
                        note.path,
                        note.title,
                        chunk.heading,
                        chunk.content,
                        round(result.score, 6),
                    ),
                )
            )
    for _, _, _, source in sorted(candidates, key=lambda item: (-item[0], item[1], item[2])):
        pack.sources.append(source)
        if _measure(pack, output_format, estimator) <= budget:
            continue
        pack.sources.pop()
        # Binary search keeps processing long notes cheap for monotone counters.
        low, high = 0, len(source.content) - 1
        best: Source | None = None
        while low <= high:
            middle = (low + high) // 2
            clipped = replace(source, content=source.content[:middle].rstrip(), truncated=True)
            pack.sources.append(clipped)
            fits = _measure(pack, output_format, estimator) <= budget
            pack.sources.pop()
            if fits:
                if clipped.content:
                    best = clipped
                low = middle + 1
            else:
                high = middle - 1
        if best:
            pack.sources.append(best)
    _measure(pack, output_format, estimator)
    if pack.estimated_tokens > budget:
        raise BudgetError("token estimator did not produce a stable in-budget result")
    return pack
