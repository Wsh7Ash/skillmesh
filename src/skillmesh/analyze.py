"""Corpus analysis: token cost, instruction overlap, conflicts, triggers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from .parser import Skill, directives

WORD_RE = re.compile(r"[a-z0-9']+")

SHINGLE_SIZE = 5


def normalize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def tokens_of(text: str) -> int:
    """Cheap token estimate: ~1.33 tokens per word for English instruction text."""
    words = normalize(text)
    return int(round(len(words) * 1.33))


def shingles(words: list[str], k: int = SHINGLE_SIZE) -> set[str]:
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def instruction_lines(skill: Skill) -> list[tuple[int, str]]:
    """Content-bearing lines (list items / imperative sentences)."""
    out: list[tuple[int, str]] = []
    for line_no, line in skill.body_lines:
        text = line.strip()
        if not text:
            continue
        if text.startswith("#") or text.startswith("```"):
            continue
        if text.startswith(("- ", "* ", "+ ")) or re.match(r"^\d+\.\s", text):
            out.append((line_no, re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", text)))
        elif text.endswith((".", "!", "?", ":")) and len(text.split()) >= 5:
            out.append((line_no, text))
    return out


def line_fingerprint(text: str) -> str:
    joined = "-".join(normalize(text))
    return hashlib.sha1(joined.encode()).hexdigest()[:12]


@dataclass
class DuplicateInstruction:
    fingerprint: str
    text: str
    occurrences: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class OverlapPair:
    a: str
    b: str
    score: float
    shared_shingles: int
    kind: str  # "body" | "section"


@dataclass
class Conflict:
    phrase: str
    positives: list[dict[str, Any]]
    negatives: list[dict[str, Any]]
    prefers: list[dict[str, Any]] = field(default_factory=list)

    @property
    def severity(self) -> str:
        if self.positives and self.negatives:
            return "high"
        return "medium"


@dataclass
class TriggerIssue:
    kind: str  # "missing-trigger" | "overlapping-triggers"
    a: str
    b: str | None
    detail: str


@dataclass
class Analysis:
    skills: list[Skill]
    per_skill_tokens: dict[str, int] = field(default_factory=dict)
    duplicates: list[DuplicateInstruction] = field(default_factory=list)
    overlaps: list[OverlapPair] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    trigger_issues: list[TriggerIssue] = field(default_factory=list)
    parse_warnings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(self.per_skill_tokens.values())

    @property
    def verdict(self) -> str:
        if self.conflicts:
            return "CONFLICTS"
        if self.overlaps or self.duplicates or self.trigger_issues:
            return "REDUNDANT"
        return "CLEAN" if not self.parse_warnings else "WARNINGS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "skills": [s.rel_path for s in self.skills],
            "skill_count": len(self.skills),
            "total_tokens": self.total_tokens,
            "per_skill_tokens": self.per_skill_tokens,
            "duplicates": [
                {"fingerprint": d.fingerprint, "text": d.text, "occurrences": d.occurrences}
                for d in self.duplicates
            ],
            "overlaps": [
                {"a": o.a, "b": o.b, "score": round(o.score, 3), "kind": o.kind}
                for o in self.overlaps
            ],
            "conflicts": [
                {
                    "phrase": c.phrase,
                    "severity": c.severity,
                    "positive": c.positives,
                    "negative": c.negatives,
                    "prefer": c.prefers,
                }
                for c in self.conflicts
            ],
            "trigger_issues": [
                {"kind": t.kind, "a": t.a, "b": t.b, "detail": t.detail}
                for t in self.trigger_issues
            ],
            "parse_warnings": self.parse_warnings,
            "verdict": self.verdict,
        }


def analyze(
    skills: Iterable[Skill],
    *,
    min_overlap: float = 0.35,
    duplicate_threshold: int = 1,
) -> Analysis:
    skills = list(skills)
    analysis = Analysis(skills=skills)

    # --- token cost --------------------------------------------------------
    for skill in skills:
        analysis.per_skill_tokens[skill.rel_path] = tokens_of(skill.raw)
        analysis.parse_warnings.extend(
            {"path": skill.rel_path, "warning": w} for w in skill.parse_warnings
        )

    # --- exact duplicate instructions --------------------------------------
    seen: dict[str, list[dict[str, Any]]] = {}
    for skill in skills:
        for line_no, text in instruction_lines(skill):
            fp = line_fingerprint(text)
            seen.setdefault(fp, []).append(
                {"path": skill.rel_path, "line": line_no, "text": text[:100]}
            )
    for fp, occurrences in seen.items():
        if len(occurrences) >= 2 and duplicate_threshold <= len(occurrences):
            analysis.duplicates.append(
                DuplicateInstruction(
                    fingerprint=fp,
                    text=occurrences[0]["text"],
                    occurrences=occurrences,
                )
            )
    analysis.duplicates.sort(key=lambda d: -len(d.occurrences))

    # --- n-gram overlap, pairwise ------------------------------------------
    shingle_map = {
        s.rel_path: shingles(normalize(s.body)) for s in skills
    }
    section_tokens: dict[tuple[str, str], set[str]] = {}
    for skill in skills:
        for section in skill.sections:
            if section.title == "(preamble)":
                continue
            section_tokens[(skill.rel_path, section.title)] = shingles(
                normalize(section.text)
            )

    names = [s.rel_path for s in skills]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            score = jaccard(shingle_map[a], shingle_map[b])
            if score >= min_overlap:
                shared = len(shingle_map[a] & shingle_map[b])
                analysis.overlaps.append(
                    OverlapPair(a=a, b=b, score=score, shared_shingles=shared, kind="body")
                )
    analysis.overlaps.sort(key=lambda o: -o.score)

    # --- directive conflicts -------------------------------------------------
    all_directives = []
    for skill in skills:
        all_directives.extend(directives(skill))

    by_phrase: dict[str, dict[str, list]] = {}
    seen_order: list[str] = []
    for d in all_directives:
        bucket = by_phrase.setdefault(
            d.phrase_key, {"positive": [], "negative": [], "prefer": []}
        )
        if d.phrase_key not in seen_order:
            seen_order.append(d.phrase_key)
        bucket[d.polarity].append(
            {"path": d.source, "line": d.line, "raw": d.raw, "modal": d.modal}
        )
    for phrase in sorted(by_phrase):
        bucket = by_phrase[phrase]
        if bucket["positive"] and bucket["negative"]:
            analysis.conflicts.append(
                Conflict(
                    phrase=phrase,
                    positives=bucket["positive"],
                    negatives=bucket["negative"],
                    prefers=bucket["prefer"],
                )
            )
        elif bucket["prefer"] and (bucket["positive"] or bucket["negative"]):
            # 'prefer X' vs 'always X'/'never X' is a preference clash, medium
            analysis.conflicts.append(
                Conflict(
                    phrase=phrase,
                    positives=bucket["positive"],
                    negatives=bucket["negative"],
                    prefers=bucket["prefer"],
                )
            )
    analysis.conflicts.sort(key=lambda c: (c.severity != "high", c.phrase))

    # --- trigger analyses ------------------------------------------------------
    analysis.trigger_issues.extend(_trigger_issues(skills))
    return analysis


def _trigger_issues(skills: list[Skill]) -> list[TriggerIssue]:
    issues: list[TriggerIssue] = []
    for skill in skills:
        if not skill.description.strip():
            issues.append(
                TriggerIssue(
                    kind="missing-trigger",
                    a=skill.rel_path,
                    b=None,
                    detail="no description/when in front matter — the agent has no way to know when to load it",
                )
            )
        elif len(skill.description.split()) < 4:
            issues.append(
                TriggerIssue(
                    kind="missing-trigger",
                    a=skill.rel_path,
                    b=None,
                    detail=f"description too short to disambiguate: {skill.description!r}",
                )
            )

    trigger_sets = {
        s.rel_path: set(normalize(s.description)) - STOPWORDISH for s in skills if s.description.strip()
    }
    names = [s.rel_path for s in skills if s.description.strip()]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            inter = trigger_sets[a] & trigger_sets[b]
            union = trigger_sets[a] | trigger_sets[b]
            if not union:
                continue
            score = len(inter) / len(union)
            if score >= 0.6 and len(inter) >= 3:
                issues.append(
                    TriggerIssue(
                        kind="overlapping-triggers",
                        a=a,
                        b=b,
                        detail=(
                            f"descriptions share {sorted(inter)} (Jaccard {score:.0%}) — "
                            "the dispatcher cannot tell them apart"
                        ),
                    )
                )
    return issues


STOPWORDISH = {
    "a", "an", "the", "to", "of", "in", "on", "for", "and", "or", "when",
    "use", "using", "with", "this", "that", "your", "you", "it", "as", "at",
}