import unittest

from md_context.ignore import is_ignored
from md_context.parsing import (
    FrontmatterError,
    chunks_by_heading,
    parse_frontmatter,
    scan_markdown,
)
from md_context.text import normalize, tokenize


class FrontmatterTests(unittest.TestCase):
    def test_supported_values(self):
        metadata, body = parse_frontmatter("""\ufeff---
title: "A: title # literal" # comment
description: 'it''s fine'
tags: [water, "a,b", 'two words']
aliases:
  - "Test"
  - Other
date: 2026-01-01
---
Body
""")
        self.assertEqual(metadata["title"], "A: title # literal")
        self.assertEqual(metadata["description"], "it's fine")
        self.assertEqual(metadata["tags"], ["water", "a,b", "two words"])
        self.assertEqual(metadata["aliases"], ["Test", "Other"])
        self.assertEqual(metadata["date"], "2026-01-01")
        self.assertEqual(body, "Body\n")

    def test_no_frontmatter(self):
        self.assertEqual(parse_frontmatter("# Heading\n---\n"), ({}, "# Heading\n---\n"))

    def test_empty_list_and_terminator(self):
        self.assertEqual(parse_frontmatter("---\ntags: []\n...\ntext"), ({"tags": []}, "text"))

    def test_invalid_frontmatter_fails_closed(self):
        cases = [
            "---\nvisibility: private",
            "---\ntags: [one\n---",
            '---\ntitle: "bad\n---',
            "---\nx: a\nx: b\n---",
            "---\nparent:\n  child: nested\n---",
            "---\nx: |\n---",
            "---\n- orphan\n---",
            "---\nx: &anchor\n---",
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(FrontmatterError):
                parse_frontmatter(case)

    def test_crlf(self):
        self.assertEqual(parse_frontmatter("---\r\ntitle: Test\r\n---\r\nx")[0]["title"], "Test")


class MarkdownTests(unittest.TestCase):
    def test_heading_chunks_preserve_code(self):
        body = "Intro\n# First\nAlpha\n```md\n## Not a heading\n```\n## Second\nBeta\n"
        chunks = chunks_by_heading(body)
        self.assertEqual([chunk.heading for chunk in chunks], ["", "First", "Second"])
        self.assertIn("## Not a heading", chunks[1].content)

    def test_tilde_fences_and_long_closing_fence(self):
        chunks = chunks_by_heading("~~~text\n# Literal\n~~~~\n# Real\ntext")
        self.assertEqual([chunk.heading for chunk in chunks], ["", "Real"])

    def test_tags_and_links_ignore_code(self):
        links, tags, title = scan_markdown(
            "# Title\n[[Folder/Note#Section|label]] #tag/sub #ölçüm\n"
            "`#hidden [[Secret]]`\n```\n#hidden2 [[Secret2]]\n```\n"
        )
        self.assertEqual(links, ["Folder/Note"])
        self.assertEqual(tags, ["tag/sub", "ölçüm"])
        self.assertEqual(title, "Title")

    def test_empty_and_heading_only(self):
        self.assertEqual(chunks_by_heading("# Title\n"), [])
        self.assertEqual(chunks_by_heading(""), [])


class UnicodeTests(unittest.TestCase):
    def test_turkish_case_folding(self):
        self.assertEqual(
            tokenize("I İ ı i IŞIK ışık İSTANBUL"), ["i", "i", "i", "i", "işik", "işik", "istanbul"]
        )

    def test_accents_are_optional(self):
        self.assertEqual(tokenize("café ÖLÇÜM", True), ["cafe", "olcum"])
        self.assertEqual(tokenize("café ÖLÇÜM"), ["café", "ölçüm"])
        self.assertEqual(normalize("cafe\u0301"), normalize("café"))

    def test_multilingual_tokens(self):
        self.assertEqual(tokenize("東京 русский notes_2026"), ["東京", "русский", "notes", "2026"])


class IgnoreTests(unittest.TestCase):
    def test_patterns(self):
        cases = [
            ("archive/a.md", ["archive/"], True),
            ("sub/archive/a.md", ["archive/"], True),
            ("sub/archive/a.md", ["/archive/"], False),
            ("notes/a.md", ["notes/*.md"], True),
            ("notes/sub/a.md", ["notes/*.md"], False),
            ("a.md", ["**/*.md"], True),
            ("notes/sub/a.md", ["**/*.md"], True),
            ("notes/keep.md", ["notes/", "!notes/keep.md"], False),
            ("a.md", ["# comment", "", "b.md"], False),
            ("archive.md", ["archive/"], False),
        ]
        for path, rules, expected in cases:
            with self.subTest(path=path, rules=rules):
                self.assertEqual(is_ignored(path, rules), expected)
