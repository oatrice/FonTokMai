import os
import glob

replacements = {
    '"app.routers.webhook_admin.send_telegram_message"': '"app.services.telegram.send_telegram_message"',
    '"app.routers.webhook_admin.send_telegram_document"': '"app.services.telegram.send_telegram_document"',
    '"app.routers.webhook_admin.DEVELOPER_CHAT_IDS"': '"app.services.telegram.DEVELOPER_CHAT_IDS"',
    '"app.routers.webhook_devmock.send_telegram_message"': '"app.services.telegram.send_telegram_message"',
    '"app.routers.webhook_devmock.DEVELOPER_CHAT_IDS"': '"app.services.telegram.DEVELOPER_CHAT_IDS"',
    '"app.routers.webhook_commands.send_telegram_message"': '"app.services.telegram.send_telegram_message"',
    '"app.routers.webhook_commands.WeatherManager"': '"app.services.weather_manager.WeatherManager"',
    '"app.routers.line_webhook.WeatherManager"': '"app.services.weather_manager.WeatherManager"',
    '"app.routers.line_webhook.reply_to_line"': '"app.services.line.reply_to_line"'
}

for filepath in glob.glob("backend/tests/test_*.py"):
    with open(filepath, "r") as f:
        content = f.read()
    
    changed = False
    for old, new in replacements.items():
        if old in content:
            content = content.replace(old, new)
            changed = True
            
    if changed:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"Fixed {filepath}")
