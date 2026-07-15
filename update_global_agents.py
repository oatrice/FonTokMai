import re

with open("/Users/oatrice/.gemini/config/AGENTS.md", "r", encoding="utf-8") as f:
    content = f.read()

# Remove duplicate TDD Rule if it exists
tdd_rule = """# 🧪 Test-Driven Development (TDD) Rule
When implementing new features or fixing bugs (especially for backend or core logic), you **MUST** follow a Test-Driven Development (TDD) approach:
1. **Write Tests First:** Before modifying or creating implementation code, write unit tests covering the expected behavior or reproducing the bug.
2. **Verify Failure:** Run the tests to ensure they fail as expected (proving the test is valid and the bug/missing feature exists).
3. **Implement:** Write the minimum code necessary to make the tests pass.
4. **Verify Success:** Run the tests again to confirm they pass and no existing functionality is broken."""

occurrences = content.count(tdd_rule)
if occurrences > 1:
    # Replace all with empty, then add one back
    content = content.replace(tdd_rule, "").strip() + "\n\n" + tdd_rule + "\n\n"

# Add Global Webhook Rule
global_webhook_rule = """# ⚡ Serverless Webhook Fast Response Rule
When building or modifying webhook endpoints (Telegram, LINE, Slack, Discord, etc.) in a Serverless environment (e.g., Cloud Run, AWS Lambda):
1. **Immediate Acknowledgment:** You **MUST** return a `200 OK` (or equivalent success response) as fast as possible to prevent timeouts and platform retries.
2. **Background Offloading:** Any heavy processing, network requests, or database operations **MUST** be offloaded to an asynchronous task queue (e.g., Cloud Tasks, Pub/Sub, Celery).
3. **Avoid BackgroundTasks:** Do **NOT** rely on lightweight background tasks (like FastAPI's `BackgroundTasks` or standard `asyncio.create_task`) for heavy lifting in Serverless architectures, as CPU resources are throttled immediately after the HTTP response is sent.
4. **User Feedback:** For user-facing bots, immediately send a loading message (e.g., "Processing...") and pass the message ID to the background worker to edit later when the heavy task completes.
"""

if "# ⚡ Serverless Webhook Fast Response Rule" not in content:
    content += global_webhook_rule

with open("/Users/oatrice/.gemini/config/AGENTS.md", "w", encoding="utf-8") as f:
    f.write(content)
