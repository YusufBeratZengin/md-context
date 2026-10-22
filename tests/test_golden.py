import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "vault"
GOLDEN = Path(__file__).parent / "golden" / "query-valve.md"


class GoldenTests(unittest.TestCase):
    def test_quickstart_commands_match_golden_and_keep_fixture_clean(self):
        env = {**os.environ, "PYTHONPATH": str(PROJECT / "src"), "PYTHONUTF8": "1"}

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = Path(tmp_dir) / "cache"

            # 1. index command
            cmd_index = [
                sys.executable,
                "-m",
                "md_context",
                "index",
                str(FIXTURE),
                "--cache-dir",
                str(cache_dir),
            ]
            res_index = subprocess.run(
                cmd_index,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(res_index.returncode, 0, res_index.stderr)
            stats_index = json.loads(res_index.stdout)
            self.assertEqual(stats_index["notes"], 4)

            # 2. query command
            cmd_query = [
                sys.executable,
                "-m",
                "md_context",
                "query",
                "valve",
                "--root",
                str(FIXTURE),
                "--cache-dir",
                str(cache_dir),
                "--budget",
                "4000",
            ]
            res_query = subprocess.run(
                cmd_query,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(res_query.returncode, 0, res_query.stderr)

            # Compare exact output to golden file
            golden_text = GOLDEN.read_text(encoding="utf-8")
            # Normalize newlines for cross-platform stability
            actual_norm = res_query.stdout.replace("\r\n", "\n")
            golden_norm = golden_text.replace("\r\n", "\n")
            self.assertEqual(actual_norm, golden_norm)

            # 3. stats command
            cmd_stats = [
                sys.executable,
                "-m",
                "md_context",
                "stats",
                "--root",
                str(FIXTURE),
                "--cache-dir",
                str(cache_dir),
            ]
            res_stats = subprocess.run(
                cmd_stats,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(res_stats.returncode, 0, res_stats.stderr)
            stats_out = json.loads(res_stats.stdout)
            self.assertEqual(stats_out["notes"], 4)

            # Assert fixture directory remained completely clean
            self.assertFalse(
                (FIXTURE / ".md-context").exists(),
                "Running quickstart with --cache-dir polluted tests/fixtures/vault with .md-context",
            )
