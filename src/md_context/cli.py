"""Command-line interface; all data stays on the local filesystem."""

import argparse
import io
import json
import sys
from pathlib import Path

from . import __version__
from .index import CACHE_DIRECTORY, Index, build_index, load_index, save_index
from .pack import build_pack


def _root(explicit: str | None) -> Path:
    if explicit is not None:
        return Path(explicit).resolve()
    current = Path.cwd()
    for candidate in (current, *current.parents):
        if (candidate / CACHE_DIRECTORY / "index.json").is_file():
            return candidate
    raise ValueError("no index found; run md-context index <dir> or use --root <dir>")


def _refresh(explicit: str | None) -> Index:
    root = _root(explicit)
    cache = root / CACHE_DIRECTORY / "index.json"
    strip = load_index(root).strip_diacritics if cache.exists() else False
    index = build_index(root, strip_diacritics=strip)
    save_index(index)
    return index


def main(argv: list[str] | None = None) -> int:
    # Emit the exact UTF-8/LF representation that was measured, including on
    # Windows where the default text stream can translate LF into CRLF.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser(description="Build local Markdown context packs.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    index_parser = commands.add_parser("index", help="index a Markdown folder")
    index_parser.add_argument("directory", type=Path)
    index_parser.add_argument("--strip-diacritics", action="store_true")
    query_parser = commands.add_parser("query", help="rank notes and emit a context pack")
    query_parser.add_argument("query")
    query_parser.add_argument("--budget", type=int, default=4000)
    query_parser.add_argument("--format", choices=["md", "json"], default="md")
    query_parser.add_argument("--root", help="vault folder (otherwise find nearest parent index)")
    stats_parser = commands.add_parser("stats", help="show current index statistics as JSON")
    stats_parser.add_argument("--root", help="vault folder (otherwise find nearest parent index)")
    args = parser.parse_args(argv)
    try:
        if args.command == "index":
            index = build_index(args.directory, strip_diacritics=args.strip_diacritics)
            save_index(index)
            print(json.dumps(index.stats(), ensure_ascii=False))
        elif args.command == "stats":
            print(json.dumps(_refresh(args.root).stats(), ensure_ascii=False))
        else:
            pack = build_pack(
                _refresh(args.root),
                args.query,
                args.budget,
                output_format=args.format,
            )
            sys.stdout.write(pack.render(args.format))
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"md-context: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
