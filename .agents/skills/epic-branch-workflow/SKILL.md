---
name: epic-branch-workflow
description: Use when you need to sync your local feature branch with a team's integration branch or epic branch to prevent or resolve merge conflicts proactively.
---

# Epic Branch & Team Sync Workflow

Use this skill to keep your active feature branch up-to-date with a shared integration branch (e.g., `develop` or an epic branch like `epic/new-ui`) before you push code and create a Merge Request. 

## When to use
* Before finishing a task and pushing your branch to remote.
* When returning to a task after other agents or developers have merged changes.
* Whenever you suspect the integration branch has progressed.

## Steps

### 0. Creating a New Branch (Feature / Fix / Subtask)
Before starting work on a new feature or fix, **ALWAYS** update `main` first and branch off from it:
```bash
# 1. Switch to base branch
git checkout main

# 2. Pull latest upstream changes
git pull origin main

# 3. Create your new branch
git checkout -b feat/<issue-id>-<short-desc>
# Or for bugfixes: git checkout -b fix/<issue-id>-<short-desc>
```

### 1. Identify the Integration Branch
Determine which branch you are targeting for your MR. If unsure, check the user's instructions or the current epic definition. Example: `develop`.

### 2. Fetch Latest Changes
Always ensure your local git tree has the latest remote references:
```bash
git fetch origin
```

### 3. Rebase onto Integration Branch
Rebase your current feature branch on top of the remote integration branch. This prevents cluttered merge commits and keeps the history linear:
```bash
git rebase origin/<integration-branch>
```

### 4. Handle Conflicts (If Any)
If the rebase stops due to conflicts:
1. Stop and read the conflict markers carefully.
2. If the conflicts are complex, refer to the `resolving-merge-conflicts` skill.
3. Resolve the conflicts in the affected files, keeping both intentions intact.
4. Stage the files (`git add <file>`).
5. Continue the rebase (`git rebase --continue`). **Never run `--abort` unless explicitly instructed to roll back.**

### 5. Run Verifications
After a successful rebase (whether conflicts occurred or not):
* Run the automated test suite (e.g., `pytest tests/`).
* Fix any regressions caused by the newly integrated code from the team.

### 6. Push Changes
If you have already pushed this branch previously, you will need to force-push safely:
```bash
git push --force-with-lease origin <your-feature-branch>
```
If this is the first push, a normal `git push -u origin <your-feature-branch>` is sufficient.
