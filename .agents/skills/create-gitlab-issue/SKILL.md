---
name: create-gitlab-issue
description: Create a standardized GitLab issue using glab CLI without executing any code implementation. Trigger when user asks to create an issue, card, or task ticket (e.g. "สร้างการ์ด issue", "สร้าง issue", "create issue").
---

# Create GitLab Issue Skill

Use this skill whenever the user explicitly requests to create an issue, card, or task ticket on GitLab.

## ⚠️ CRITICAL RULE: DO NOT IMPLEMENT
When this skill is triggered, your **ONLY** job is to create the GitLab issue card using `glab`.
- **DO NOT** write, modify, or refactor any project code.
- **DO NOT** run tests, create branches, or execute implementation steps.
- **DO NOT** generate `implementation_plan.md` or start fixing the problem.
- After creating the issue card successfully, report the created issue URL / number to the user and **STOP**.

---

## 📋 Issue Language & Format Guidelines

1. **Title & Description Language**: Must be strictly in **English** (translate if provided in Thai).
2. **Issue Format Standard**:

```markdown
## Overview
<Clear 1-2 sentence description of the feature or bug>

## Problem Statement / Motivation
<Why is this change necessary? What issue or user need does it address?>

## Proposed Solution / Scope
<High-level details of what needs to be implemented or changed>

## Acceptance Criteria
- [ ] <Criterion 1>
- [ ] <Criterion 2>
- [ ] <Criterion 3>

## Technical Notes / Context (Optional)
<Relevant file paths, API endpoints, error logs, or architectural notes if known>
```

---

## 🛠️ Step-by-Step Execution Procedure

1. **Synthesize Details**: Gather the issue requirements from the user's prompt or current context. Translate details to English if needed.
2. **Check for Attached Images**: If the user provided image(s) in their prompt, locate the saved media file in the conversation brain directory (or `/Users/oatrice/.gemini/antigravity/brain/<conv_id>/media_*.jpg`). Upload each file using the GitLab uploads API endpoint (`POST /api/v4/projects/<project_id>/uploads` with Bearer token from `glab` config) to obtain the image markdown URL (e.g. `![alt](/uploads/.../image.jpg)`). Append the markdown to the description or add a note/comment via `glab issue note`.
3. **Prepare Markdown File**: Write the issue description into a temporary file (e.g., `/tmp/issue_desc.md`) to avoid multi-line escaping errors in terminal commands.
4. **Execute `glab issue create`**:
   Run the `glab` CLI command via shell:
   ```bash
   glab issue create --title "<Title in English>" --description-filename "/tmp/issue_desc.md"
   ```
   *(Optionally add labels like `--label "bug"` or `--label "enhancement"` if obvious from context).*
5. **Clean up**: Remove the temporary file `/tmp/issue_desc.md`.
6. **Notify User & STOP**: Return the issue link/ID to the user and state clearly that the issue has been created, and wait for further instructions before taking any implementation action.

