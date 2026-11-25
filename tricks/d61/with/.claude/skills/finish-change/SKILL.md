---
name: finish-change
description: Use when making any code change in this repo, before saying done.
---

Finishing a change in this repo:
1. Find the package the task is about and change its src files only.
2. Build it with pnpm --filter <package> build.
3. Run its tests with pnpm --filter <package> test.
4. If the task names a CLI command, run the built CLI once and check the output.
5. Do not edit or add test files unless the task asks for tests.
6. End with the commands you ran and their results.
