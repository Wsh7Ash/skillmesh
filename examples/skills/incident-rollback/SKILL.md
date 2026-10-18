---
name: incident-rollback
description: Use when rolling back a bad production release during an incident.
---

# Incident rollback

- Do not run the deploy script while an incident channel is open.
- Always run the linter before committing code changes.
- Page the on-call engineer before touching production.

Conflict intent: `deploy-runbook` says "Always run the deploy script with the
target environment", this one says `Do not run the deploy script ...` — same
action, opposite polarity, flagged as a high-severity conflict.