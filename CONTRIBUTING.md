# Contributing

Use Python 3.10 or newer. Runtime code must use only the standard library. Keep
examples and fixture notes fictional; do not include personal information or keys.

```sh
python -m venv .venv
# Activate .venv using your shell's activation command.
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

Without a package install, set `PYTHONPATH=src` before running unittest. Test
temporary files are confined to `is/test-tmp/`, which is ignored by Git.

Open an issue at
[YusufBeratZengin/md-context](https://github.com/YusufBeratZengin/md-context/issues)
for a bug or substantial proposal. Include a minimal synthetic reproduction,
Python version, operating system, command, and expected result. Never attach a
real vault or generated cache.

For a pull request, keep changes focused, explain the behavior and validation,
and add regression coverage for behavior changes. Update the English and Turkish
READMEs when user-facing behavior changes, and add a changelog entry. Preserve
stable ordering, cross-platform paths, privacy exclusions, and complete-output
budget accounting. Do not silently broaden the supported frontmatter subset.

Use small Conventional Commits in English, for example
`fix: exclude newly private notes during refresh`. Run the checks above before
submitting. CI covers Ubuntu and Windows on Python 3.10 and 3.14. Security concerns
belong in the private reporting process described in [SECURITY.md](SECURITY.md).
