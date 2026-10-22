"""Portable gitignore-style matching for .mdcontextignore."""

import fnmatch
from pathlib import PurePosixPath


def _glob(path: str, pattern: str) -> bool:
    """Match path segments; ** alone also consumes zero segments."""
    paths, patterns = path.split("/"), pattern.split("/")

    def match(i: int, j: int) -> bool:
        if j == len(patterns):
            return i == len(paths)
        if patterns[j] == "**":
            return match(i, j + 1) or (i < len(paths) and match(i + 1, j))
        return i < len(paths) and fnmatch.fnmatchcase(paths[i], patterns[j]) and match(i + 1, j + 1)

    return match(0, 0)


def is_ignored(path: str, rules: list[str]) -> bool:
    ignored = False
    parts = PurePosixPath(path).parts
    for raw in rules:
        pattern = raw.strip()
        if not pattern or pattern.startswith("#"):
            continue
        negate = pattern.startswith("!")
        if negate:
            pattern = pattern[1:]
        anchored = pattern.startswith("/")
        directory = pattern.endswith("/")
        pattern = pattern.strip("/")
        if not pattern:
            continue
        candidates = ["/".join(parts[:i]) for i in range(1, len(parts) + (not directory))]
        if "/" in pattern or anchored:
            matched = any(_glob(candidate, pattern) for candidate in candidates)
        else:
            names = parts[:-1] if directory else parts
            matched = any(fnmatch.fnmatchcase(name, pattern) for name in names)
        if matched:
            ignored = not negate
    return ignored
