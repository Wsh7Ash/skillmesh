# Usage

Exit codes: `0` ok, `1` findings at/above the gate (`check` only), `2` usage error.

## scan

```shell
skillmesh scan DIR                     # full human-readable report
skillmesh scan DIR --json              # machine-readable
skillmesh scan DIR --markdown          # markdown report to stdout
skillmesh scan path/to/SKILL.md        # single file works too
skillmesh scan DIR --min-overlap 0.2   # report near-clones more eagerly
```

`scan` always exits 0 — it is the exploration command. Findings:

- **duplicate instructions** — same instruction (by normalized fingerprint)
  in several places, listed with `path:line`
- **overlapping bodies** — pairwise 5-gram Jaccard at/above `--min-overlap`
  (default 0.35)
- **conflicting directives** — `ALWAYS` vs `NEVER` about the same action key
  (high), or `PREFER` clashing with an absolute (medium)
- **trigger problems** — missing/short `description`, or two skills whose
  descriptions the dispatcher cannot tell apart
- **parse warnings** — front matter irregularities (missing `name`, duplicates…)

## check

```shell
skillmesh check DIR                            # gate: conflicts (default)
skillmesh check DIR --fail-on redundancy       # also duplicates + overlaps + ambiguous triggers
skillmesh check DIR --fail-on warning          # gate on anything at all
skillmesh check DIR --fail-on never            # report only, always exit 0
skillmesh check DIR --json > skillmesh.json
```

### CI example

```yaml
- name: Skill pack lint
  run: |
    pip install -e .
    skillmesh check .github/skills --fail-on conflict --json > skillmesh.json
- uses: actions/upload-artifact@v4
  with: { name: skillmesh-report, path: skillmesh.json }
```

## report

```shell
skillmesh report DIR                     # markdown to stdout
skillmesh report DIR -o skillmesh-report.md
```

Paste the markdown into a PR comment when a skill-pack change introduces
duplication or contradictions.

## Typical workflows

**Before adding a new skill**

```shell
skillmesh check .skills/ --fail-on redundancy
skillmesh scan .skills/ --min-overlap 0.2 | less
```

**Quarterly skill-pack hygiene**

```shell
skillmesh report .skills/ -o docs/skill-mesh-review.md
```

**Refactor: merge two overlapping skills**

```shell
skillmesh scan .skills/ --json | jq '.overlaps'
# merge the near-clone, re-run: verdict should move toward CLEAN
skillmesh check .skills/ --fail-on warning
```

## Notes

- skillmesh reads only the paths you name, makes no network requests, and
  never executes the instructions it parses — parsing is purely textual.
- Findings quote your own skill content; treat reports like the repository
  they came from when sharing.
- Token counts are an estimate; use them for comparisons, not billing.