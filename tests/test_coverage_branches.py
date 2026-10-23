import contextlib
import io
import json
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from md_context import BudgetError, Index, build_index, build_pack, load_index
from md_context.cli import _cache_dir, _refresh, _root, main
from md_context.ignore import is_ignored
from md_context.index import Chunk, Note
from md_context.parsing import FrontmatterError, _scalar, _uncomment, _value, parse_frontmatter

FIXTURE = Path(__file__).parent / "fixtures" / "vault"


class CoverageBranchesTests(unittest.TestCase):
    def test_ignore_empty_slash_pattern(self):
        self.assertFalse(is_ignored("file.md", ["/"]))
        self.assertFalse(is_ignored("file.md", ["!/"]))

    def test_parsing_edge_branches(self):
        # Comment with escaped quote
        self.assertEqual(_uncomment('key: "val \\" #notacomment"'), 'key: "val \\" #notacomment"')
        # Escaped quote inside inline list
        self.assertEqual(_value('["hello \\"world\\"", "second"]'), ['hello "world"', "second"])
        # Unclosed single quoted string
        with self.assertRaises(FrontmatterError):
            _scalar("'unclosed")
        # Unclosed list string
        with self.assertRaises(FrontmatterError):
            _value("['unclosed, 'bar']")
        # Comments within frontmatter lines
        fm_text = "---\n# leading comment\ntitle: Example\n# trailing comment\n---\nBody\n"
        meta, body = parse_frontmatter(fm_text)
        self.assertEqual(meta["title"], "Example")
        self.assertIn("Body", body)
        # Double quoted string resulting in non-string via mock
        with patch("json.loads", return_value=123):
            with self.assertRaises(FrontmatterError):
                _scalar('"dummy"')

    def test_index_edge_branches(self):
        # Non-directory root in build_index
        with self.assertRaises(ValueError):
            build_index("nonexistent_path_xyz_123")

        # Symlink .mdcontextignore
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / ".mdcontextignore").write_text("test\n", encoding="utf-8")
            with patch("pathlib.Path.is_symlink", return_value=True):
                with self.assertRaises(ValueError) as ctx:
                    build_index(p)
                self.assertIn(".mdcontextignore must not be a symlink", str(ctx.exception))

        # walk_error branch
        with tempfile.TemporaryDirectory() as td:
            with patch("os.walk", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    build_index(td)

        # load_index unsupported version
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            cache_file = p / ".md-context" / "index.json"
            cache_file.parent.mkdir(parents=True)
            cache_file.write_text(json.dumps({"version": 9999}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_index(p)
            self.assertIn("unsupported index version", str(ctx.exception))

        # load_index non-boolean strip_diacritics
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            cache_file = p / ".md-context" / "index.json"
            cache_file.parent.mkdir(parents=True)
            cache_file.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "root": str(p),
                        "strip_diacritics": "yes",
                        "excluded_count": 0,
                        "notes": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                load_index(p)
            self.assertIn("invalid normalization option", str(ctx.exception))

        # _cache_path symlink error
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            with patch("pathlib.Path.is_symlink", return_value=True):
                with self.assertRaises(ValueError) as ctx:
                    load_index(p)
                self.assertIn("index cache must not be a symlink", str(ctx.exception))

    def test_pack_unstable_estimator_branches(self):
        note = Note("test.md", "Test", [], [], "Hello world", [Chunk("Intro", "Hello world")], 1.0)
        idx = Index(Path("."), [note], False, 0)

        # Endless growth in _measure
        call_count = 0

        def exploding_estimator(text: str) -> int:
            nonlocal call_count
            call_count += 1
            return call_count * 100

        with self.assertRaises(ValueError) as ctx:
            build_pack(idx, "Hello", budget=100000, estimator=exploding_estimator)
        self.assertIn("cannot produce a stable output estimate", str(ctx.exception))

        # Post-fitting expansion exceeding budget
        calls = 0

        def unstable_estimator(text: str) -> int:
            nonlocal calls
            calls += 1
            if calls >= 3:
                return 100
            return 20

        with self.assertRaises(BudgetError):
            build_pack(idx, "Hello", budget=50, estimator=unstable_estimator)

    def test_cli_in_process_execution(self):
        with tempfile.TemporaryDirectory() as td:
            cache_dir = Path(td) / "cache"

            # Index command
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(["index", str(FIXTURE), "--cache-dir", str(cache_dir)])
            self.assertEqual(rc, 0)
            data = json.loads(out.getvalue())
            self.assertEqual(data["notes"], 4)

            # Stats command
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(["stats", "--root", str(FIXTURE), "--cache-dir", str(cache_dir)])
            self.assertEqual(rc, 0)
            data = json.loads(out.getvalue())
            self.assertEqual(data["notes"], 4)

            # Query markdown command
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(
                    [
                        "query",
                        "valve",
                        "--root",
                        str(FIXTURE),
                        "--cache-dir",
                        str(cache_dir),
                        "--budget",
                        "4000",
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertIn("## Valve schedule", out.getvalue())

            # Query json command with top and tags
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(
                    [
                        "query",
                        "water",
                        "--root",
                        str(FIXTURE),
                        "--cache-dir",
                        str(cache_dir),
                        "--format",
                        "json",
                        "--top",
                        "2",
                        "--include-tag",
                        "gardening",
                    ]
                )
            self.assertEqual(rc, 0)
            jdata = json.loads(out.getvalue())
            self.assertIn("sources", jdata)

            # Query invalid format
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(["query", "water", "--root", str(FIXTURE), "--format", "csv"])
            self.assertEqual(rc, 2)
            self.assertIn("invalid format", err.getvalue())

            # Query invalid top
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(["query", "water", "--root", str(FIXTURE), "--top", "-1"])
            self.assertEqual(rc, 2)
            self.assertIn("top must be a positive integer", err.getvalue())

            # Missing root error
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(["query", "water", "--root", str(Path(td) / "missing_dir")])
            self.assertEqual(rc, 2)
            self.assertIn("not a directory", err.getvalue())

    def test_cli_helpers_branches(self):
        # _cache_dir with None and env var
        with patch.dict(os.environ, {"MD_CONTEXT_CACHE": "custom/path"}):
            self.assertEqual(_cache_dir(None), Path("custom/path").resolve())
        with patch.dict(os.environ, {"MD_CONTEXT_CACHE": ""}):
            self.assertIsNone(_cache_dir(None))
        self.assertEqual(_cache_dir(Path("explicit")), Path("explicit").resolve())

        # _root with cache_dir containing valid root in index.json
        with tempfile.TemporaryDirectory() as td:
            cache_p = Path(td)
            (cache_p / "index.json").write_text(
                json.dumps({"root": str(FIXTURE)}), encoding="utf-8"
            )
            self.assertEqual(_root(None, cache_dir=cache_p), FIXTURE.resolve())

        # _root with no index raising ValueError
        with tempfile.TemporaryDirectory() as td:
            with patch("pathlib.Path.cwd", return_value=Path(td)):
                with self.assertRaises(ValueError) as ctx:
                    _root(None)
                self.assertIn("no index found", str(ctx.exception))

        # _refresh with existing cache preserving strip_diacritics
        with tempfile.TemporaryDirectory() as td:
            cache_dir = Path(td)
            main(["index", str(FIXTURE), "--cache-dir", str(cache_dir), "--strip-diacritics"])
            idx = _refresh(str(FIXTURE), cache_dir=cache_dir)
            self.assertTrue(idx.strip_diacritics)

    def test_main_module_execution(self):
        with patch("sys.argv", ["md-context", "--version"]):
            with self.assertRaises(SystemExit) as ctx:
                runpy.run_module("md_context.__main__", run_name="__main__")
            self.assertEqual(ctx.exception.code, 0)
