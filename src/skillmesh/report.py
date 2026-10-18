"""Renderers for skillmesh analyses."""

from __future__ import annotations

import json
from typing import Any

from .analyze import Analysis


def _table(rows: list[tuple[str, ...]]) -> list[str]:
    if not rows:
        return []
    widths = [max(len(r[c]) for r in rows) for c in range(len(rows[0]))]
    out = []
    for idx, row in enumerate(rows):
        out.append("  ".join(cell.ljust(widths[c]) for c, cell in enumerate(row)).rstrip())
        if idx == 0:
            out.append("  ".join("-" * w for w in widths))
    return out


def render_text(a: Analysis) -> str:
    lines = [
        f"skillmesh — {len(a.skills)} skill(s), {a.total_tokens} estimated tokens in the mesh",
        f"verdict: {a.verdict}",
        "",
    ]

    lines.append("## token cost")
    rows = [("SKILL", "TOKENS")] + [
        (path, str(a.per_skill_tokens[path])) for path in sorted(a.per_skill_tokens)
    ]
    lines.extend(_table(rows) or ["(none)"])
    lines.append("")

    lines.append("## duplicate instructions")
    if not a.duplicates:
        lines.append("  none")
    for d in a.duplicates:
        lines.append(f"  [{len(d.occurrences)}x] {d.text!r}")
        for occ in d.occurrences:
            lines.append(f"        {occ['path']}:{occ['line']}")
    lines.append("")

    lines.append("## overlapping bodies")
    if not a.overlaps:
        lines.append("  none")
    for o in a.overlaps:
        lines.append(f"  {o.a} ~ {o.b}: {o.score:.0%} ({o.shared_shingles} shared {SHINGLE}-grams)")
    lines.append("")

    lines.append("## conflicting directives")
    if not a.conflicts:
        lines.append("  none")
    for c in a.conflicts:
        lines.append(f"  [{c.severity}] about {c.phrase!r}")
        for pos in c.positives:
            lines.append(f"      ALWAYS  {pos['path']}:{pos['line']}  {pos['raw']!r}")
        for neg in c.negatives:
            lines.append(f"      NEVER   {neg['path']}:{neg['line']}  {neg['raw']!r}")
        for pref in c.prefers:
            lines.append(f"      PREFER  {pref['path']}:{pref['line']}  {pref['raw']!r}")
    lines.append("")

    lines.append("## trigger problems")
    if not a.trigger_issues:
        lines.append("  none")
    for t in a.trigger_issues:
        other = f" ~ {t.b}" if t.b else ""
        lines.append(f"  [{t.kind}] {t.a}{other}: {t.detail}")
    lines.append("")

    if a.parse_warnings:
        lines.append("## parse warnings")
        for w in a.parse_warnings:
            lines.append(f"  {w['path']}: {w['warning']}")
    return "\n".join(lines)


SHINGLE = 5


def render_markdown(a: Analysis) -> str:
    lines = [
        "# skillmesh report",
        "",
        f"- skills: **{len(a.skills)}**",
        f"- estimated mesh tokens: **{a.total_tokens}**",
        f"- verdict: **{a.verdict}**",
        "",
        "## Token cost",
        "",
        "| Skill | Estimated tokens |",
        "|---|---|",
    ]
    for path in sorted(a.per_skill_tokens):
        lines.append(f"| `{path}` | {a.per_skill_tokens[path]} |")

    lines += ["", "## Findings", ""]
    if not (a.duplicates or a.overlaps or a.conflicts or a.trigger_issues):
        lines.append("No redundancy, conflict or trigger problems found.")
    for d in a.duplicates:
        lines.append(f"- **duplicate** ×{len(d.occurrences)}: {d.text!r}")
        for occ in d.occurrences:
            lines.append(f"  - `{occ['path']}:{occ['line']}`")
    for o in a.overlaps:
        lines.append(f"- **overlap {o.score:.0%}**: `{o.a}` ~ `{o.b}`")
    for c in a.conflicts:
        lines.append(f"- **{c.severity} conflict** about `{c.phrase}`: "
                     f"{len(c.positives)} always-side vs {len(c.negatives)} never-side")
        for pos in c.positives:
            lines.append(f"  - always: `{pos['path']}:{pos['line']}` — {pos['raw']}")
        for neg in c.negatives:
            lines.append(f"  - never: `{neg['path']}:{neg['line']}` — {neg['raw']}")
    for t in a.trigger_issues:
        other = f" ~ `{t.b}`" if t.b else ""
        lines.append(f"- **{t.kind}** `{t.a}`{other}: {t.detail}")
    if a.parse_warnings:
        lines += ["", "## Parse warnings", ""]
        for w in a.parse_warnings:
            lines.append(f"- `{w['path']}`: {w['warning']}")
    return "\n".join(lines) + "\n"


def to_json(payload: Any) -> str:
    if isinstance(payload, Analysis):
        payload = payload.to_dict()
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)