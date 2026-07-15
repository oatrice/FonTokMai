import re

with open("backend/app/routers/worker.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add message_id_to_edit to CommandPayload
content = content.replace(
    "    show_advanced: bool = False",
    "    show_advanced: bool = False\n    message_id_to_edit: Optional[int] = None"
)

# Update handle-rain
content = content.replace(
    "await handle_rain_command(payload.chat_id, payload.command, payload.show_advanced)",
    "await handle_rain_command(payload.chat_id, payload.command, payload.show_advanced, payload.message_id_to_edit)"
)

# Update handle-devmock
content = content.replace(
    "await handle_devmock_command(payload.chat_id, payload.command)",
    "await handle_devmock_command(payload.chat_id, payload.command, payload.username, payload.message_id_to_edit)"
)

# Update AdminCommandPayload (which we added previously)
content = content.replace(
    "    username: str = \"\"",
    "    username: str = \"\"\n    message_id_to_edit: Optional[int] = None"
)

# Update handle-metrics
content = content.replace(
    "await handle_metrics_command(payload.chat_id, payload.command, payload.username)",
    "await handle_metrics_command(payload.chat_id, payload.command, payload.username, payload.message_id_to_edit)"
)

# Update handle-setbudget
content = content.replace(
    "await handle_setbudget_command(payload.chat_id, payload.command, payload.username)",
    "await handle_setbudget_command(payload.chat_id, payload.command, payload.username, payload.message_id_to_edit)"
)

# Update handle-tmd-fallback
content = content.replace(
    "await handle_tmd_fallback_command(payload.chat_id, payload.command, payload.username)",
    "await handle_tmd_fallback_command(payload.chat_id, payload.command, payload.username, payload.message_id_to_edit)"
)

with open("backend/app/routers/worker.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated worker.py")
