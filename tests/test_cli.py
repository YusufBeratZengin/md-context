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

    def run_cli(self, *args, cwd=None):
        env = {**os.environ, "PYTHONPATH": str(PROJECT / "src"), "PYTHONUTF8": "1"}
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
