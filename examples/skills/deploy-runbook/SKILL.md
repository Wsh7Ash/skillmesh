---
name: deploy-runbook
description: Use when deploying the service to staging or production.
---

# Deploy runbook

## Steps

- Always run the linter before committing code changes.
- Never commit directly to main.
- Tag the release with the version from package.json.
- Run the deploy script with the target environment as the first flag.

## Rollback

If the health check fails, roll back to the previous tag and notify the
on-call channel in the incident thread.