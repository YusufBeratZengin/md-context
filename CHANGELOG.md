# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `--cache-dir PATH` option and `MD_CONTEXT_CACHE` environment variable on `index`, `query`, and `stats` to isolate index snapshots and prevent fixture pollution.
- `--top N` flag on `query` to limit the maximum number of heading sections included in the context pack.
- `--include-tag TAG` and `--exclude-tag TAG` filtering flags on `query` and API (`search`, `build_pack`).
- Strict validation and descriptive error messages for unsupported `--format` choices (`md`, `json`).
- Automated release workflow (`.github/workflows/release.yml`) on `v*` tags with PyPI trusted publishing (`pypa/gh-action-pypi-publish@release/v1`) and GitHub Releases.
- Enriched `pyproject.toml` metadata with trove classifiers, project URLs (`Source`, `Changelog`), more keywords, and `twine` in `dev` extra.
- Live CI, PyPI version, and license badges in `README.md` and `README.tr.md`.
- Real terminal transcript for `index`, `query`, and `stats` commands in documentation.
- Ready-to-use agent pipe examples in POSIX shell (`examples/agent-pipe.sh`) and PowerShell (`examples/agent-pipe.ps1`).
- Synthetic golden file test (`tests/test_golden.py` and `tests/golden/query-valve.md`) asserting quickstart output matches documented excerpts.
- In-memory caching of tokenized bodies, inverted index, and tag structures on loaded `Index` objects without schema changes.
- Large-vault synthetic benchmark script (`scripts/benchmark.py`) evaluating 2,000 notes and 20 queries under 10 seconds.
- Quality tests for Turkish case folding (`IŞIK` matching `ışık`, diacritic-stripped `isik`), stop punctuation handling, and edge cases.
- Comprehensive CLI error testing for missing roots, empty folders, corrupt index cache files, and non-UTF-8 encodings.
- Community health files: Contributor Covenant 2.1 Code of Conduct (`CODE_OF_CONDUCT.md`), issue templates (`bug_report.md`, `feature_request.md`), and PR template (`pull_request_template.md`).
- Extended CI matrix to test Python 3.11–3.13 on Ubuntu and verify quickstart execution on installed wheel outside the source tree.

### Fixed
- Include filename in error diagnostics when reading non-UTF-8 Markdown notes.
- Prevent fixture pollution in `tests/fixtures/vault` by defaulting documentation and testing workflows to custom cache directories.

## [0.1.0] — 2026-10-22

### Added
- Local Markdown indexing with an atomic, versioned JSON cache.
- Flat frontmatter parser, wikilinks, inline tags, and heading sections.
- Unicode-aware BM25 ranking with Turkish case folding, optional accent folding, and title, tag, recency, and one-hop graph boosts.
- Complete-output-budgeted Markdown and JSON context packs with relative source paths.
- Custom token estimator support through typed Python API.
- Privacy controls via `visibility: private`, `.mdcontextignore` patterns, and symlink protection.
- CLI commands: `index`, `query`, and `stats`.
- Bilingual documentation (English and Turkish) and cross-platform CI.

[Unreleased]: https://github.com/YusufBeratZengin/md-context/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YusufBeratZengin/md-context/releases/tag/v0.1.0
