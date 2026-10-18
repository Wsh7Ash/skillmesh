"""SKILL.md parsing.

A *skill file* is a Markdown document with optional YAML-style front matter:

```markdown
---
name: invoice-tie-out
description: Use when reconciling invoices against a bank statement.
---

# Invoice tie-out

## Steps
...
```

The parser is deliberately dependency-free: single-level ``key: value`` pairs,
with ``|`` / ``>`` block scalars supported for multi-line values.  Anything not
front matter is the body, split into sections by Markdown headings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$")

KNOWN_KEYS = ("name", "description", "when", "allowed-tools", "license", "version", "meta")


class SkillParseError(ValueError):
    """Raised when a file cannot be interpreted as a skill at all."""


@dataclass
class Section:
    level: int
    title: str
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()


@dataclass
class Directive:
    """One instruction line, classified by polarity.

    ``polarity`` is ``"positive"``, ``"negative"`` or ``"prefer"`` and
    ``phrase`` is the normalized action the directive talks about.
    ``phrase_key`` (the first three content words) is the key we use to find
    two skills giving opposite orders about the same action even when their
    wording differs after the verb.
    """

    polarity: str
    phrase: str
    phrase_key: str
    raw: str
    line: int
    source: str
    modal: str


@dataclass
class Skill:
    path: Path
    rel_path: str
    raw: str
    meta: dict[str, str] = field(default_factory=dict)
    sections: list[Section] = field(default_factory=list)
    body_lines: list[tuple[int, str]] = field(default_factory=list)  # (line number, text)
    parse_warnings: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.meta.get("name") or self.path.stem

    @property
    def description(self) -> str:
        return self.meta.get("description") or self.meta.get("when") or ""

    @property
    def body(self) -> str:
        return "\n".join(text for _, text in self.body_lines)

    @property
    def has_front_matter(self) -> bool:
        return bool(self.meta)

    @property
    def heading_titles(self) -> list[str]:
        return [s.title for s in self.sections]


def parse_front_matter(text: str) -> tuple[dict[str, str], str, list[str]]:
    """Return ``(meta, body_without_front_matter, warnings)``."""
    warnings: list[str] = []
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text, ["missing front matter (-- name/description)"]

    meta: dict[str, str] = {}
    lines = match.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line[0].isspace():
            warnings.append(f"unexpected indented line outside a block scalar: {line.strip()[:40]!r}")
            i += 1
            continue
        if ":" not in line:
            warnings.append(f"front matter line is not 'key: value': {line.strip()[:40]!r}")
            i += 1
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value in ("|", ">", "|-", ">-"):
            block: list[str] = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i][0].isspace()):
                block.append(lines[i].strip())
                i += 1
            meta[key] = "\n".join(block).strip()
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key in meta:
            warnings.append(f"duplicate front matter key: {key}")
        meta[key] = value
        i += 1

    body = text[match.end():]
    return meta, body, warnings


def split_sections(body: str) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    preamble: list[str] = []
    for line in body.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            if current is not None:
                sections.append(current)
            elif preamble and any(l.strip() for l in preamble):
                sections.append(Section(level=0, title="(preamble)", lines=list(preamble)))
                preamble = []
            current = Section(level=len(heading.group(1)), title=heading.group(2))
            preamble = []
        elif current is not None:
            current.lines.append(line)
        else:
            preamble.append(line)
    if current is not None:
        sections.append(current)
    elif any(l.strip() for l in preamble):
        sections.append(Section(level=0, title="(preamble)", lines=preamble))
    return sections


def numbered_body_lines(body: str, start_line: int) -> list[tuple[int, str]]:
    return [(start_line + i, line) for i, line in enumerate(body.splitlines())]


def parse_text(text: str, rel_path: str = "<memory>", path: Path | None = None) -> Skill:
    meta, body, warnings = parse_front_matter(text)
    match = FRONT_MATTER_RE.match(text)
    if match:
        start_line = text[: match.end()].count("\n") + 1
    else:
        start_line = 1  # body starts on the first line when there is no front matter
    skill = Skill(
        path=path or Path(rel_path),
        rel_path=rel_path,
        raw=text,
        meta=meta,
        sections=split_sections(body),
        body_lines=numbered_body_lines(body, start_line),
        parse_warnings=warnings,
    )
    if "name" not in meta:
        skill.parse_warnings.append("no 'name' in front matter")
    if len(skill.description.split()) < 4:
        skill.parse_warnings.append("description is missing or too short to act as a trigger")
    return skill


def parse_file(path: Path, root: Path | None = None) -> Skill:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = str(path.relative_to(root)) if root else str(path)
    return parse_text(text, rel_path=rel, path=path)


def find_skill_files(directory: Path) -> list[Path]:
    """Every SKILL.md / *.skill.md file under ``directory``, sorted."""
    if directory.is_file():
        return [directory]
    found = [
        p
        for p in directory.rglob("*")
        if p.is_file() and p.suffix == ".md" and (p.name.lower().startswith("skill") or p.name.lower().endswith(".skill.md"))
    ]
    return sorted(found)


def load_corpus(directory: str | Path) -> list[Skill]:
    root = Path(directory)
    if not root.exists():
        raise SkillParseError(f"no such directory or file: {root}")
    files = find_skill_files(root)
    if not files:
        raise SkillParseError(f"no skill files (SKILL.md / *.skill.md) found under {root}")
    return [parse_file(p, root if root.is_dir() else p.parent) for p in files]


def directives(skill: Skill) -> list[Directive]:
    """Extract polarity-tagged directives from a skill body."""
    out: list[Directive] = []
    for line_no, line in skill.body_lines:
        list_match = LIST_ITEM_RE.match(line)
        if not list_match:
            continue
        text = list_match.group(1).strip().rstrip(".!?")
        polarized = classify_directive(text)
        if polarized is None:
            continue
        polarity, phrase = polarized
        if not phrase:
            continue
        modal = _modal_for(text, polarity)
        out.append(
            Directive(
                polarity=polarity,
                phrase=phrase,
                phrase_key=phrase_key(phrase),
                raw=text,
                line=line_no,
                source=skill.rel_path,
                modal=modal,
            )
        )
    return out


NEGATIVE_MODALS = ("never", "do not", "don't", "must not", "avoid", "no longer", "refrain from")
POSITIVE_MODALS = ("always", "must", "need to", "have to", "make sure", "remember to", "shall")
PREFER_MODALS = ("prefer", "rather than", "instead of")


def _modal_for(text: str, polarity: str) -> str:
    lowers = text.lower()
    pool = NEGATIVE_MODALS if polarity == "negative" else (PREFER_MODALS if polarity == "prefer" else POSITIVE_MODALS)
    for modal in pool:
        if modal and modal in lowers:
            return modal
    return ""


def classify_directive(text: str) -> tuple[str, str] | None:
    """Classify a list item as (polarity, normalized phrase), or None.

    Only clearly directive lines are classified: the phrase is everything after
    the modal verb, stop-worded and lowercased so ``"Never open the PR before
    re-running lint"`` and ``"Always open the PR"`` collide.
    """
    lowers = text.lower()
    for modal in NEGATIVE_MODALS:
        idx = lowers.find(modal)
        if idx >= 0:
            phrase = lowers[idx + len(modal):]
            phrase = _normalize_phrase(phrase)
            if phrase:
                return "negative", phrase
    for modal in PREFER_MODALS:
        if not modal:
            continue
        idx = lowers.find(modal)
        if idx >= 0:
            phrase = lowers[idx + len(modal):]
            phrase = _normalize_phrase(phrase)
            if phrase:
                return "prefer", phrase
    for modal in POSITIVE_MODALS:
        idx = lowers.find(modal)
        if idx >= 0:
            phrase = lowers[idx + len(modal):]
            phrase = _normalize_phrase(phrase)
            if phrase:
                return "positive", phrase
    # No modal at all: a list item in a skill body is an instruction, so treat
    # it as positive.  Conflicts only fire on an opposite-polarity match of the
    # same phrase key, which keeps this fallback safe.
    phrase = _normalize_phrase(text)
    if phrase:
        return "positive", phrase
    return None


STOP_WORDS = frozenset(
    """
    a an the to of in on for and or with by at from as it its this that
    be is are was were you your re-run rerun before after when while
    please always never do not dont must make sure remember every
    """.split()
)


def _normalize_phrase(phrase: str) -> str:
    words = re.findall(r"[a-z0-9]+", phrase.lower())
    kept = [w for w in words if w not in STOP_WORDS]
    return " ".join(kept[:8])  # bounded: first 8 content words


def phrase_key(phrase: str, size: int = 3) -> str:
    """Action key used for conflict matching: the first ``size`` content words.

    ``"run the deploy script with the target environment"`` and ``"run the
    deploy script while an incident channel is open"`` share the key
    ``"run deploy script"``, so opposite polarities about that action are
    caught even though the sentences differ afterwards.
    """
    return " ".join(phrase.split()[:size])