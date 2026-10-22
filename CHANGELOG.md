# Changelog

## 0.1.0 — 2026-10-22

- Add local Markdown indexing with an atomic, versioned JSON cache.
- Parse flat frontmatter, wikilinks, inline tags, and heading sections.
- Rank with Unicode-aware BM25, Turkish case folding, optional accent folding,
  and title, tag, recency, and one-hop graph boosts.
- Build complete-output-budgeted Markdown and JSON context packs with source paths.
- Support custom token estimators through the typed Python API.
- Exclude private notes, ignore patterns, and symlinks; refresh before CLI retrieval.
- Add index, query, and stats commands, synthetic fixture tests, bilingual usage
  guides, and cross-platform CI.
