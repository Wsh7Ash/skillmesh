---
name: sql-review
description: Use when reviewing a pull request that changes raw SQL statements.
---

# SQL review

- Prefer small migrations that can roll back in one statement.
- Check every index against the actual query plans.
- Flag any statement that scans a table without a predicate.