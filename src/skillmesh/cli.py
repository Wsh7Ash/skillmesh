"""skillmesh CLI."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__
from .analyze import analyze
from .parser import SkillParseError, load_corpus
from .report import render_markdown, render_text, to_json

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillmesh",
        description="Analyze a collection of agent SKILL.md files as a mesh: "
        "redundancy, contradictory directives, trigger ambiguity, token cost.",
    )
    parser.add_argument("--version", action="version", version=f"skillmesh {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("path", help="directory (or single file) containing SKILL.md files")
        p.add_argument("--min-overlap", type=float, default=0.35,
                       help="body n-gram Jaccard reported at or above this (default 0.35)")

    scan = sub.add_parser("scan", help="full report, exit 0 even with findings")
    common(scan)
    scan.add_argument("--json", action="store_true")
    scan.add_argument("--markdown", action="store_true")

    check = sub.add_parser("check", help="report and gate CI on conflicts/redundancy")
    common(check)
    check.add_argument("--fail-on", choices=["conflict", "redundancy", "warning", "never"],
                       default="conflict", help="gate level (default: conflict)")
    check.add_argument("--json", action="store_true")

    report = sub.add_parser("report", help="markdown report (for PR comments/Wiki)")
    common(report)
    report.add_argument("-o", "--output", help="write to file instead of stdout")
    return parser


def _run(args: argparse.Namespace) -> int:
    skills = load_corpus(args.path)
    analysis = analyze(skills, min_overlap=args.min_overlap)

    if args.command == "scan":
        if args.json:
            print(to_json(analysis))
        elif args.markdown:
            print(render_markdown(analysis), end="")
        else:
            print(render_text(analysis))
        return EXIT_OK

    if args.command == "report":
        text = render_markdown(analysis)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(text)
            print(f"wrote {args.output}")
        else:
            print(text, end="")
        return EXIT_OK

    # check
    if args.json:
        print(to_json(analysis))
    else:
        print(render_text(analysis))
    if args.fail_on == "never":
        return EXIT_OK
    if args.fail_on == "conflict" and analysis.conflicts:
        return EXIT_FINDINGS
    if args.fail_on == "redundancy" and (
        analysis.conflicts
        or analysis.overlaps
        or analysis.duplicates
        or any(t.kind == "overlapping-triggers" for t in analysis.trigger_issues)
    ):
        return EXIT_FINDINGS
    if args.fail_on == "warning" and analysis.verdict != "CLEAN":
        return EXIT_FINDINGS
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        return _run(args)
    except SkillParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE


def entry() -> None:  # pragma: no cover
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover
    entry()