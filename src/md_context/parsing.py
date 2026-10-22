"""A deliberately small, strict frontmatter parser and Markdown scanner."""

import json
import re
from dataclasses import dataclass

Metadata = dict[str, str | list[str]]


class FrontmatterError(ValueError):
    """Frontmatter is outside the supported flat subset."""


def _uncomment(value: str) -> str:
    quote = ""
    escaped = False
    for pos, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote == '"':
            escaped = True
        elif quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "#" and (pos == 0 or value[pos - 1].isspace()):
            return value[:pos].rstrip()
    return value.strip()


def _scalar(value: str) -> str:
    value = _uncomment(value.strip())
    if value.startswith('"'):
        try:
            result = json.loads(value)
        except ValueError as exc:
            raise FrontmatterError("invalid double-quoted string") from exc
        if not isinstance(result, str):
            raise FrontmatterError("expected a string")
        return result
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise FrontmatterError("unclosed single-quoted string")
        return value[1:-1].replace("''", "'")
    if value.startswith(("{", "&", "*", "!", "|", ">")):
        raise FrontmatterError("nested YAML, aliases and multiline values are unsupported")
    return value


def _value(value: str) -> str | list[str]:
    value = _uncomment(value.strip())
    if not value.startswith("["):
        return _scalar(value)
    if not value.endswith("]"):
        raise FrontmatterError("unclosed inline list")
    parts: list[str] = []
    start = 1
    quote = ""
    escaped = False
    for pos in range(1, len(value) - 1):
        char = value[pos]
        if escaped:
            escaped = False
        elif char == "\\" and quote == '"':
            escaped = True
        elif quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == ",":
            parts.append(_scalar(value[start:pos]))
            start = pos + 1
    if quote:
        raise FrontmatterError("unclosed list string")
    tail = value[start:-1].strip()
    if tail:
        parts.append(_scalar(tail))
    return parts


def parse_frontmatter(text: str) -> tuple[Metadata, str]:
    lines = text.lstrip("\ufeff").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text.lstrip("\ufeff")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() in {"---", "..."}), None)
    if end is None:
        raise FrontmatterError("frontmatter has no closing delimiter")
    metadata: Metadata = {}
    active: str | None = None
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if active is None or not isinstance(metadata[active], list):
                raise FrontmatterError("list item has no parent key")
            items = metadata[active]
            assert isinstance(items, list)
            items.append(_scalar(stripped[2:]))
            continue
        match = re.fullmatch(r"([A-Za-z_][\w-]*):(?:\s+(.*)|\s*)", line.rstrip("\r\n"))
        if match is None:
            raise FrontmatterError("expected a flat key: value or list item")
        key, raw = match.group(1).casefold(), match.group(2) or ""
        if key in metadata:
            raise FrontmatterError(f"duplicate frontmatter key: {key}")
        metadata[key] = _value(raw) if raw else []
        active = key
    return metadata, "".join(lines[end + 1 :])


@dataclass(frozen=True)
class Chunk:
    heading: str
    content: str


def _lines_outside_fences(body: str) -> list[tuple[str, bool]]:
    result: list[tuple[str, bool]] = []
    fence_char = ""
    fence_len = 0
    for line in body.splitlines(keepends=True):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        outside = not fence_char
        if match:
            marker, rest = match.groups()
            if not fence_char:
                fence_char, fence_len = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len and not rest.strip():
                fence_char = ""
            outside = False
        result.append((line, outside))
    return result


def chunks_by_heading(body: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading = ""
    current: list[str] = []
    for line, outside in _lines_outside_fences(body):
        match = re.match(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", line) if outside else None
        if match:
            if "".join(current).strip():
                chunks.append(Chunk(heading, "".join(current).strip()))
            heading = match.group(1).strip()
            current = []
        else:
            current.append(line)
    if "".join(current).strip():
        chunks.append(Chunk(heading, "".join(current).strip()))
    return chunks


def scan_markdown(body: str) -> tuple[list[str], list[str], str | None]:
    visible = "".join(line for line, outside in _lines_outside_fences(body) if outside)
    visible = re.sub(r"`+[^`\n]*`+", "", visible)
    links = [
        m.split("|", 1)[0].split("#", 1)[0].strip()
        for m in re.findall(r"\[\[([^\]\n]+)\]\]", visible)
    ]
    tags = re.findall(r"(?<![\w/])#([^\W_][\w/-]*)", visible, flags=re.UNICODE)
    heading = re.search(r"^ {0,3}#\s+(.+?)\s*#*\s*$", visible, flags=re.MULTILINE)
    title = heading.group(1) if heading else None
    return sorted(set(filter(None, links))), sorted(set(tags)), title
