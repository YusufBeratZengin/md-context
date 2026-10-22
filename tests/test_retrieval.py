import json
import unittest
from pathlib import Path

from md_context import BudgetError, build_index, build_pack, estimate_tokens, search
from md_context.index import Index, Note
from md_context.parsing import Chunk

FIXTURE = Path(__file__).parent / "fixtures" / "vault"


def note(path, body, *, title="", tags=None, links=None, modified=0):
    return Note(path, title, tags or [], links or [], body, [Chunk("Section", body)], modified)


class RankingTests(unittest.TestCase):
    def test_bm25_relevance(self):
        results = search(build_index(FIXTURE), "irrigation")
        self.assertEqual(results[0].note.path, "Orchard.md")
        self.assertIn("Water storage.md", [r.note.path for r in results])
        self.assertNotIn("Recipes.md", [r.note.path for r in results])

    def test_title_and_tag_boosts(self):
        index = Index(
            Path("."),
            [
                note("body.md", "quartz"),
                note("title.md", "other", title="quartz"),
                note("tag.md", "other", tags=["quartz"]),
            ],
        )
        results = search(index, "quartz", recency_boost=0, neighbor_boost=0)
        self.assertEqual([r.note.path for r in results], ["title.md", "tag.md", "body.md"])

    def test_recency_boost_and_tie_order(self):
        index = Index(Path("."), [note("old.md", "quartz"), note("new.md", "quartz", modified=100)])
        self.assertEqual(search(index, "quartz", now=100)[0].note.path, "new.md")
        self.assertEqual(search(index, "quartz", now=100, recency_boost=0)[0].note.path, "new.md")

    def test_graph_is_one_hop_and_bidirectional(self):
        index = Index(
            Path("."),
            [
                note("a.md", "quartz", links=["b.md"]),
                note("b.md", "other", links=["c.md"]),
                note("c.md", "unrelated"),
                note("d.md", "else", links=["a.md"]),
            ],
        )
        self.assertEqual({r.note.path for r in search(index, "quartz")}, {"a.md", "b.md", "d.md"})
        self.assertEqual(len(search(index, "quartz", neighbor_boost=0)), 1)

    def test_turkish_and_accent_option(self):
        self.assertEqual(search(build_index(FIXTURE), "istanbul IŞIK")[0].note.path, "Unicode.md")
        self.assertEqual(search(build_index(FIXTURE), "cafe"), [])
        self.assertEqual(
            search(build_index(FIXTURE, strip_diacritics=True), "cafe")[0].note.path, "Unicode.md"
        )

    def test_turkish_retrieval_and_stop_punctuation(self):
        notes = [
            note(
                "su_deposu.md",
                "Bahçe için su deposu ve yağmur suyu toplama planı.",
                title="Su deposu",
                tags=["su", "depo"],
            ),
            note(
                "irrigasyon.md",
                "Damlama irrigasyon hattı ve vana kontrolü.",
                title="İrrigasyon",
                tags=["tarim"],
            ),
            note(
                "isik.md",
                "Bahçede ışık ölçümü ve sensör verisi.",
                title="ışık",
                tags=["olcum"],
            ),
        ]
        index = Index(Path("."), notes, strip_diacritics=False)

        # "IŞIK" matches "ışık" without strip_diacritics
        results = search(index, "IŞIK")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].note.path, "isik.md")

        # "isik" does not match "ışık" without strip_diacritics
        self.assertEqual(search(index, "isik"), [])

        # "isik" matches "ışık" with strip_diacritics
        index_stripped = Index(Path("."), notes, strip_diacritics=True)
        results_stripped = search(index_stripped, "isik")
        self.assertEqual(len(results_stripped), 1)
        self.assertEqual(results_stripped[0].note.path, "isik.md")

        # Turkish queries for "Su deposu" and "İrrigasyon"
        self.assertEqual(search(index, "su deposu")[0].note.path, "su_deposu.md")
        self.assertEqual(search(index, "irrigasyon")[0].note.path, "irrigasyon.md")

        # Packs with Turkish terms
        pack_isik = build_pack(index_stripped, "isik", 4000)
        self.assertEqual(len(pack_isik.sources), 1)
        self.assertEqual(pack_isik.sources[0].path, "isik.md")

        pack_upper = build_pack(index, "IŞIK", 4000)
        self.assertEqual(len(pack_upper.sources), 1)
        self.assertEqual(pack_upper.sources[0].path, "isik.md")

        # Query containing only stop punctuation returns empty pack without error
        pack = build_pack(index, "!?. , ;: ---", 4000)
        self.assertEqual(pack.sources, [])
        self.assertEqual(pack.query, "!?. , ;: ---")

    def test_shared_tags_form_one_hop_neighbors_without_self_boost(self):
        index = Index(
            Path("."),
            [
                note("a.md", "quartz", tags=["research"]),
                note("b.md", "other", tags=["research", "planning"]),
                note("c.md", "unrelated", tags=["planning"]),
            ],
        )
        results = search(index, "quartz")
        self.assertEqual({r.note.path for r in results}, {"a.md", "b.md"})
        self.assertEqual(results[0].score, search(index, "quartz", neighbor_boost=0)[0].score)

    def test_empty_queries_and_invalid_boost(self):
        index = build_index(FIXTURE)
        self.assertEqual(search(index, "!!!"), [])
        self.assertEqual(search(index, "nonexistentterm"), [])
        with self.assertRaises(ValueError):
            search(index, "water", title_boost=float("nan"))

    def test_length_normalization(self):
        index = Index(
            Path("."),
            [
                note("short.md", "quartz"),
                note("long.md", "quartz " + "filler " * 100),
            ],
        )
        self.assertEqual(search(index, "quartz")[0].note.path, "short.md")

    def test_include_and_exclude_tag_filters(self):
        index = build_index(FIXTURE)
        results_all = search(index, "water")
        paths = [r.note.path for r in results_all]
        self.assertIn("Orchard.md", paths)
        self.assertIn("Water storage.md", paths)

        # Include tag gardening: only Orchard.md has gardening
        results_inc = search(index, "water", include_tags=["gardening"])
        self.assertEqual([r.note.path for r in results_inc], ["Orchard.md"])

        # Exclude tag gardening: Orchard.md is excluded
        results_exc = search(index, "water", exclude_tags=["gardening"])
        self.assertNotIn("Orchard.md", [r.note.path for r in results_exc])
        self.assertIn("Water storage.md", [r.note.path for r in results_exc])


class PackTests(unittest.TestCase):
    def test_both_formats_fit_many_budgets(self):
        index = build_index(FIXTURE)
        for fmt in ["md", "json"]:
            for budget in [32, 64, 100, 150, 300, 1000, 4000]:
                with self.subTest(fmt=fmt, budget=budget):
                    pack = build_pack(index, "irrigation water", budget, output_format=fmt)
                    self.assertLessEqual(estimate_tokens(pack.render(fmt)), budget)
                    self.assertLessEqual(pack.estimated_tokens, budget)
                    if fmt == "json":
                        self.assertEqual(json.loads(pack.to_json())["budget"], budget)

    def test_source_and_heading_output(self):
        pack = build_pack(build_index(FIXTURE), "valve", 4000)
        self.assertIn("Source: `Orchard.md`", pack.to_markdown())
        self.assertIn("## Valve schedule", pack.to_markdown())
        self.assertTrue(pack.sources)

    def test_top_sections_limit(self):
        index = build_index(FIXTURE)
        pack_all = build_pack(index, "water", 4000)
        self.assertGreater(len(pack_all.sources), 1)
        pack_top1 = build_pack(index, "water", 4000, top=1)
        self.assertEqual(len(pack_top1.sources), 1)

    def test_truncates_large_chunk(self):
        index = Index(Path("."), [note("large.md", "quartz " * 1000)])
        for fmt in ["md", "json"]:
            pack = build_pack(index, "quartz", 150, output_format=fmt)
            self.assertEqual(len(pack.sources), 1)
            self.assertTrue(pack.sources[0].truncated)
            self.assertLessEqual(estimate_tokens(pack.render(fmt)), 150)

    def test_custom_estimator_counts_complete_output(self):
        index = build_index(FIXTURE)
        for fmt in ["md", "json"]:
            pack = build_pack(index, "water", 600, output_format=fmt, estimator=len)
            self.assertLessEqual(len(pack.render(fmt)), 600)
            self.assertLessEqual(len(pack.render(fmt)), pack.estimated_tokens)

    def test_invalid_budgets_and_estimator(self):
        index = build_index(FIXTURE)
        for budget in [0, -1, True]:
            with self.assertRaises(ValueError):
                build_pack(index, "water", budget)
        with self.assertRaises(BudgetError):
            build_pack(index, "water", 1)
        with self.assertRaises(ValueError):
            build_pack(index, "water", estimator=lambda _: -1)
        with self.assertRaises(ValueError):
            build_pack(index, "water", output_format="xml")
        with self.assertRaises(ValueError):
            build_pack(index, "water", top=0)
        with self.assertRaises(ValueError):
            build_pack(index, "water", top=-1)

    def test_custom_estimator_rechecks_json_estimate_digits(self):
        def estimator(text):
            surcharge = 0 if '"estimated_tokens": 200' in text else 9
            return estimate_tokens(text) + surcharge

        pack = build_pack(
            build_index(FIXTURE), "water", 200, output_format="json", estimator=estimator
        )
        self.assertLessEqual(estimator(pack.to_json()), pack.estimated_tokens)
        self.assertLessEqual(estimator(pack.to_json()), 200)

    def test_no_matches_and_empty_vault(self):
        pack = build_pack(Index(Path("."), []), "nothing", 100, output_format="json")
        self.assertEqual(json.loads(pack.to_json())["sources"], [])

    def test_query_envelope_also_consumes_budget(self):
        with self.assertRaises(BudgetError):
            build_pack(build_index(FIXTURE), "x" * 10000, 100)

    def test_heading_relevance_beats_unrelated_section(self):
        text = "quartz " * 10
        n = Note(
            "a.md", "A", [], [], text, [Chunk("Other", "filler " * 100), Chunk("Quartz", text)], 0
        )
        pack = build_pack(Index(Path("."), [n]), "quartz", 80)
        self.assertEqual(pack.sources[0].heading, "Quartz")

    def test_token_rounding(self):
        self.assertEqual([estimate_tokens("x" * n) for n in range(6)], [0, 1, 1, 1, 1, 2])
