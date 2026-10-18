# Architecture

## Goals

1. **One mesh, many files.** A skill is only meaningful relative to the others:
   the unit of analysis is the corpus, not the file.
2. **Lexical honesty.** Every finding points at `path:line` and quotes the
   original text. No embeddings, no hidden heuristics — findings are
   reproducible from the files alone.
3. **Cheap and offline.** Standard library only, no network, no cache; running
   `skillmesh check` twice gives identical output (asserted by test).

## Components

### parser.py — file → `Skill`

`Skill(path, rel_path, raw, meta, sections, body_lines, parse_warnings)`

- **Front matter**: YAML-subset — single-level `key: value`, quoted values,
  `|`/`>` block scalars. Unknown keys are preserved verbatim. Non-conforming
  lines append `parse_warnings` rather than failing the parse (a broken
  description must not hide a broken conflict).
- **Sections**: split on ATX headings; a heading-less preamble becomes a
  `(preamble)` section so its lines are still analyzed.
- **Line numbers**: `numbered_body_lines` records absolute file line numbers
  (computed from the front-matter match offset) so `path:line` findings are
  editor-accurate.
- **Trigger**: `description` (or `when`) with a minimum useful length; a short
  or missing one is a finding, not a crash.

### parser.py — directives

`directives(skill)` walks list items and classifies each with
`classify_directive()`:

| Polarity | Modals (first match wins) |
|---|---|
| negative | `never`, `do not`, `don't`, `must not`, `avoid`, `refrain from` |
| prefer | `prefer`, `rather than`, `instead of` |
| positive | `always`, `must`, `need to`, `have to`, `make sure`, `remember to`, `shall` |
| positive (fallback) | no modal at all — a list item in a skill body is an instruction |

The **phrase** is the modal-stripped remainder, stop-word-filtered and bounded
to the first 8 content words. The **phrase key** is the first 3 content words:
it is what makes "run the deploy script with the target environment" and
"run the deploy script while an incident channel is open" collide as the same
action.

### analyze.py — corpus → `Analysis`

| Check | Mechanism | Notes |
|---|---|---|
| token cost | `tokens_of()` = words × 1.33 | per skill and total |
| duplicates | `line_fingerprint()` = sha1 of normalized words | identical instructions anywhere |
| overlap | 5-gram word shingles + Jaccard, pairwise | `--min-overlap` gate (default 0.35) |
| conflicts | group directives by phrase key, compare polarity buckets | `positive ∧ negative` ⇒ **high**; `prefer` involved ⇒ **medium** |
| triggers | description token sets, Jaccard ≥ 0.6 with ≥ 3 shared | plus missing/short description |

`Analysis.verdict` is the single gate value:
`CONFLICTS > REDUNDANT > WARNINGS > CLEAN` (highest applicable).

Safety bounds: phrases are capped at 8 words, report excerpts at 100 chars,
instruction lines are matched only in list items or full-sentence lines (≥ 5
words), so prose cannot flood the conflict table.

### report.py / cli.py

Pure renderers plus three subcommands:

| Command | Purpose | Exit |
|---|---|---|
| `scan` | full report, never gates | 0 |
| `check` | full report + gate (`--fail-on`) | 0/1 |
| `report` | markdown for PR comments | 0 |
| — | usage errors (`SkillParseError`) | 2 |

## Conflict semantics — worked example

```
deploy-runbook/SKILL.md:12   - Run the deploy script with the target environment as the first flag.
incident-rollback/SKILL.md:7 - Do not run the deploy script while an incident channel is open.
```

1. `classify_directive` → `("positive", "run deploy script target environment first flag")`
   and `("negative", "run deploy script incident channel open")`.
2. `phrase_key` on both → `"run deploy script"`.
3. The bucket for that key holds both polarities ⇒ one `Conflict(severity="high")`
   with both lines quoted.

The same mechanism inside one skill (`- Always …` and `- Do not …` in the same
file) is also a conflict — tested.

## Testing strategy

- **Parser**: front-matter forms (missing, quoted, block scalar, duplicate key,
  comments), section splitting, line-number accuracy against the raw text,
  trigger fallback (`when`), discovery, load errors.
- **Analysis math**: shingle/Jaccard edge cases, fingerprint stability,
  instruction-line filtering (headings and code fences excluded).
- **Corpus behavior**: the bundled problematic corpus must produce its
  duplicates/conflict/trigger issues, the repaired corpus must be `CLEAN`,
  determinism holds, `--min-overlap` monotonicity, no false conflict for
  unrelated negatives, self-conflict within one skill, prefer-vs-always ⇒ medium.
- **CLI**: every subcommand, every `--fail-on` level, JSON/markdown output,
  file output, single-file input, and both error paths (missing dir, dir
  without skills).