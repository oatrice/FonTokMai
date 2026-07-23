---
name: create-manual-verification
description: Generate a standardized manual_verification.md document in the artifact/worktree directory after an agent squad completes feature implementation and unit testing. Trigger when completing an MR or feature implementation.
---

# Create Manual Verification Document Skill

Use this skill whenever an agent squad or subagent finishes implementing a feature or completing an MR (Merge Request) to document step-by-step manual verification procedures.

---

## 🎯 Purpose
While automated unit tests (`pytest`) verify code logic, a `manual_verification.md` artifact ensures that developers, QA, and reviewers can manually execute, test, and visually verify the changes in a staging or production-like environment (including API endpoints, UI, or CLI).

---

## 📋 Standard Document Template

The generated `manual_verification.md` **MUST** follow this structure:

```markdown
# Manual Verification Plan - [MR Title / Feature Name]

- **Branch**: `[branch-name]`
- **MR / Issue ID**: `[MR # or Issue #]`
- **Date**: `YYYY-MM-DD`

---

## 📌 Prerequisites & Environment Setup
1. List environment variables or DB configs required.
2. Shell commands to launch server locally or in test container.
   ```bash
   # Example
   poetry run uvicorn backend.app.main:app --reload
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: [Name of Primary Happy Path Scenario]
- **Goal**: [What this scenario verifies]
- **Steps**:
  1. Perform action A (e.g. `curl -X POST ...` or click button in UI).
  2. Perform action B.
- **Expected Outcome**:
  - HTTP Status: `200 OK` (or expected state)
  - Response Body / State: `{"status": "success", ...}`
  - Logs/Database: Verify entry created in DB table `xyz`.

---

### Scenario 2: [Edge Case / Failure Mode / Circuit Breaker Scenario]
- **Goal**: [Verify system behavior under error/overdrive/fallback conditions]
- **Steps**:
  1. Simulate API failure or trigger limit condition.
  2. Send request to endpoint.
- **Expected Outcome**:
  - Fallback routine triggered without 500 Server Error.
  - Appropriate warning logs emitted.

---

## 📸 Proof of Verification (Artifacts & Logs)
- **Command Output / Test Logs Snippet**:
  ```text
  [Insert relevant log output or cURL response here]
  ```
- **Automated Verification Summary**:
  - `pytest` result: `288 passed, 4 skipped`
```

---

## 🛠️ Step-by-Step Execution Procedure

1. **Locate Target Directory**: Identify the worktree or project root (e.g., `<worktree_path>/manual_verification.md` or `<appDataDir>/brain/<conversation_id>/manual_verification.md`).
2. **Synthesize Verification Scenarios**: Extract key endpoints, parameters, edge cases, and fallback mechanisms added/modified in the MR.
3. **Generate Document**: Write the markdown content following the standard template.
4. **Copy to PR Description**: If creating/updating a GitLab MR or PR description, ensure the contents of `manual_verification.md` are included in the MR body per `ai_agent_artifact_lifecycle` rules.
