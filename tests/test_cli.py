"""CLI end-to-end tests: scan, check, report and their exit codes."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest

from skillmesh.cli import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, main

EXAMPLES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "examples"))
PROBLEMATIC = os.path.join(EXAMPLES, "skills")
CLEAN = os.path.join(EXAMPLES, "skills-clean")


def run_cli(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue() + err.getvalue()


class ScanTests(unittest.TestCase):
    def test_scan_problematic(self) -> None:
        code, out = run_cli("scan", PROBLEMATIC)
        self.assertEqual(code, EXIT_OK, "scan never gates")
        self.assertIn("verdict: CONFLICTS", out)
        self.assertIn("duplicate instructions", out)
        self.assertIn("conflicting directives", out)

    def test_scan_clean(self) -> None:
        code, out = run_cli("scan", CLEAN)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("verdict: CLEAN", out)
        self.assertIn("  none", out)

    def test_scan_json(self) -> None:
        code, out = run_cli("scan", PROBLEMATIC, "--json")
        payload = json.loads(out)
        self.assertEqual(payload["verdict"], "CONFLICTS")
        self.assertTrue(payload["conflicts"])
        self.assertGreaterEqual(payload["total_tokens"], 0)

    def test_scan_markdown(self) -> None:
        code, out = run_cli("scan", PROBLEMATIC, "--markdown")
        self.assertTrue(out.startswith("# skillmesh report"))
        self.assertIn("| `deploy-runbook/SKILL.md` |", out)


class CheckTests(unittest.TestCase):
    def test_check_clean_passes(self) -> None:
        code, _ = run_cli("check", CLEAN)
        self.assertEqual(code, EXIT_OK)

    def test_check_conflict_gates(self) -> None:
        code, out = run_cli("check", PROBLEMATIC, "--fail-on", "conflict")
        self.assertEqual(code, EXIT_FINDINGS)
        self.assertIn("run deploy script", out)

    def test_check_redundancy_gates_on_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "SKILL.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(
                    "---\nname: dup\ndescription: Use when testing duplicate detection here\n---\n"
                    "# Dup\n- Always run the linter before committing code changes.\n"
                )
            other = os.path.join(tmp, "SKILL2.md")
            with open(other, "w", encoding="utf-8") as fh:
                fh.write(
                    "---\nname: dup2\ndescription: Use when testing duplicate detection here\n---\n"
                    "# Dup2\n- Always run the linter before committing code changes.\n"
                )
            code, _ = run_cli("check", tmp, "--fail-on", "redundancy")
            self.assertEqual(code, EXIT_FINDINGS)
            code, _ = run_cli("check", tmp, "--fail-on", "conflict")
            self.assertEqual(code, EXIT_OK, "duplicates are not conflicts")

    def test_check_fail_on_warning(self) -> None:
        code, _ = run_cli("check", PROBLEMATIC, "--fail-on", "warning")
        self.assertEqual(code, EXIT_FINDINGS)

    def test_check_never_never_fails(self) -> None:
        code, _ = run_cli("check", PROBLEMATIC, "--fail-on", "never")
        self.assertEqual(code, EXIT_OK)

    def test_check_json_output(self) -> None:
        code, out = run_cli("check", PROBLEMATIC, "--json")
        payload = json.loads(out)
        self.assertEqual(payload["verdict"], "CONFLICTS")

    def test_min_overlap_flag_changes_findings(self) -> None:
        code_strict, out_strict = run_cli("scan", PROBLEMATIC, "--min-overlap", "0.99", "--json")
        code_zero, out_zero = run_cli("scan", PROBLEMATIC, "--min-overlap", "0", "--json")
        strict = json.loads(out_strict)
        loose = json.loads(out_zero)
        self.assertEqual(strict["overlaps"], [])
        self.assertGreaterEqual(len(loose["overlaps"]), len(strict["overlaps"]))


class ReportTests(unittest.TestCase):
    def test_report_stdout(self) -> None:
        code, out = run_cli("report", CLEAN)
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(out.startswith("# skillmesh report"))
        self.assertIn("CLEAN", out)

    def test_report_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "report.md")
            code, out = run_cli("report", PROBLEMATIC, "-o", target)
            self.assertEqual(code, EXIT_OK)
            with open(target, encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("conflict", content)


class UsageTests(unittest.TestCase):
    def test_missing_path_is_usage_error(self) -> None:
        code, out = run_cli("check", "/no/such/skills")
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("error:", out)

    def test_directory_without_skills_is_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run_cli("scan", tmp)
            self.assertEqual(code, EXIT_USAGE)
            self.assertIn("no skill files", out)

    def test_single_file_path_supported(self) -> None:
        path = os.path.join(CLEAN, "sql-review", "SKILL.md")
        code, out = run_cli("scan", path, "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(json.loads(out)["skill_count"], 1)


if __name__ == "__main__":
    unittest.main()