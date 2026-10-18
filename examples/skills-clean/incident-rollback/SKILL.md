---
name: incident-rollback
description: Use when undoing a production release after an alert fires.
---

# Incident rollback

- Halt the deploy pipeline while an incident channel is open.
- Page the on-call engineer before touching production.
- Replay the failed health check once traffic is stable again.