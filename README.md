# md-context

[![CI](https://github.com/YusufBeratZengin/md-context/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/md-context/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/md-context.svg)](https://pypi.org/project/md-context/)
[![License](https://img.shields.io/github/license/YusufBeratZengin/md-context.svg)](LICENSE)

[Türkçe](README.tr.md)

Build a context pack for an LLM from a local folder of Markdown notes. md-context
ranks notes against a query, selects heading sections, and emits Markdown or JSON
within an estimated token budget. It works with Obsidian-style vaults and ordinary
documentation folders. Python 3.10 or newer; zero runtime dependencies.

## Install and try

Install from PyPI or checkout:

```sh
python -m pip install md-context
```

Quickstart with custom cache directory (keeps fixture clean):

```sh
md-context index tests/fixtures/vault --cache-dir .cache
md-context query "valve" --root tests/fixtures/vault --cache-dir .cache --budget 4000
md-context stats --root tests/fixtures/vault --cache-dir .cache
```

Captured terminal transcript:

```text
$ md-context index tests/fixtures/vault --cache-dir .cache
{"notes": 4, "chunks": 8, "links": 2, "tags": 8, "tag_edges": 9, "excluded": 3, "strip_diacritics": false}

$ md-context query "valve" --root tests/fixtures/vault --cache-dir .cache --budget 4000
# Context pack

Query: valve

## Valve schedule

Source: `Orchard.md`

Open the east valve at sunrise. Check soil moisture before the next irrigation cycle.

## Orchard irrigation

Source: `Orchard.md`

A fictional orchard uses drip irrigation to conserve water.
See [[Water storage]] for the supply plan. #planning

## Maintenance

Source: `Orchard.md`

Inspect each filter weekly and clean sediment from the pipes.

## Water storage

Source: `Water storage.md`

A demonstration tank holds rainwater for the orchard.

## Capacity

Source: `Water storage.md`

Reserve one quarter of the tank for dry weather. [[Orchard]]

$ md-context stats --root tests/fixtures/vault --cache-dir .cache
{"notes": 4, "chunks": 8, "links": 2, "tags": 8, "tag_edges": 9, "excluded": 3, "strip_diacritics": false}
```

Run without installation (POSIX shell):

```sh
PYTHONPATH=src python -m md_context query "water storage" --root tests/fixtures/vault --cache-dir .cache
```

PowerShell equivalent:

```powershell
$env:PYTHONPATH = 'src'
$env:PYTHONUTF8 = '1'
py -m md_context query 'water storage' --root tests/fixtures/vault --cache-dir .cache
```

To work from inside a vault:

```sh
cd /path/to/notes
md-context index . --strip-diacritics
md-context query "irrigation" --budget 4000
md-context query "irrigation" --budget 4000 --format json
md-context query "irrigation" --top 2 --include-tag gardening
md-context stats
```

`query` and `stats` find the nearest `.md-context/index.json` in the current folder
or its parents. Use `--root <dir>` from anywhere; an existing index is optional for
this form. `index` stores a JSON snapshot in the indexed folder's `.md-context/`
(or under `--cache-dir PATH` / `MD_CONTEXT_CACHE` environment variable).
Every CLI query and stats call rescans the source folder and replaces that snapshot,
preserving the normalization option. Deleted, newly private, and newly ignored
notes therefore leave the next successful snapshot and query. Reindex without
`--strip-diacritics` to turn accent folding off.

If a folder contains no Markdown files, `index` produces an index with 0 notes,
`query` returns an empty context pack with exit status 0, and `stats` reports
`{"notes": 0, ...}`. Invalid frontmatter, corrupt cache files, or unreadable
non-UTF-8 files fail the operation with exit status 2 and a diagnostic naming the
offending file on stderr, never an unhandled traceback.

## Pipe into an agent

Ready-to-use pipe scripts are provided in [`examples/agent-pipe.sh`](examples/agent-pipe.sh)
and [`examples/agent-pipe.ps1`](examples/agent-pipe.ps1).

With a local agent command that accepts context on standard input:

```sh
md-context query "irrigation valve schedule" --root ./notes --budget 4000 | local-agent
```

`local-agent` is a placeholder for your own agent CLI. md-context makes no network
requests. The receiving command determines where the selected text goes; review
the pack before sending it to any external service.

Example Markdown output (excerpt):

```markdown
# Context pack

Query: valve

## Valve schedule

Source: `Orchard.md`

Open the east valve at sunrise. Check soil moisture before the next irrigation cycle.
```

JSON contains `query`, `budget`, `estimated_tokens`, and a `sources` array. Each
source has `path` (relative to the vault), `title`, `heading`, `content`, `score`,
and `truncated`. Scores describe note relevance; selection also favors matching
sections. No matches produce an empty pack. A tiny budget that cannot hold the
output envelope produces an error.

### CLI options for `query`

- `--budget N`: Maximum token budget for the complete output (default: `4000`).
- `--format md|json`: Output format; defaults to `md`. Invalid choices exit with status 2.
- `--top N`: Maximum number of sections to include in the context pack. Must be positive.
- `--include-tag TAG`: Only include notes with this tag (repeatable for multiple tags).
- `--exclude-tag TAG`: Exclude notes with this tag (repeatable for multiple tags).
- `--cache-dir PATH`: Custom directory to read and write the index cache snapshot.
- `--root PATH`: Vault root folder.

## Notes, privacy, and ignores

Files with a `.md` extension (case insensitive) are read recursively as UTF-8.
Symlink files and directories are skipped, as are `.git/`, `.obsidian/`, and
`.md-context/`. The cache and ignore file themselves cannot be symlinks.

```yaml
---
title: "Orchard irrigation"
tags: [gardening, water]
date: 2026-01-15
updated: "2026-02-01T09:00:00Z"
visibility: public
---
```

The built-in frontmatter parser supports flat `key: value` pairs, inline lists,
block lists, quoted strings, and comments. Double quotes use JSON string escapes;
single quotes escape an apostrophe by doubling it. Scalars, including dates,
remain strings. Nested mappings, YAML anchors, and multiline scalars are unsupported
and cause an error. Duplicate keys and unclosed frontmatter also fail. Frontmatter
must start at the beginning of the file; a UTF-8 BOM is allowed.

Set `visibility: private` to exclude a note before its text enters the cache or
retrieval results. `.mdcontextignore` at the vault root excludes paths:

```gitignore
# Basename patterns match at any depth.
scratch-*.md
archive/
# Paths containing / are relative to the vault root.
drafts/**/*.md
!drafts/ready.md
```

Patterns are case sensitive on every OS. `*`, `?`, and character classes match
within a path segment; `**` matches zero or more segments. A leading `/` anchors
to the root, a trailing `/` matches directories, and later `!` rules reinclude
matches, even inside an ignored directory. Escaped patterns and Git's full
ignore syntax are unsupported. Built-in exclusions and private visibility cannot
be overridden. Ignored directories are still traversed to permit reinclude rules.

The cache contains full text of included notes. Keep `.md-context/` out of version
control and backups that should not contain note content. A failed refresh leaves
the previous cache on disk, but emits no pack. Python API snapshots also remain
unchanged until rebuilt. Exclusion does not redact references already written in
other public notes. See [SECURITY.md](SECURITY.md).

## How retrieval works

- Unicode word tokens use case folding. `I`, `İ`, `ı`, and `i` match each other;
  optional diacritic folding also makes `café` match `cafe`.
- BM25 uses `k1=1.2`, `b=0.75`. Title and tag matches add boosts of 2.0 and 1.5
  times the term's inverse document frequency.
- Recency multiplies lexical scores by up to 1.15, decaying with a 90-day time
  scale. It uses a valid `updated`, otherwise `date`, otherwise filesystem mtime.
  An invalid chosen date falls back to mtime; naive dates use UTC. Future dates
  receive the maximum recency boost.
- `[[wikilinks]]`, `[[note#section|label]]`, and shared frontmatter or inline
  `#tags` connect notes. A one-hop neighbor gets 0.2 times its strongest lexical
  neighbor's score. Links work in both directions for this boost; tag groups also
  connect their members. There is no recursive propagation or self-boost.
- Link targets resolve by vault path, then source-relative path, then unique
  filename stem or title. Ambiguous and missing targets are ignored. Frontmatter
  aliases are parsed but are not used for link resolution. Tags and links inside
  fenced or inline code are ignored.
- ATX headings (`#` through `######`) split sections; fenced code is preserved.
  Setext headings are kept as body text. Sections are sorted by note score and
  query overlap, with stable path and section-order tie breaking. Oversized
  sections may be prefix-trimmed and marked as truncated.

The default token estimate is `ceil(character_count / 4)`, **not a model tokenizer**.
The budget covers the complete serialized output, including query, paths, headings,
JSON metadata, and truncation markers. JSON's `estimated_tokens` is conservative
because its own digits consume space. The guarantee applies to the chosen estimator
and requested output format; formatting a pack differently requires a new budget
calculation. Character truncation can cut a sentence or code block. No room is
reserved for your agent's system prompt, tools, or answer.

## Performance and benchmark

md-context caches the pre-tokenized corpus and inverted index in memory on the
loaded `Index` object without altering the persisted cache schema version.

On a synthetic benchmark of 2,000 notes (`scripts/benchmark.py`):
- `build_index`: ~6.6 s
- `save_index`: ~0.10 s
- `load_index`: ~0.03 s
- 20 queries: ~1.5 s total (~76 ms/query; first query warmup ~130 ms)

*(Approximate, machine dependent numbers measured on Python 3.11).*

## Python API

```python
from md_context import build_index, build_pack, load_index, save_index, search

index = build_index("./notes", strip_diacritics=True)
save_index(index)  # Optional: queries can operate entirely in memory.
matches = search(index, "water", title_boost=2.0, neighbor_boost=0.2)
pack = build_pack(
    index,
    "water",
    budget=4000,
    top=5,
    include_tags=["gardening"],
    output_format="json",
)
print(pack.to_json(), end="")

# Plug in a tokenizer you already have; no tokenizer dependency is bundled.
# estimator must accept str and return a nonnegative int.
# pack = build_pack(index, "water", estimator=lambda text: len(encoder.encode(text)))
```

Custom estimators must be deterministic. Prefix search fills the budget best with
monotone counters; nonmonotone tokenizers can leave unused space. The final rendered
output is also measured to keep the budget valid. `build_index` refreshes the source;
`load_index` loads a snapshot without rescanning. There is no semantic or
vector search. `.mdcontextignore` is an exclusion tool, not an access-control boundary.

## Development

```sh
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

For dependency-free tests without installation, set `PYTHONPATH=src` as shown
above. Tests use original fictional notes and write temporary data only under
`is/test-tmp/` in the checkout. CI runs lint, typing, tests, and a wheel smoke check
on Ubuntu (Python 3.10–3.14) and Windows (Python 3.10, 3.14).

Contributions: [CONTRIBUTING.md](CONTRIBUTING.md). Changes:
[CHANGELOG.md](CHANGELOG.md). Licensed under the [MIT License](LICENSE).
