import json
import os
import shutil
import subprocess
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from md_context import estimate_tokens
from tests.support import temporary_directory

PROJECT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "vault"


class CliTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.root = stack.enter_context(temporary_directory()) / "vault"
        shutil.copytree(FIXTURE, self.root)

    def run_cli(self, *args, cwd=None, extra_env=None):
        env = {**os.environ, "PYTHONPATH": str(PROJECT / "src"), "PYTHONUTF8": "1"}
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, "-m", "md_context", *args],
            cwd=cwd or self.root,
            env=env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

    def test_index_query_and_stats(self):
        result = self.run_cli("index", str(self.root), "--strip-diacritics")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["notes"], 4)
        result = self.run_cli("query", "cafe", "--budget", "300", "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["sources"][0]["path"], "Unicode.md")
        result = self.run_cli("stats")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["strip_diacritics"])

    def test_auto_discovery_from_nested_directory(self):
        self.run_cli("index", str(self.root))
        result = self.run_cli("query", "water", cwd=self.root / "archive")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Source:", result.stdout)

    def test_explicit_root_without_existing_index(self):
        result = self.run_cli("query", "water", "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Orchard.md", result.stdout)

    def test_refresh_excludes_newly_private_and_ignored(self):
        self.run_cli("index", str(self.root))
        (self.root / "Orchard.md").write_text(
            "---\nvisibility: private\n---\nORCHARD_NEW_SECRET water",
            encoding="utf-8",
        )
        (self.root / ".mdcontextignore").write_text("Water storage.md\n", encoding="utf-8")
        result = self.run_cli("query", "water", "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("ORCHARD_NEW_SECRET", result.stdout)
        self.assertNotIn("Orchard.md", result.stdout)
        self.assertNotIn("Water storage.md", result.stdout)
        cache = (self.root / ".md-context" / "index.json").read_text(encoding="utf-8")
        self.assertNotIn("ORCHARD_NEW_SECRET", cache)

    def test_missing_index_and_invalid_budget_errors(self):
        result = self.run_cli("stats")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no index found", result.stderr)
        result = self.run_cli("query", "water", "--root", str(self.root), "--budget", "1")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("budget", result.stderr)

    def test_version_and_bad_path(self):
        self.assertEqual(self.run_cli("--version").stdout.strip(), "0.1.0")
        result = self.run_cli("index", str(self.root / "missing"))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_cache_dir_flag_and_env(self):
        cache_dir = self.root.parent / "custom_cache"
        result = self.run_cli("index", str(self.root), "--cache-dir", str(cache_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((cache_dir / "index.json").is_file())
        self.assertFalse((self.root / ".md-context").exists())

        result = self.run_cli(
            "query", "water", "--root", str(self.root), "--cache-dir", str(cache_dir)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Orchard.md", result.stdout)
        self.assertFalse((self.root / ".md-context").exists())

        result = self.run_cli("stats", "--root", str(self.root), "--cache-dir", str(cache_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["notes"], 4)

        env_cache = self.root.parent / "env_cache"
        result = self.run_cli(
            "index", str(self.root), extra_env={"MD_CONTEXT_CACHE": str(env_cache)}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((env_cache / "index.json").is_file())
        self.assertFalse((self.root / ".md-context").exists())

    def test_query_top_and_tag_filters(self):
        result = self.run_cli(
            "query", "water", "--root", str(self.root), "--top", "1", "--format", "json"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(len(data["sources"]), 1)

        result_invalid_top = self.run_cli("query", "water", "--root", str(self.root), "--top", "0")
        self.assertEqual(result_invalid_top.returncode, 2)
        self.assertIn("top", result_invalid_top.stderr)

        result_inc = self.run_cli(
            "query",
            "water",
            "--root",
            str(self.root),
            "--include-tag",
            "gardening",
            "--format",
            "json",
        )
        self.assertEqual(result_inc.returncode, 0, result_inc.stderr)
        sources_inc = json.loads(result_inc.stdout)["sources"]
        self.assertTrue(sources_inc)
        self.assertTrue(all(s["path"] == "Orchard.md" for s in sources_inc))

        result_exc = self.run_cli(
            "query",
            "water",
            "--root",
            str(self.root),
            "--exclude-tag",
            "gardening",
            "--format",
            "json",
        )
        self.assertEqual(result_exc.returncode, 0, result_exc.stderr)
        sources_exc = json.loads(result_exc.stdout)["sources"]
        self.assertTrue(sources_exc)
        self.assertFalse(any(s["path"] == "Orchard.md" for s in sources_exc))

    def test_invalid_format_error(self):
        result = self.run_cli("query", "water", "--root", str(self.root), "--format", "xml")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid format", result.stderr)
        self.assertIn("md", result.stderr)
        self.assertIn("json", result.stderr)

    def test_missing_root_error(self):
        result = self.run_cli("query", "water", "--root", str(self.root / "nonexistent"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a directory", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

        result_stats = self.run_cli("stats", "--root", str(self.root / "nonexistent"))
        self.assertEqual(result_stats.returncode, 2)
        self.assertIn("not a directory", result_stats.stderr)
        self.assertNotIn("Traceback", result_stats.stderr)

    def test_empty_folder_emits_empty_pack(self):
        empty_dir = self.root.parent / "empty_vault"
        empty_dir.mkdir()
        result = self.run_cli("query", "anything", "--root", str(empty_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Query: anything", result.stdout)
        self.assertNotIn("## ", result.stdout)

        result_json = self.run_cli(
            "query", "anything", "--root", str(empty_dir), "--format", "json"
        )
        self.assertEqual(result_json.returncode, 0, result_json.stderr)
        self.assertEqual(json.loads(result_json.stdout)["sources"], [])

        result_stats = self.run_cli("stats", "--root", str(empty_dir))
        self.assertEqual(result_stats.returncode, 0, result_stats.stderr)
        self.assertEqual(json.loads(result_stats.stdout)["notes"], 0)

    def test_corrupt_index_fails_without_traceback(self):
        cache_file = self.root / ".md-context" / "index.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("{corrupted JSON content", encoding="utf-8")

        result_stats = self.run_cli("stats", "--root", str(self.root))
        self.assertEqual(result_stats.returncode, 2)
        self.assertIn("invalid index cache", result_stats.stderr)
        self.assertNotIn("Traceback", result_stats.stderr)

        result_query = self.run_cli("query", "water", "--root", str(self.root))
        self.assertEqual(result_query.returncode, 2)
        self.assertIn("invalid index cache", result_query.stderr)
        self.assertNotIn("Traceback", result_query.stderr)

    def test_non_utf8_note_includes_filename_in_error(self):
        (self.root / "corrupt_encoding.md").write_bytes(b"\xff\xfe\x00")
        result = self.run_cli("query", "water", "--root", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("corrupt_encoding.md", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_utf8_lf_bytes_obey_budget_on_windows_too(self):
        env = {**os.environ, "PYTHONPATH": str(PROJECT / "src"), "PYTHONUTF8": "0"}
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "md_context",
                "query",
                "ışık",
                "--budget",
                "200",
                "--format",
                "json",
                "--root",
                str(self.root),
            ],
            env=env,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(b"\r\n", result.stdout)
        output = result.stdout.decode("utf-8")
        self.assertLessEqual(estimate_tokens(output), 200)
        self.assertIn("Unicode.md", output)
