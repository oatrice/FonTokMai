# 📖 Issue Planning Rule
When asked to plan or start a new issue, you **MUST ALWAYS** use the `glab` CLI (e.g., `glab issue view <issue_number>`) to fetch and read the full issue description before creating an `implementation_plan.md` or taking action. 
Do not rely solely on the issue title, your memory, or conversation summaries. If you cannot find the full description, you must explicitly ask the user for it before proceeding.

# 🧪 Test-Driven Development (TDD) Rule
When implementing new features or fixing bugs (especially for backend or core logic), you **MUST** follow a Test-Driven Development (TDD) approach:
1. **Write Tests First:** Before modifying or creating implementation code, write unit tests covering the expected behavior or reproducing the bug.
2. **Verify Failure:** Run the tests to ensure they fail as expected (proving the test is valid and the bug/missing feature exists).
3. **Implement:** Write the minimum code necessary to make the tests pass.
4. **Verify Success:** Run the tests again to confirm they pass and no existing functionality is broken.

# 🔒 Cloud Run Environment Variables Sync Rule
Whenever you introduce, modify, or delete environment variables in the backend configuration (e.g. `.env.example` or code calling `os.getenv()`), you **MUST** update `backend/deploy/deploy_cloudrun.sh` to ensure the new variables are passed to the Cloud Run instances. Always run `pytest backend/tests/test_deploy_env_sync.py` to verify synchronization.

# 🌐 Issue Creation Language & Scope Rule
Whenever asked to create an issue card (e.g. "สร้างการ์ด issue", "create issue"):
1. **DO NOT IMPLEMENT CODE:** Your sole objective is to create the issue card. Do not modify files, run tests, or start implementation.
2. **English Only:** You **MUST ALWAYS** write the issue title and description in **English** (translate from Thai if necessary).
3. **Attach Provided Images:** If the user attached image(s) or screenshot(s) in the prompt, you **MUST** upload them to GitLab (via GitLab API `/uploads`) and embed the uploaded image markdown into the issue description or issue note.
4. **Use Skill:** Follow the format and procedure in `.agents/skills/create-gitlab-issue/SKILL.md`.



# 🚀 Telegram Webhook Latency Rule
Whenever you introduce a new Telegram command handler or inline button callback in `webhook.py`, you **MUST**:
1. Return a `200 OK` (via `{"status": "ok"}`) almost instantly.
2. If the operation is heavy or network-bound (e.g. fetching radar, database ops), offload it using `CloudTasksService().enqueue_task()`.
3. Provide immediate visual feedback to the user (e.g., `send_telegram_message_return_id` with "กำลังประมวลผล...") before enqueuing, and pass `message_id_to_edit` to the worker so it can edit that loading message when done.
4. **DO NOT** use `background_tasks.add_task` directly for heavy operations unless as a strict fallback when `enqueue_task` fails.

# 🌿 Git Branching Strategy Rule
When creating a new branch or submitting a Merge Request (MR) in a multi-agent or team environment, you MUST follow this strict structure:
1. **No Direct Sub-task MR to `main`**: You are strictly **FORBIDDEN** from creating an MR/PR from `subtask/*` or individual task branches directly targeting `main`.
2. **Sub-task Integration Workflow**: You **MUST** switch to the parent feature branch (`git checkout feat/<parent-feature>`), merge the sub-task branch (`git merge subtask/<task-id>`), and run automated tests (`pytest`) until all pass before integrating into the main integration branch.
3. **Target Integration Branch**: Feature branches must be named `feat/<issue-id>-<short-desc>` and MUST target the active integration branch (e.g., `develop` or epic branch). DO NOT target `main` directly unless explicitly instructed.
4. **MR Command Strictness**: When using `glab mr create`, always specify `--target-branch <branch_name>` explicitly.
5. **Skill Compliance**: Use `.agents/skills/subtask-branch-integrator/SKILL.md` for sub-task merges and `epic-branch-workflow` for integration branch rebasing prior to pushing.

# 📋 Manual Verification Artifact Rule
Whenever an Agent Squad or Subagent finishes implementing a feature or completing an MR (Merge Request), you **MUST ALWAYS** generate a `manual_verification.md` file in the worktree/project directory following `.agents/skills/create-manual-verification/SKILL.md`.
1. **Document Verification Steps:** List clear steps, curl/CLI commands, prerequisites, and expected outcomes for happy path and edge cases.
2. **Include in MR Description:** When creating or updating a Merge Request, copy the contents of `manual_verification.md` directly into the MR description body so reviewers have clear steps for manual verification.

# 📝 Documentation & Version Sync Rule (Luma Pattern)
Whenever completing a feature release or significant MR, you **MUST** ensure documentation and version files are synchronized following `.agents/skills/doc-version-updater/SKILL.md`:
1. **Isolated Per-MR Updates**: **DO NOT** update documentation for multiple MRs/branches in a single commit. Each MR/PR branch MUST modify `CHANGELOG.md`, `README.md`, and `VERSION` exclusively for the scope of **that specific MR**.
2. **Changelog Entry**: Add structured entries in `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format (`Added`, `Changed`, `Fixed`, `Security`).
3. **Version Synchronization**: Ensure the version string in `VERSION` (or `package.json`/`pyproject.toml`) strictly matches the latest version header in `CHANGELOG.md`. Release versions MUST move forward incrementally per MR without collisions.
4. **README Alignment**: If new API endpoints, environment variables, or CLI options are added, update `README.md` to reflect the changes.


