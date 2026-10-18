---
name: sql-review
---

# SQL review

A skill with no usable trigger: the front matter has a name but no
`description`, so the agent cannot decide when to load it.

- Prefer small migrations that can roll back in one statement.
- Check every index against the actual query plans.