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
When creating a new branch or submitting a Merge Request (MR) in a multi-agent or team environment, you MUST follow this structure:
1. Feature branches must be named `feat/<issue-id>-<short-desc>`.
2. All feature branches MUST be branched off from and merged into the active integration branch (e.g. `develop` or specific `epic/feature` branch). DO NOT target `main` directly unless explicitly told to do so.
3. When using `glab mr create`, always specify the target branch explicitly using `--target-branch <branch_name>`.
4. Prior to pushing, ALWAYS ensure your branch is up-to-date with the integration branch using the `epic-branch-workflow` skill.
