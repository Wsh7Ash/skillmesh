# Results

Honest record of what was actually executed for skillmesh on 2026-10-18.

## Environment

- OS: Windows 11 (MINGW64_NT-10.0-19044, x86_64), MSYS2 MinGW shell
- Runtime: Python 3.14.3 (project venv `.venv/`), pip 25.3
- Dependency manager: pip (`python -m venv .venv` + `.venv/bin/python -m pip install -e .`)
- Network: none — the package performs no network I/O and none was needed

## Validation performed

| Gate | Result | Evidence |
|---|---|---|
| install | **PASS** | venv + `pip install -e .` → exit 0; `.venv/bin/skillmesh --version` → `skillmesh 0.1.0` (system MSYS pip is PEP-668 managed, hence the venv) |
| build | N/A | pure Python, no build step |
| unit tests | **PASS** | `python -m unittest discover -s tests -t .` → `Ran 65 tests … OK`, exit 0 |
| unit tests (warnings as errors) | **PASS** | `python -W error::ResourceWarning -m unittest discover -s tests -t .` → 65 tests OK |
| integration tests | **PASS** | included in the 65: CLI end-to-end on both bundled corpora, temp-corpus fixtures, file output |
| lint | N/A | no linter configured for this repo |
| type check | N/A | no type checker configured; annotations present but not mypy-verified |
| demo run | **PASS** | `python examples/demo.py` → `[result] PASS`, exit 0 |
| CLI gates | **PASS** | `check examples/skills-clean --fail-on warning` → 0; `check examples/skills --fail-on conflict` → 1 (asserted in the test suite and reproduced locally) |
| secret scan | **PASS** | grep for credential/key/token patterns across the tree: only prose in docs matched; no `.env`, no key material |

## Commands executed

```shell
python -m venv .venv
.venv/bin/python -m pip install -e .
python -m unittest discover -s tests -t . -v        # 65 tests, OK, exit 0
python -W error::ResourceWarning -m unittest discover -s tests -t .
.venv/bin/skillmesh --version                        # skillmesh 0.1.0
.venv/bin/skillmesh check examples/skills-clean --fail-on warning   # exit 0
.venv/bin/skillmesh check examples/skills --fail-on conflict        # exit 1
python examples/demo.py                              # exit 0
```

## Observed result

`python examples/demo.py` (offline):

```
[problematic] skills=4 tokens=365 verdict=CONFLICTS duplicates=4 overlaps=1 conflicts=1 trigger_issues=1
[clean] skills=3 tokens=227 verdict=CLEAN duplicates=0 overlaps=0 conflicts=0 trigger_issues=0
[done] results/demo-summary.json written; verdicts: CONFLICTS / CLEAN
[result] PASS
```

The conflict the detector reports on the problematic corpus (from
`results/report-problematic.txt`):

```
## conflicting directives
  [high] about 'run deploy script'
      ALWAYS  deploy-runbook/SKILL.md:12  'Run the deploy script with the target environment as the first flag'
      NEVER   incident-rollback/SKILL.md:7  'Do not run the deploy script while an incident channel is open'
```

and the near-clone pair is reported as an overlapping body
(`deploy-runbook/SKILL.md ~ release-runbook/SKILL.md: 41%`), while the same
checks on `examples/skills-clean/` report zero findings — the repaired corpus
gates clean with `--fail-on warning`.

Behavior proven by tests, not just by the demo:

- front-matter forms (missing, quoted, block scalar, duplicate key) parse or
  warn exactly as documented; reported line numbers match the raw file
- unrelated negatives ("never commit to main" vs "never disable tests") do
  **not** produce a conflict; prefer-vs-always produces a *medium* conflict;
  a self-conflict inside one skill is caught
- `--min-overlap` monotonicity, determinism (two runs → identical JSON)
- CLI: every subcommand, every `--fail-on` level, JSON/markdown output,
  `-o` file output, single-file input, missing-dir and empty-dir errors

## Generated artifacts

- `results/demo-summary.json` — both corpora analyzed as JSON
- `results/report-problematic.txt` / `.md` — full text and markdown reports
- `results/report-clean.txt` / `.md` — the clean-corpus report

Regenerate with `python examples/demo.py`.

## Known limitations

- No linter/type checker ran (none configured). CI covers Python 3.10/3.12;
  this local run used 3.14.3.
- Directive classification is lexical (modal verbs); contradictions phrased
  with no modal and no shared action key are out of scope (documented).
- Token counts are a ~1.33 tokens/word estimate, not a real tokenizer.
- Front matter parsing is a YAML subset: nested structures stay as text.