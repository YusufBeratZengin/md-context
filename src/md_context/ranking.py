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


@dataclass(frozen=True)
class _PreparedCorpus:
    bodies: list[Counter[str]]
    titles: list[set[str]]
    tags: list[set[str]]
    note_tags_normalized: list[set[str]]
    lengths: list[int]
    average: float
    neighbors: dict[str, set[str]]
    inverted_index: dict[str, set[int]]


def _prepare_corpus(index: Index) -> _PreparedCorpus:
    cached = getattr(index, "_cached_corpus", None)
    if isinstance(cached, _PreparedCorpus):
        return cached

    strip = index.strip_diacritics
    bodies = [Counter(tokenize(note.body, strip)) for note in index.notes]
    titles = [set(tokenize(note.title, strip)) for note in index.notes]
    tags = [set(tokenize(" ".join(note.tags), strip)) for note in index.notes]
    note_tags_normalized = [{normalize(tag, strip) for tag in note.tags} for note in index.notes]
    lengths = [sum(body.values()) for body in bodies]
    average = (sum(lengths) / len(lengths)) if lengths else 1.0

    neighbors: dict[str, set[str]] = {note.path: set(note.links) for note in index.notes}
    for note in index.notes:
        for target in note.links:
            if target in neighbors:
                neighbors[target].add(note.path)

    inverted: dict[str, set[int]] = {}
    for i, (body, title, tag) in enumerate(zip(bodies, titles, tags, strict=True)):
        for term in set(body) | title | tag:
            inverted.setdefault(term, set()).add(i)

    corpus = _PreparedCorpus(
        bodies=bodies,
        titles=titles,
        tags=tags,
        note_tags_normalized=note_tags_normalized,
        lengths=lengths,
        average=average,
        neighbors=neighbors,
        inverted_index=inverted,
    )
    object.__setattr__(index, "_cached_corpus", corpus)
    return corpus


def search(
    index: Index,
    query: str,
    *,
    title_boost: float = 2.0,
    tag_boost: float = 1.5,
    recency_boost: float = 0.15,
    neighbor_boost: float = 0.2,
    now: float | None = None,
    include_tags: list[str] | None = None,
    exclude_tags: list[str] | None = None,
) -> list[SearchResult]:
    """Rank lexical matches and one-hop neighbors; ties use source path."""
    boosts = (title_boost, tag_boost, recency_boost, neighbor_boost)
    if any(not math.isfinite(boost) or boost < 0 for boost in boosts):
        raise ValueError("boosts must be finite, nonnegative numbers")
    terms = sorted(set(tokenize(query, index.strip_diacritics)))
    if not terms or not index.notes:
        return []

    corpus = _prepare_corpus(index)
    bodies = corpus.bodies
    titles = corpus.titles
    tags = corpus.tags
    lengths = corpus.lengths
    average = corpus.average
    neighbors = corpus.neighbors
    inverted = corpus.inverted_index

    idf: dict[str, float] = {}
    total_docs = len(bodies)
    for term in terms:
        frequency = len(inverted.get(term, ()))
        idf[term] = math.log(1 + (total_docs - frequency + 0.5) / (frequency + 0.5))

    matching_doc_indices: set[int] = set()
    for term in terms:
        matching_doc_indices.update(inverted.get(term, ()))

    scores: dict[str, float] = {}
    timestamp = time.time() if now is None else now
    for i in matching_doc_indices:
        note = index.notes[i]
        body = bodies[i]
        title = titles[i]
        tag = tags[i]
        length = lengths[i]
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
    tag_scores: dict[str, list[tuple[float, str]]] = {}
    for note, norm_tags in zip(index.notes, corpus.note_tags_normalized, strict=True):
        lex_score = lexical.get(note.path, 0.0)
        for key in norm_tags:
            tag_scores.setdefault(key, []).append((lex_score, note.path))
    # Only the two strongest seeds per tag are needed to exclude self-boosts.
    tag_seeds = {tag: sorted(values, reverse=True)[:2] for tag, values in tag_scores.items()}
    for note, norm_tags in zip(index.notes, corpus.note_tags_normalized, strict=True):
        path, adjacent = note.path, neighbors[note.path]
        bonus = max((lexical.get(other, 0.0) for other in adjacent), default=0.0)
        tag_bonus = max(
            (score for key in norm_tags for score, source in tag_seeds[key] if source != path),
            default=0.0,
        )
        bonus = max(bonus, tag_bonus)
        if bonus and neighbor_boost:
            scores[path] = scores.get(path, 0.0) + neighbor_boost * bonus

    norm_include = (
        {normalize(t.lstrip("#"), index.strip_diacritics) for t in include_tags}
        if include_tags
        else None
    )
    norm_exclude = (
        {normalize(t.lstrip("#"), index.strip_diacritics) for t in exclude_tags}
        if exclude_tags
        else None
    )

    results: list[SearchResult] = []
    for note, norm_tags in zip(index.notes, corpus.note_tags_normalized, strict=True):
        if note.path not in scores:
            continue
        if norm_exclude and (norm_tags & norm_exclude):
            continue
        if norm_include and not (norm_tags & norm_include):
            continue
        results.append(SearchResult(note, scores[note.path]))

    results.sort(key=lambda result: (-result.score, result.note.path))
    return results
