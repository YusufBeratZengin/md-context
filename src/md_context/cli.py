"""Command-line interface; all data stays on the local filesystem."""

import argparse
import io
import json
import os
import sys
from pathlib import Path

from . import __version__
from .index import CACHE_DIRECTORY, Index, build_index, load_index, save_index
from .pack import build_pack


def _cache_dir(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit.resolve()
    env = os.environ.get("MD_CONTEXT_CACHE")
    if env and env.strip():
        return Path(env.strip()).resolve()
    return None


def _root(explicit: str | None, cache_dir: Path | None = None) -> Path:
    if explicit is not None:
        path = Path(explicit).resolve()
        if not path.is_dir():
            raise ValueError(f"not a directory: {path}")
        return path
    if cache_dir is not None:
        cache_file = cache_dir / "index.json"
        if cache_file.is_file():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "root" in data:
                    root_path = Path(data["root"]).resolve()
                    if root_path.is_dir():
                        return root_path
            except Exception:
                pass
    current = Path.cwd()
    for candidate in (current, *current.parents):
        if (candidate / CACHE_DIRECTORY / "index.json").is_file():
            return candidate
    raise ValueError("no index found; run md-context index <dir> or use --root <dir>")


def _refresh(explicit: str | None, cache_dir: Path | None = None) -> Index:
    root = _root(explicit, cache_dir=cache_dir)
    cache_path = (
        (cache_dir / "index.json")
        if cache_dir is not None
        else (root / CACHE_DIRECTORY / "index.json")
    )
    strip = False
    if cache_path.is_file():
        strip = load_index(root, cache_dir=cache_dir).strip_diacritics
    index = build_index(root, strip_diacritics=strip)
    save_index(index, cache_dir=cache_dir)
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
    index_parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="directory to store index cache (default: <root>/.md-context or MD_CONTEXT_CACHE)",
    )

    query_parser = commands.add_parser("query", help="rank notes and emit a context pack")
    query_parser.add_argument("query")
    query_parser.add_argument("--budget", type=int, default=4000)
    query_parser.add_argument("--format", default="md")
    query_parser.add_argument("--root", help="vault folder (otherwise find nearest parent index)")
    query_parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="directory to store index cache (default: <root>/.md-context or MD_CONTEXT_CACHE)",
    )
    query_parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="maximum number of sections to include",
    )
    query_parser.add_argument(
        "--include-tag",
        action="append",
        dest="include_tags",
        default=None,
        help="only include notes with this tag (repeatable)",
    )
    query_parser.add_argument(
        "--exclude-tag",
        action="append",
        dest="exclude_tags",
        default=None,
        help="exclude notes with this tag (repeatable)",
    )

    stats_parser = commands.add_parser("stats", help="show current index statistics as JSON")
    stats_parser.add_argument("--root", help="vault folder (otherwise find nearest parent index)")
    stats_parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="directory to store index cache (default: <root>/.md-context or MD_CONTEXT_CACHE)",
    )

    args = parser.parse_args(argv)
    try:
        cache_dir = _cache_dir(args.cache_dir)
        if args.command == "index":
            index = build_index(args.directory, strip_diacritics=args.strip_diacritics)
            save_index(index, cache_dir=cache_dir)
            print(json.dumps(index.stats(), ensure_ascii=False))
        elif args.command == "stats":
            print(json.dumps(_refresh(args.root, cache_dir=cache_dir).stats(), ensure_ascii=False))
        else:
            if args.format not in {"md", "json"}:
                raise ValueError(f"invalid format '{args.format}'; choose 'md' or 'json'")
            if args.top is not None and args.top <= 0:
                raise ValueError("top must be a positive integer")
            pack = build_pack(
                _refresh(args.root, cache_dir=cache_dir),
                args.query,
                args.budget,
                output_format=args.format,
                top=args.top,
                include_tags=args.include_tags,
                exclude_tags=args.exclude_tags,
            )
            sys.stdout.write(pack.render(args.format))
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"md-context: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
