# Contributing

Thanks for helping improve skillmesh.

## Setup

```shell
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -t . -v
python examples/demo.py
```

Standard library only — keep it dependency-free unless a dependency clearly
pays for itself.

## Ground rules

1. **Findings must stay explainable.** Every finding quotes real lines with
   `path:line`; no black-box scoring.
2. **False positives are the real bug.** A linter people disable is worse than
   no linter. Any new detector ships with a negative test proving clean skill
   packs stay quiet.
3. **Determinism.** Same corpus in, same report out — no timestamps, no
   randomness, no network.
4. **Bounded output.** Excerpts and phrases stay capped; reports must stay
   readable in a terminal.

## Adding a detector

1. Add the analysis to `analyze.py` and a section to `report.py`
   (text + markdown + `to_dict`).
2. Add `--fail-on` behavior if it should gate.
3. Tests: positive case on the problematic corpus, negative case on
   `examples/skills-clean/`, and a CLI test for the gate.
4. Update README (feature table + limitations) and CHANGELOG.

## Commit style

Any clear imperative message is fine; reference the issue when there is one.