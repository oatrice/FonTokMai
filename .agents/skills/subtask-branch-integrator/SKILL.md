---
name: subtask-branch-integrator
description: Enforce strict sub-task branch integration. Prevents creating PRs/MRs from subtask/* directly into main and ensures sub-task branches are merged, rebased, and tested on the parent feature/integration branch first.
---

# Sub-task Branch Integrator Skill

Use this skill whenever working with multi-agent sub-tasks, feature sub-branches, or task-level branches (`subtask/*` or `feat/<task-id>`) before submitting Merge Requests.

---

## 🛑 STRICT RULES & CONSTRAINTS

1. **FORBIDDEN DIRECT MERGE TO `main`**:
   - **NEVER** create a PR or MR from a `subtask/*` or individual sub-issue branch directly targeting `main`.
2. **FEATURE BRANCH INTEGRATION FIRST**:
   - Sub-task branches MUST be merged and integrated into the primary parent feature branch (e.g. `feat/<issue-id>-<desc>` or `develop`) first.
3. **MANDATORY INTEGRATION TESTING**:
   - Run unit tests (`pytest`) on the combined parent feature branch AFTER merging the sub-task, ensuring no regressions occurred.

---

## 🛠️ Step-by-Step Execution Workflow

### Step 1: Verify Current Branch & Target Parent
Check current branch status and verify parent feature branch exists:
```bash
git status
git branch -a
```

### Step 2: Switch to Parent Feature Branch
Checkout the parent feature branch (e.g., `feat/196-197-resiliency` or `develop`):
```bash
git checkout feat/<parent-feature-name>
git pull origin feat/<parent-feature-name>
```

### Step 3: Merge Sub-task Branch into Parent Feature Branch
Merge the completed sub-task branch:
```bash
git merge --no-ff subtask/<task-id>-<desc> -m "feat(subtask): integrate subtask/<task-id> into feat/<parent-feature-name>"
```

### Step 4: Run Verification Suite
Execute backend tests to ensure the integrated code works smoothly without conflicts:
```bash
pytest backend/tests/
```

### Step 5: Sync with Integration/Epic Branch & Push
Use the `epic-branch-workflow` skill to rebase and push the updated parent feature branch:
```bash
git fetch origin
git rebase origin/develop
git push origin feat/<parent-feature-name>
```

### Step 6: Create MR Targeting Integration Branch & Auto-Close Issues
When submitting via `glab`, explicitly specify `--target-branch` and include closing keywords (`Closes #<issue_id>`) in the description:
```bash
glab mr create --target-branch develop --title "feat: <Feature Description>" --description "## 📌 Summary
<description>

## 🔗 Related Issues
- Closes #<issue_id>"
```
