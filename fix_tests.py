import os
import glob

replacements = {
    "test_developer_commands.py": [("app.routers.webhook.", "app.routers.webhook_admin.")],
    "test_devmock.py": [("app.routers.webhook.", "app.routers.webhook_devmock.")],
    "test_manual_targeting.py": [("app.routers.webhook.", "app.routers.webhook_commands.")],
    "test_line_integration.py": [("app.routers.webhook.", "app.routers.webhook_commands.")],
}

test_files = glob.glob("/Users/oatrice/Software Project/FonMaYang/backend/tests/test_*.py")
for file in test_files:
    basename = os.path.basename(file)
    with open(file, "r") as f:
        content = f.read()
    
    if basename in replacements:
        for old, new in replacements[basename]:
            content = content.replace(old, new)
            
    content = content.replace('patch("app.routers.webhook.send_telegram_message"', 'patch("app.services.telegram.send_telegram_message"')
    content = content.replace('patch("app.routers.webhook.send_telegram_message_return_id"', 'patch("app.services.telegram.send_telegram_message_return_id"')
    content = content.replace('patch("app.routers.webhook.edit_telegram_message"', 'patch("app.services.telegram.edit_telegram_message"')
    content = content.replace('patch("app.routers.webhook.answer_callback_query"', 'patch("app.services.telegram.answer_callback_query"')
    content = content.replace('patch("app.routers.webhook.WeatherManager"', 'patch("app.services.weather_manager.WeatherManager"')
    content = content.replace('patch("app.routers.webhook.get_repo_context"', 'patch("app.dependencies.get_repo_context"')
    content = content.replace('patch("app.routers.webhook.DEVELOPER_CHAT_IDS"', 'patch("app.services.telegram.DEVELOPER_CHAT_IDS"')
    content = content.replace('patch("app.routers.webhook.process_telegram_location"', 'patch("app.routers.webhook_location.process_telegram_location"')
    
    with open(file, "w") as f:
        f.write(content)

print("Test patches updated.")
