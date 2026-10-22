"""Build and persist a local, versioned Markdown snapshot."""

import json
import os
import posixpath
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ignore import is_ignored
from .parsing import Chunk, FrontmatterError, chunks_by_heading, parse_frontmatter, scan_markdown
from .text import normalize

CACHE_VERSION = 1
CACHE_DIRECTORY = ".md-context"


@dataclass(frozen=True)
class Note:
    path: str
    title: str
    tags: list[str]
    links: list[str]
    body: str
    chunks: list[Chunk]
    modified: float


@dataclass(frozen=True)
class Index:
    root: Path
    notes: list[Note]
    strip_diacritics: bool = False
    excluded_count: int = 0

    def stats(self) -> dict[str, int | bool]:
        return {
            "notes": len(self.notes),
            "chunks": sum(len(note.chunks) for note in self.notes),
            "links": sum(len(note.links) for note in self.notes),
            "tags": len({tag for note in self.notes for tag in note.tags}),
            "tag_edges": sum(len(note.tags) for note in self.notes),
            "excluded": self.excluded_count,
            "strip_diacritics": self.strip_diacritics,
        }


def _timestamp(value: str | list[str] | None, fallback: float) -> float:
    if not isinstance(value, str):
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (ValueError, OverflowError, OSError):
        return fallback


def _resolve_links(notes: list[Note]) -> list[Note]:
    paths: dict[str, list[str]] = {}
    names: dict[str, list[str]] = {}
    for note in notes:
        key = normalize(Path(note.path).with_suffix("").as_posix())
        paths.setdefault(key, []).append(note.path)
        for name in {Path(note.path).stem, note.title}:
            key = normalize(name)
            if note.path not in names.setdefault(key, []):
                names[key].append(note.path)
    resolved: list[Note] = []
    for note in notes:
        links: set[str] = set()
        for target in note.links:
            if target.lower().endswith(".md"):
                target = target[:-3]
            relative = posixpath.normpath(posixpath.join(posixpath.dirname(note.path), target))
            candidates = paths.get(normalize(target.lstrip("/")), [])
            if not candidates:
                candidates = paths.get(normalize(relative), [])
            if not candidates and "/" not in target:
                candidates = names.get(normalize(target), [])
            if len(candidates) == 1 and candidates[0] != note.path:
                links.add(candidates[0])
        resolved.append(
            Note(
                note.path,
                note.title,
                note.tags,
                sorted(links),
                note.body,
                note.chunks,
                note.modified,
            )
        )
    return resolved


def build_index(root: str | Path, *, strip_diacritics: bool = False) -> Index:
    """Read UTF-8 notes, excluding private/ignored files and all symlinks."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    ignore_path = root / ".mdcontextignore"
    if ignore_path.is_symlink():
        raise ValueError(".mdcontextignore must not be a symlink")
    rules = ignore_path.read_text(encoding="utf-8-sig").splitlines() if ignore_path.exists() else []
    notes: list[Note] = []
    excluded = 0

    def walk_error(error: OSError) -> None:
        raise error

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(
            name
            for name in dirs
            if name not in {".git", ".md-context", ".obsidian"}
            and not (Path(directory) / name).is_symlink()
        )
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix.lower() != ".md":
                continue
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or is_ignored(relative, rules):
                excluded += 1
                continue
            try:
                metadata, body = parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            except FrontmatterError as exc:
                raise FrontmatterError(f"{relative}: {exc}") from exc
            visibility = metadata.get("visibility", "")
            if isinstance(visibility, str) and visibility.strip().casefold() == "private":
                excluded += 1
                continue
            links, inline_tags, heading = scan_markdown(body)
            raw_tags = metadata.get("tags", [])
            tags = raw_tags if isinstance(raw_tags, list) else raw_tags.replace(",", " ").split()
            title = metadata.get("title")
            title = title if isinstance(title, str) and title.strip() else heading or path.stem
            modified = _timestamp(
                metadata.get("updated", metadata.get("date")),
                path.stat().st_mtime,
            )
            notes.append(
                Note(
                    relative,
                    title,
                    sorted({normalize(tag.lstrip("#")) for tag in tags + inline_tags}),
                    links,
                    body,
                    chunks_by_heading(body),
                    modified,
                )
            )
    return Index(root, _resolve_links(notes), strip_diacritics, excluded)


def _cache_path(root: Path) -> Path:
    directory = root / CACHE_DIRECTORY
    path = directory / "index.json"
    if directory.is_symlink() or path.is_symlink():
        raise ValueError("index cache must not be a symlink")
    return path


def save_index(index: Index) -> Path:
    """Replace the cache atomically; it contains the full text of included notes."""
    path = _cache_path(index.root)
    path.parent.mkdir(exist_ok=True)
    data = {
        "version": CACHE_VERSION,
        "strip_diacritics": index.strip_diacritics,
        "excluded_count": index.excluded_count,
        "notes": [asdict(note) for note in index.notes],
    }
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = stream.name
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
    return path


def load_index(root: str | Path) -> Index:
    root = Path(root).resolve()
    try:
        data: Any = json.loads(_cache_path(root).read_text(encoding="utf-8"))
        if data["version"] != CACHE_VERSION:
            raise ValueError("unsupported index version; run md-context index again")
        notes = [
            Note(
                path=n["path"],
                title=n["title"],
                tags=n["tags"],
                links=n["links"],
                body=n["body"],
                chunks=[Chunk(**chunk) for chunk in n["chunks"]],
                modified=n["modified"],
            )
            for n in data["notes"]
        ]
        option = data["strip_diacritics"]
        if not isinstance(option, bool):
            raise ValueError("invalid normalization option")
        return Index(root, notes, option, int(data["excluded_count"]))
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid index cache; run md-context index again") from exc
