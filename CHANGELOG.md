# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-18

### Added

- `SKILL.md` parser: YAML-subset front matter (quoted values, `|`/`>` block
  scalars), section splitting by heading, absolute line numbers, parse
  warnings instead of hard failures, `SKILL.md`/`*.skill.md` discovery.
- Directive extraction with polarity classification (negative / prefer /
  positive / modal-less list items) and 3-word action keys.
- Corpus analysis: token cost estimate, normalized duplicate-instruction
  fingerprints, pairwise 5-gram body overlap (`--min-overlap`), conflicting
  directives (high: always vs never; medium: prefer vs absolute), trigger
  problems (missing/short description, ambiguous overlapping triggers).
- `skillmesh scan` (report, exit 0), `skillmesh check` (CI gate:
  `--fail-on conflict|redundancy|warning|never`, JSON output),
  `skillmesh report` (markdown, `-o` file).
- Bundled corpora: `examples/skills/` (deliberately problematic) and
  `examples/skills-clean/` (repaired), plus `examples/demo.py` writing
  `results/`.
- 65 tests, CI workflow on Python 3.10/3.12.