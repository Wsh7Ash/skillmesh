"""Analysis tests: tokens, duplicates, overlaps, conflicts, triggers."""

from __future__ import annotations

import os
import unittest

from skillmesh.analyze import (
    analyze,
    instruction_lines,
    jaccard,
    line_fingerprint,
    normalize,
    shingles,
    tokens_of,
)
from skillmesh.parser import parse_text

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def skill(body: str, *, name: str = "x", description: str = "Use when testing skill analysis output", path: str | None = None):
    text = f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n{body}\n"
    return parse_text(text, path or f"{name}/SKILL.md")


class MathTests(unittest.TestCase):
    def test_normalize_lowercases_and_splits(self) -> None:
        self.assertEqual(normalize("Hello, World's!"), ["hello", "world's"])

    def test_tokens_estimate(self) -> None:
        words = " ".join(f"word{i}" for i in range(10))
        self.assertEqual(tokens_of(words), 13)

    def test_shingles_short_strings(self) -> None:
        self.assertEqual(shingles(["a", "b"]), {"a b"})
        self.assertEqual(shingles([]), set())

    def test_jaccard(self) -> None:
        self.assertEqual(jaccard({"a", "b"}, {"a", "b"}), 1.0)
        self.assertEqual(jaccard({"a"}, {"b"}), 0.0)
        self.assertEqual(jaccard(set(), {"a"}), 0.0)

    def test_line_fingerprint_stable_ignores_punct_and_case(self) -> None:
        a = line_fingerprint("Always run the linter, before committing!")
        b = line_fingerprint("always RUN the linter before committing")
        self.assertEqual(a, b)

    def test_instruction_lines_skip_headings_and_code(self) -> None:
        s = skill("- Always run tests.\n# Heading\n```\ncode line here runs\n```\n")
        lines = [t for _, t in instruction_lines(s)]
        self.assertEqual(lines, ["Always run tests."])


class CorpusAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from skillmesh.parser import load_corpus

        cls.bad = load_corpus(os.path.join(EXAMPLES, "skills"))
        cls.good = load_corpus(os.path.join(EXAMPLES, "skills-clean"))

    def test_problematic_corpus_has_duplicates(self) -> None:
        analysis = analyze(self.bad)
        self.assertTrue(analysis.duplicates)
        top = analysis.duplicates[0]
        self.assertGreaterEqual(len(top.occurrences), 2)
        self.assertTrue(all("path" in o and "line" in o for o in top.occurrences))

    def test_problematic_corpus_has_conflict(self) -> None:
        analysis = analyze(self.bad)
        self.assertTrue(analysis.conflicts)
        conflict = analysis.conflicts[0]
        self.assertEqual(conflict.severity, "high")
        self.assertTrue(conflict.positives)
        self.assertTrue(conflict.negatives)
        self.assertIn("run deploy script", conflict.phrase)

    def test_problematic_corpus_reports_missing_trigger(self) -> None:
        analysis = analyze(self.bad)
        kinds = {t.kind for t in analysis.trigger_issues}
        self.assertIn("missing-trigger", kinds)

    def test_problematic_corpus_verdict(self) -> None:
        self.assertEqual(analyze(self.bad).verdict, "CONFLICTS")

    def test_clean_corpus_is_clean(self) -> None:
        analysis = analyze(self.good)
        self.assertEqual(analysis.verdict, "CLEAN")
        self.assertEqual(analysis.conflicts, [])
        self.assertEqual(analysis.duplicates, [])
        self.assertEqual(analysis.overlaps, [])
        self.assertEqual(analysis.trigger_issues, [])

    def test_token_totals(self) -> None:
        analysis = analyze(self.good)
        self.assertGreater(analysis.total_tokens, 0)
        self.assertEqual(
            analysis.total_tokens, sum(analysis.per_skill_tokens.values())
        )

    def test_near_clone_pair_is_overlapping(self) -> None:
        analysis = analyze(self.bad)  # default 0.35 threshold
        pairs = {(o.a, o.b) for o in analysis.overlaps}
        self.assertIn(("deploy-runbook/SKILL.md", "release-runbook/SKILL.md"), pairs)
        score = [o for o in analysis.overlaps if o.a.startswith("deploy")][0].score
        self.assertGreaterEqual(score, 0.35)
        self.assertGreater([o for o in analysis.overlaps if o.a.startswith("deploy")][0].shared_shingles, 0)

    def test_min_overlap_threshold_respected(self) -> None:
        loose = analyze(self.bad, min_overlap=0.0)
        strict = analyze(self.bad, min_overlap=0.99)
        self.assertGreaterEqual(len(loose.overlaps), len(strict.overlaps))
        self.assertEqual(strict.overlaps, [])

    def test_overlapping_triggers_detected(self) -> None:
        a = skill("- Run the tests.", name="one", description="Use when deploying the service to staging")
        b = skill("- Run the lint.", name="two", description="Use when deploying the service to staging")
        analysis = analyze([a, b])
        self.assertEqual([t.kind for t in analysis.trigger_issues], ["overlapping-triggers"])

    def test_self_conflict_within_one_skill(self) -> None:
        s = skill(
            "- Always run the deploy script with the target environment first.\n"
            "- Do not run the deploy script while an incident channel is open.\n",
            name="selfclash",
        )
        analysis = analyze([s])
        self.assertEqual(len(analysis.conflicts), 1)
        self.assertEqual(analysis.conflicts[0].severity, "high")

    def test_prefer_clash_is_medium(self) -> None:
        a = skill("- Always run the deploy script first thing.\n", name="one")
        b = skill("- Prefer run the deploy script only after review.\n", name="two")
        analysis = analyze([a, b])
        self.assertEqual(len(analysis.conflicts), 1)
        self.assertEqual(analysis.conflicts[0].severity, "medium")

    def test_no_false_conflict_for_unrelated_negatives(self) -> None:
        a = skill("- Never commit directly to main.\n", name="one")
        b = skill("- Never disable the test suite.\n", name="two")
        self.assertEqual(analyze([a, b]).conflicts, [])

    def test_parse_warnings_surface(self) -> None:
        s = parse_text("---\nname: x\n---\n# x\nbody\n", "x/SKILL.md")
        analysis = analyze([s])
        self.assertTrue(any(w["path"] == "x/SKILL.md" for w in analysis.parse_warnings))

    def test_to_dict_is_json_ready(self) -> None:
        import json

        payload = analyze(self.bad).to_dict()
        json.dumps(payload)
        self.assertEqual(payload["skill_count"], len(self.bad))
        self.assertIn(payload["verdict"], {"CLEAN", "REDUNDANT", "CONFLICTS", "WARNINGS"})

    def test_analysis_is_deterministic(self) -> None:
        first = analyze(self.bad).to_dict()
        second = analyze(self.bad).to_dict()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()