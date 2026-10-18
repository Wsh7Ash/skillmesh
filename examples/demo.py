#!/usr/bin/env python3
"""Offline skillmesh demo.

Analyze two bundled corpora and write the evidence to ``results/``:

    python examples/demo.py

* ``examples/skills``        — deliberately problematic (duplicates, a
                               cross-skill conflict, trigger problems)
* ``examples/skills-clean``  — the repaired version of the same corpus
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from skillmesh.analyze import analyze  # noqa: E402
from skillmesh.parser import load_corpus  # noqa: E402
from skillmesh.report import render_markdown, render_text, to_json  # noqa: E402

RESULTS = os.path.join(ROOT, "results")


def run(name: str, directory: str) -> dict:
    skills = load_corpus(directory)
    analysis = analyze(skills)
    with open(os.path.join(RESULTS, f"report-{name}.txt"), "w", encoding="utf-8") as fh:
        fh.write(render_text(analysis) + "\n")
    with open(os.path.join(RESULTS, f"report-{name}.md"), "w", encoding="utf-8") as fh:
        fh.write(render_markdown(analysis))
    print(
        f"[{name}] skills={len(skills)} tokens={analysis.total_tokens} "
        f"verdict={analysis.verdict} duplicates={len(analysis.duplicates)} "
        f"overlaps={len(analysis.overlaps)} conflicts={len(analysis.conflicts)} "
        f"trigger_issues={len(analysis.trigger_issues)}"
    )
    return analysis.to_dict()


def main() -> int:
    os.makedirs(RESULTS, exist_ok=True)
    summary = {
        "problematic": run("problematic", os.path.join(ROOT, "examples", "skills")),
        "clean": run("clean", os.path.join(ROOT, "examples", "skills-clean")),
    }
    with open(os.path.join(RESULTS, "demo-summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False, sort_keys=True)

    ok = (
        summary["problematic"]["verdict"] in {"CONFLICTS", "REDUNDANT"}
        and summary["problematic"]["conflicts"]
        and summary["problematic"]["duplicates"]
        and summary["clean"]["verdict"] == "CLEAN"
        and not summary["clean"]["conflicts"]
        and not summary["clean"]["duplicates"]
        and not summary["clean"]["trigger_issues"]
    )
    print(f"[done] results/demo-summary.json written; verdicts: "
          f"{summary['problematic']['verdict']} / {summary['clean']['verdict']}")
    print(f"[result] {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())