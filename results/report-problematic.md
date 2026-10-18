# skillmesh report

- skills: **4**
- estimated mesh tokens: **365**
- verdict: **CONFLICTS**

## Token cost

| Skill | Estimated tokens |
|---|---|
| `deploy-runbook/SKILL.md` | 96 |
| `incident-rollback/SKILL.md` | 104 |
| `release-runbook/SKILL.md` | 102 |
| `sql-review/SKILL.md` | 63 |

## Findings

- **duplicate** ×3: 'Always run the linter before committing code changes.'
  - `deploy-runbook/SKILL.md:10`
  - `incident-rollback/SKILL.md:9`
  - `release-runbook/SKILL.md:10`
- **duplicate** ×2: 'Never commit directly to main.'
  - `deploy-runbook/SKILL.md:11`
  - `release-runbook/SKILL.md:11`
- **duplicate** ×2: 'Tag the release with the version from package.json.'
  - `deploy-runbook/SKILL.md:12`
  - `release-runbook/SKILL.md:12`
- **duplicate** ×2: 'Run the deploy script with the target environment as the first flag.'
  - `deploy-runbook/SKILL.md:13`
  - `release-runbook/SKILL.md:13`
- **overlap 41%**: `deploy-runbook/SKILL.md` ~ `release-runbook/SKILL.md`
- **high conflict** about `run deploy script`: 2 always-side vs 1 never-side
  - always: `deploy-runbook/SKILL.md:13` — Run the deploy script with the target environment as the first flag
  - always: `release-runbook/SKILL.md:13` — Run the deploy script with the target environment as the first flag
  - never: `incident-rollback/SKILL.md:8` — Do not run the deploy script while an incident channel is open
- **missing-trigger** `sql-review/SKILL.md`: no description/when in front matter — the agent has no way to know when to load it

## Parse warnings

- `sql-review/SKILL.md`: description is missing or too short to act as a trigger
