"""BM25 note ranking with explicit field, recency and graph boosts."""

import math
import time
from collections import Counter
from dataclasses import dataclass

from .index import Index, Note
from .text import normalize, tokenize


@dataclass(frozen=True)
class SearchResult:
    note: Note
    score: float


def search(
    index: Index,
    query: str,
    *,
    title_boost: float = 2.0,
    tag_boost: float = 1.5,
    recency_boost: float = 0.15,
    neighbor_boost: float = 0.2,
    now: float | None = None,
) -> list[SearchResult]:
    """Rank lexical matches and one-hop neighbors; ties use source path."""
    boosts = (title_boost, tag_boost, recency_boost, neighbor_boost)
    if any(not math.isfinite(boost) or boost < 0 for boost in boosts):
        raise ValueError("boosts must be finite, nonnegative numbers")
    terms = sorted(set(tokenize(query, index.strip_diacritics)))
    if not terms or not index.notes:
        return []
    bodies = [Counter(tokenize(note.body, index.strip_diacritics)) for note in index.notes]
    titles = [set(tokenize(note.title, index.strip_diacritics)) for note in index.notes]
    tags = [set(tokenize(" ".join(note.tags), index.strip_diacritics)) for note in index.notes]
    lengths = [sum(body.values()) for body in bodies]
    average = sum(lengths) / len(lengths) or 1.0
    idf = {
        term: math.log(1 + (len(bodies) - frequency + 0.5) / (frequency + 0.5))
        for term in terms
        for frequency in [
            sum(
                term in body or term in title or term in tag
                for body, title, tag in zip(bodies, titles, tags, strict=True)
            )
        ]
    }
    scores: dict[str, float] = {}
    timestamp = time.time() if now is None else now
    for note, body, title, tag, length in zip(
        index.notes, bodies, titles, tags, lengths, strict=True
    ):
        score = 0.0
        for term in terms:
            frequency = body[term]
            denominator = frequency + 1.2 * (0.25 + 0.75 * length / average)
            score += idf[term] * frequency * 2.2 / denominator
            score += idf[term] * (title_boost * (term in title) + tag_boost * (term in tag))
        if score > 0:
            age_days = max(0.0, (timestamp - note.modified) / 86400)
            score *= 1 + recency_boost * math.exp(-age_days / 90)
            scores[note.path] = score
    # One pass from lexical scores only: graph cycles cannot amplify themselves.
    lexical = dict(scores)
    neighbors = {note.path: set(note.links) for note in index.notes}
    for note in index.notes:
        for target in note.links:
            if target in neighbors:
                neighbors[target].add(note.path)
    tag_scores: dict[str, list[tuple[float, str]]] = {}
    for note in index.notes:
        for key in {normalize(tag_name, index.strip_diacritics) for tag_name in note.tags}:
            tag_scores.setdefault(key, []).append((lexical.get(note.path, 0.0), note.path))
    # Only the two strongest seeds per tag are needed to exclude self-boosts.
    tag_seeds = {tag: sorted(values, reverse=True)[:2] for tag, values in tag_scores.items()}
    for note in index.notes:
        path, adjacent = note.path, neighbors[note.path]
        bonus = max((lexical.get(other, 0.0) for other in adjacent), default=0.0)
        tag_bonus = max(
            (
                score
                for tag in note.tags
                for score, source in tag_seeds[normalize(tag, index.strip_diacritics)]
                if source != path
            ),
            default=0.0,
        )
        bonus = max(bonus, tag_bonus)
        if bonus and neighbor_boost:
            scores[path] = scores.get(path, 0.0) + neighbor_boost * bonus
    return sorted(
        (SearchResult(note, scores[note.path]) for note in index.notes if note.path in scores),
        key=lambda result: (-result.score, result.note.path),
    )
