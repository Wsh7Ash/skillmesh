"""Parser tests: front matter, sections, line numbers, directives."""

from __future__ import annotations

import unittest

from skillmesh.parser import (
    SkillParseError,
    classify_directive,
    directives,
    find_skill_files,
    load_corpus,
    parse_front_matter,
    parse_text,
    phrase_key,
    split_sections,
)

BASIC = """---
name: invoice-tie-out
description: Use when reconciling invoices against a bank statement.
---

# Invoice tie-out

## Steps

- Match every invoice to a payment line.
- Never accept a variance above one cent.

## Escalation

Ask the finance lead when two invoices share a number.
"""


class FrontMatterTests(unittest.TestCase):
    def test_basic_front_matter(self) -> None:
        meta, body, warnings = parse_front_matter(BASIC)
        self.assertEqual(meta["name"], "invoice-tie-out")
        self.assertTrue(body.startswith("# Invoice tie-out"))
        self.assertEqual(warnings, [])

    def test_missing_front_matter_warns(self) -> None:
        meta, body, warnings = parse_front_matter("# just markdown\n")
        self.assertEqual(meta, {})
        self.assertTrue(any("front matter" in w for w in warnings))

    def test_block_scalar_multiline_value(self) -> None:
        text = "---\nname: x\ndescription: |\n  line one\n  line two\n---\nbody\n"
        meta, body, _ = parse_front_matter(text)
        self.assertEqual(meta["description"], "line one\nline two")
        self.assertEqual(body.strip(), "body")

    def test_quoted_values_are_unquoted(self) -> None:
        meta, _, _ = parse_front_matter('---\nname: "quoted-name"\n---\n')
        self.assertEqual(meta["name"], "quoted-name")

    def test_duplicate_key_warns(self) -> None:
        meta, _, warnings = parse_front_matter("---\nname: a\nname: b\n---\n")
        self.assertTrue(any("duplicate" in w for w in warnings))

    def test_non_key_value_line_warns(self) -> None:
        _, _, warnings = parse_front_matter("---\njust some text\n---\n")
        self.assertTrue(any("not 'key: value'" in w for w in warnings))

    def test_hash_comment_lines_ignored(self) -> None:
        meta, _, warnings = parse_front_matter("---\n# a comment\nname: ok\n---\n")
        self.assertEqual(meta["name"], "ok")
        self.assertEqual(warnings, [])


class SectionTests(unittest.TestCase):
    def test_headings_split_sections(self) -> None:
        sections = split_sections("# A\n\ntext a\n\n## B\ntext b\n")
        self.assertEqual([s.title for s in sections], ["A", "B"])
        self.assertEqual(sections[1].level, 2)
        self.assertIn("text b", sections[1].text)

    def test_preamble_without_heading(self) -> None:
        sections = split_sections("intro line\n")
        self.assertEqual(sections[0].title, "(preamble)")


class ParseTextTests(unittest.TestCase):
    def test_name_description_and_body(self) -> None:
        skill = parse_text(BASIC, "inv/SKILL.md")
        self.assertEqual(skill.name, "invoice-tie-out")
        self.assertEqual(skill.description, "Use when reconciling invoices against a bank statement.")
        self.assertTrue(skill.has_front_matter)
        self.assertEqual(skill.rel_path, "inv/SKILL.md")
        self.assertEqual(skill.parse_warnings, [])

    def test_line_numbers_account_for_front_matter(self) -> None:
        skill = parse_text(BASIC, "inv/SKILL.md")
        never_line = [n for n, t in skill.body_lines if t.strip().startswith("- Never")][0]
        raw_lines = BASIC.splitlines()
        self.assertEqual(raw_lines[never_line - 1].strip(), "- Never accept a variance above one cent.")

    def test_missing_name_warns(self) -> None:
        skill = parse_text("---\ndescription: Use when testing descriptions only ok\n---\n# x\n", "a.md")
        self.assertIn("name", " ".join(skill.parse_warnings))

    def test_missing_description_warns(self) -> None:
        skill = parse_text("---\nname: x\n---\n# x\nbody\n", "a.md")
        self.assertTrue(any("description" in w for w in skill.parse_warnings))

    def test_description_falls_back_to_when(self) -> None:
        skill = parse_text("---\nname: x\nwhen: Use when the build is red after merge\n---\n", "a.md")
        self.assertEqual(skill.description, "Use when the build is red after merge")


class DiscoveryTests(unittest.TestCase):
    def test_load_corpus_examples(self) -> None:
        import os

        root = os.path.join(os.path.dirname(__file__), "..", "examples", "skills")
        skills = load_corpus(root)
        self.assertGreaterEqual(len(skills), 4)
        self.assertIn("deploy-runbook/SKILL.md", [s.rel_path for s in skills])

    def test_missing_directory_raises(self) -> None:
        with self.assertRaises(SkillParseError):
            load_corpus("/nonexistent/skills/dir")

    def test_directory_without_skill_files_raises(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SkillParseError):
                load_corpus(tmp)


class DirectiveTests(unittest.TestCase):
    def test_positive_negative_and_fallback(self) -> None:
        skill = parse_text(BASIC, "inv/SKILL.md")
        found = {(d.polarity, d.phrase) for d in directives(skill)}
        self.assertIn(("positive", "match invoice payment line"), found)
        self.assertIn(("negative", "accept variance above one cent"), found)

    def test_phrase_key_collapses_wording(self) -> None:
        a = classify_directive("Always run the deploy script with the target environment")
        b = classify_directive("Do not run the deploy script while an incident channel is open")
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertEqual(phrase_key(a[1]), phrase_key(b[1]))
        self.assertEqual(phrase_key(a[1]), "run deploy script")

    def test_non_directive_lines_ignored(self) -> None:
        skill = parse_text(
            "---\nname: x\ndescription: A description long enough for triggers\n---\n"
            "# Heading\nJust prose without a verb modal and too short to be a rule.\n",
            "x.md",
        )
        self.assertEqual(directives(skill), [])

    def test_directive_records_source_and_line(self) -> None:
        skill = parse_text(BASIC, "inv/SKILL.md")
        directive = directives(skill)[0]
        self.assertEqual(directive.source, "inv/SKILL.md")
        self.assertGreater(directive.line, 0)

    def test_prefer_polarity(self) -> None:
        skill = parse_text(
            "---\nname: x\ndescription: A description long enough for triggers here\n---\n"
            "# T\n- Prefer small migrations over schema rewrites.\n",
            "x.md",
        )
        d = directives(skill)[0]
        self.assertEqual(d.polarity, "prefer")


if __name__ == "__main__":
    unittest.main()