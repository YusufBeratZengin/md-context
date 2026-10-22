import json
import shutil
import unittest
from contextlib import ExitStack
from pathlib import Path

from md_context import build_index, load_index, save_index
from md_context.index import CACHE_DIRECTORY
from tests.support import temporary_directory

FIXTURE = Path(__file__).parent / "fixtures" / "vault"


class IndexTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.root = stack.enter_context(temporary_directory()) / "vault"
        shutil.copytree(FIXTURE, self.root)

    def test_fixture_stats_and_links(self):
        index = build_index(self.root)
        self.assertEqual(index.stats()["notes"], 4)
        self.assertEqual(index.excluded_count, 3)
        orchard = next(n for n in index.notes if n.path == "Orchard.md")
        self.assertEqual(orchard.links, ["Water storage.md"])
        self.assertEqual(orchard.tags, ["gardening", "planning", "water"])
        self.assertEqual(
            [c.heading for c in orchard.chunks],
            ["Orchard irrigation", "Valve schedule", "Maintenance"],
        )

    def test_cache_round_trip_and_privacy(self):
        index = build_index(self.root, strip_diacritics=True)
        path = save_index(index)
        text = path.read_text(encoding="utf-8")
        for sentinel in ["PRIVATE_FIXTURE", "ARCHIVE_FIXTURE", "SCRATCH_FIXTURE", "Private.md"]:
            self.assertNotIn(sentinel, text)
        self.assertEqual(load_index(self.root), index)
        self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_relative_links_and_ambiguous_names(self):
        for folder in ["a", "b"]:
            (self.root / folder).mkdir()
            (self.root / folder / "Same.md").write_text("# Same\ncontent", encoding="utf-8")
        (self.root / "Link.MD").write_text(
            "# Link\n[[Same]] [[a/Same.md|alias]] [[#local]]",
            encoding="utf-8",
        )
        (self.root / "a" / "Other.md").write_text(
            "# Other\n[[../Link]] [[Same]]",
            encoding="utf-8",
        )
        notes = {note.path: note for note in build_index(self.root).notes}
        self.assertEqual(notes["Link.MD"].links, ["a/Same.md"])
        self.assertEqual(notes["a/Other.md"].links, ["Link.MD", "a/Same.md"])

    def test_symlink_notes_and_cache_rejected(self):
        link = self.root / "linked.md"
        try:
            link.symlink_to(self.root / "Recipes.md")
        except OSError:
            self.skipTest("symlinks unavailable on this platform")
        self.assertNotIn("linked.md", [note.path for note in build_index(self.root).notes])
        (self.root / CACHE_DIRECTORY).symlink_to(self.root / "archive", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            save_index(build_index(self.root))

    def test_invalid_cache_and_version(self):
        path = save_index(build_index(self.root))
        path.write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "invalid index"):
            load_index(self.root)
        path.write_text(json.dumps({"version": 999}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "version"):
            load_index(self.root)

    def test_empty_folder(self):
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(build_index(empty).stats()["notes"], 0)

    def test_bad_frontmatter_and_encoding_fail_visibly(self):
        (self.root / "bad.md").write_text("---\nvisibility: private", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "bad.md"):
            build_index(self.root)
        (self.root / "bad.md").write_bytes(b"\xff")
        with self.assertRaises(UnicodeError):
            build_index(self.root)

    def test_iso_date_precedence_and_fallback(self):
        path = self.root / "Dates.md"
        path.write_text("---\nupdated: 2026-01-01T00:00:00Z\ndate: 2020-01-01\n---\nx")
        note = next(n for n in build_index(self.root).notes if n.path == "Dates.md")
        self.assertEqual(note.modified, 1767225600.0)
        path.write_text("---\ndate: invalid\n---\nx")
        note = next(n for n in build_index(self.root).notes if n.path == "Dates.md")
        self.assertEqual(note.modified, path.stat().st_mtime)
