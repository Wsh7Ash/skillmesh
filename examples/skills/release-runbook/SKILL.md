---
name: release-runbook
description: Use when deploying the service to staging with a release checklist.
---

# Deploy runbook

## Steps

- Always run the linter before committing code changes.
- Never commit directly to main.
- Tag the release with the version from package.json.
- Run the deploy script with the target environment as the first flag.

## Notes

A near-clone of the deploy runbook: same headings, same instruction lines, one
extra rule. skillmesh should report this pair as an overlapping body.