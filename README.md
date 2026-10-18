# skillmesh

**Analyze a collection of agent `SKILL.md` files as one mesh: find duplicated instructions, contradictory directives, overlapping triggers and the token cost every session pays.**

Agent skills (the Markdown instruction packs that coding agents load for a
task) rot the same way documentation does — except a skill's rot silently
changes agent behavior. Two skills give opposite orders about the same action,
three skills repeat the same lint rule (paying for it three times), and two
skills claim the same trigger so the dispatcher cannot tell them apart.

`skillmesh` is the linter for that.

## Key features

- **Duplicate detection** — instruction lines repeated across (or within)
  skills, fingerprinted after normalization, with every occurrence located
  `path:line`.
- **Near-clone detection** — pairwise word 5-gram Jaccard over skill bodies,
  so a renamed copy-paste surfaces even when a line or two drifted.
- **Conflict detection** — directives are classified by polarity
  (`always/must…` vs `never/do not…` vs `prefer…`) and matched by *action key*
  (the first three content words). "Run the deploy script with the target
  environment" vs "Do not run the deploy script while an incident is open" is
  a **high**-severity conflict even though the sentences differ after the verb.
- **Trigger analysis** — skills with no/short `description` (the agent has no
  way to know when to load them) and skill pairs whose descriptions are
  effectively the same (dispatcher ambiguity).
- **Token cost** — per-skill and total estimated tokens of the mesh, so the
  price of "load everything" is visible.
- **CI gating** — `skillmesh check --fail-on conflict|redundancy|warning`
  turns findings into exit codes; `--json`/markdown reports drop into PRs.
- **Zero dependencies**, Python 3.10+ standard library only.

## Example session

```shell
$ skillmesh scan examples/skills
skillmesh — 4 skill(s), 365 estimated tokens in the mesh
verdict: CONFLICTS

## token cost
SKILL                       TOKENS
--------------------------  ------
deploy-runbook/SKILL.md     108
incident-rollback/SKILL.md  104
release-runbook/SKILL.md    90
sql-review/SKILL.md         63

## duplicate instructions
  [4x] 'Always run the linter before committing code changes.'
        deploy-runbook/SKILL.md:9
        incident-rollback/SKILL.md:8
        ...

## overlapping bodies
  deploy-runbook/SKILL.md ~ release-runbook/SKILL.md: 41% (11 shared 5-grams)

## conflicting directives
  [high] about 'run deploy script'
      ALWAYS  deploy-runbook/SKILL.md:12     'Run the deploy script with the target environment as the first flag'
      NEVER   incident-rollback/SKILL.md:7   'Do not run the deploy script while an incident channel is open'

## trigger problems
  [missing-trigger] sql-review/SKILL.md: no description/when in front matter — the agent has no way to know when to load it
```

The same corpus, repaired (`examples/skills-clean/`):

```shell
$ skillmesh check examples/skills-clean; echo $?
verdict: CLEAN
0
```

Run both corpora end-to-end with `python examples/demo.py` (writes `results/`).

## Architecture summary

```
SKILL.md files ─► parser.py ─► Skill(meta, sections, body_lines)
                                     │
                                     ▼
                              analyze.py ──► Analysis
                               │  tokens_of()        per-skill cost
                               │  line fingerprints  duplicates
                               │  5-gram Jaccard     overlapping bodies
                               │  polarity phrases   conflicting directives
                               │  description sets   trigger problems
                                     │
                                     ▼
                              report.py ──► text / markdown / JSON
                                     │
                              cli.py ──► exit codes
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the parsing rules, the
conflict-matching semantics and the safety bounds.

## Requirements

- Python **3.10+**, standard library only. No network access, no state.

## Installation

```shell
git clone https://github.com/Wsh7Ash/skillmesh
cd skillmesh
python -m pip install -e .
skillmesh --version
```

Without installing: `PYTHONPATH=src python -m skillmesh.cli scan DIR`.

## Quick start

```shell
skillmesh scan .github/skills                # what is wrong in my skill pack?
skillmesh check . --fail-on conflict         # gate CI on contradictions only
skillmesh check . --fail-on redundancy       # also gate duplicates + overlap
skillmesh report . -o skillmesh-report.md    # markdown for a PR comment
skillmesh scan . --json | jq '.conflicts'    # machine-readable
```

## Skill format supported

```markdown
---
name: deploy-runbook
description: Use when deploying the service to staging or production.
---

# Deploy runbook

## Steps

- Always run the linter before committing code changes.
- Never commit directly to main.
```

* Front matter: single-level `key: value`, with `|`/`>` block scalars; quoted
  values are unquoted. Recognized keys include `name`, `description`, `when`,
  `allowed-tools`, `license`, `version` (unknown keys are preserved).
* Discovery: any `SKILL.md` or `*.skill.md` under the given directory
  (recursive). Directories named after the skill keep reports readable.
* Target runtime: the Markdown-with-front-matter skill convention used by
  agentic coding tools (Claude Code-style skills, and OpenCode/Freebuff-style
  agent skills). skillmesh itself is runtime-agnostic — it only reads files.

## Testing

```shell
python -m unittest discover -s tests -t . -v
```

65 tests cover the parser (front matter forms, block scalars, warnings,
line-number accuracy, directive extraction), the analysis math (shingles,
Jaccard, fingerprints, conflict keys), both bundled corpora, and the CLI's
exit codes for every gate level.

## Project structure

```
skillmesh/
├─ src/skillmesh/
│  ├─ parser.py     # SKILL.md → Skill(meta, sections, directives)
│  ├─ analyze.py    # tokens, duplicates, overlaps, conflicts, triggers
│  ├─ report.py     # text / markdown / JSON renderers
│  └─ cli.py        # scan / check / report + exit codes
├─ tests/           # 65 unittest cases
├─ examples/
│  ├─ skills/          # deliberately problematic corpus (4 skills)
│  ├─ skills-clean/    # the repaired corpus (3 skills)
│  └─ demo.py          # offline demo → results/
├─ docs/            # ARCHITECTURE.md, USAGE.md
├─ results/         # demo evidence
└─ .github/workflows/ci.yml
```

## Limitations

- Directive classification is lexical: `never`, `always`, `must`, `do not`,
  `prefer` and friends. A contradiction phrased without them ("the deploy
  script is off-limits during incidents") is only caught if the *other* skill
  uses a matching negative modal about the same action key — or via the
  duplicate/overlap paths.
- The action key is the first three content words; two genuinely different
  actions that share a verb phrase ("run deploy script for staging" vs "run
  deploy script for prod") will be reported as one conflict pair — read the
  quoted lines before treating a finding as a bug.
- Token counts are an estimate (~1.33 tokens/word), not a specific tokenizer.
- Front matter parsing is YAML-subset, not a YAML implementation: nested
  mappings and lists are kept as text, not structured.
- No semantic similarity (embeddings): everything here is lexical, on purpose.

## Roadmap

- `skillmesh diff A/ B/` — how a skill pack changed between two revisions.
- Unused-section and stale-date detection (skills referencing versions/dates).
- Policy file: custom modals, per-directory ignore rules, key allowlists.
- Optional `--explain` output that proposes a merged, de-duplicated skill.

## Security notes

skillmesh only reads the files you point it at and prints excerpts of your own
skill content. It performs no network requests and executes no instructions
from the skills it parses. See [docs/USAGE.md](docs/USAGE.md) for the CI
recipe.

## License

[MIT](LICENSE)