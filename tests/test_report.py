"""Renderer tests for text, markdown and JSON output."""

from __future__ import annotations

import json
import os
import unittest

from skillmesh.analyze import analyze
from skillmesh.parser import load_corpus
from skillmesh.report import render_markdown, render_text, to_json

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bad = analyze(load_corpus(os.path.join(EXAMPLES, "skills")))
        cls.good = analyze(load_corpus(os.path.join(EXAMPLES, "skills-clean")))

    def test_text_report_sections(self) -> None:
        out = render_text(self.bad)
        for heading in (
            "skillmesh —",
            "verdict: CONFLICTS",
            "## token cost",
            "## duplicate instructions",
            "## overlapping bodies",
            "## conflicting directives",
            "## trigger problems",
        ):
            self.assertIn(heading, out)

    def test_text_report_shows_always_vs_never(self) -> None:
        out = render_text(self.bad)
        self.assertIn("ALWAYS", out)
        self.assertIn("NEVER", out)
        self.assertIn("run deploy script", out)

    def test_text_report_clean(self) -> None:
        out = render_text(self.good)
        self.assertIn("verdict: CLEAN", out)
        self.assertIn("## conflicting directives\n  none", out)

    def test_markdown_report_shape(self) -> None:
        md = render_markdown(self.bad)
        self.assertTrue(md.startswith("# skillmesh report"))
        self.assertIn("| Skill | Estimated tokens |", md)
        self.assertIn("verdict: **CONFLICTS**", md)

    def test_markdown_clean_corpus_says_no_findings(self) -> None:
        md = render_markdown(self.good)
        self.assertIn("No redundancy, conflict or trigger problems found.", md)

    def test_json_roundtrip(self) -> None:
        payload = json.loads(to_json(self.bad))
        self.assertEqual(payload["verdict"], "CONFLICTS")
        self.assertEqual(payload["skill_count"], 4)
        self.assertIsInstance(payload["trigger_issues"], list)


if __name__ == "__main__":
    unittest.main()