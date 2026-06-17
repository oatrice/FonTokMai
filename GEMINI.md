# 🔔 Task Completion Notification (Required)

You are connected to an MCP Server named `akasa-remote-approval`.
Whenever you completely finish an assigned task, you **MUST** call the tool `notify_task_complete` as your very last action to notify the user via Telegram.

Do not skip this step, as it lets the user know the outcome without needing to watch the terminal.

### Tool usage parameters:
- **project**: The name of the project you are working on (e.g., "FonMaYang").
- **task**: A concise description of the task that was completed.
- **status**: Use exactly one of the following: 
  - `success` (fully done)
  - `failure` (could not complete)
  - `partial` (done with warnings)
  - `retrying` (failed but attempting again)
  - `limit_reached` (gave up after max retries)
- **duration**: (Optional) How long the task took, e.g., "5m 20s".
- **message**: (Optional) Additional details, summary of what was done, or next steps.

### Example usage:
```json
{
  "project": "FonMaYang",
  "task": "Implement webhook for TMD Radar processing",
  "status": "success",
  "message": "Webhook created and tested successfully. Ready for deployment."
}
```
> ⚙️ **Prerequisite:** Ensure that you use your provided MCP client capabilities to call this tool. Refer to global knowledge (`akasa_backend_url.md`) for the correct backend URL configuration.

# ✏️ Review Pending Notification (For IDE Agents)

If you are generating or editing files and are waiting for the user to Accept / Reject the changes in the editor, you **MUST** call `notify_pending_review` immediately before you stop and wait.

### Tool usage parameters:
- **project**: The name of the project you are working on.
- **task**: What was just implemented or changed.
- **files_changed**: (Optional) List of file paths modified.
- **summary**: (Optional) Short explanation of changes.
