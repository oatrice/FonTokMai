import os
import re

ROUTER_FILES = [
    "backend/app/routers/webhook_admin.py",
    "backend/app/routers/webhook_callbacks.py",
    "backend/app/routers/webhook_commands.py",
    "backend/app/routers/webhook_devmock.py",
    "backend/app/routers/webhook_location.py",
    "backend/app/routers/webhook_utils.py",
]

for filepath in ROUTER_FILES:
    if not os.path.exists(filepath):
        continue
    with open(filepath, "r") as f:
        content = f.read()
    
    # 1. Replace WeatherManager import
    content = re.sub(r'from app\.services\.weather_manager import WeatherManager\s*\n', 'from app.services import weather_manager\n', content)
    # Replace usages
    content = re.sub(r'(?<!\.)WeatherManager\(', 'weather_manager.WeatherManager(', content)
    content = re.sub(r'(?<!\.)WeatherManager\.', 'weather_manager.WeatherManager.', content)
    
    # 2. Replace telegram imports
    # Remove all "from app.services.telegram import (...)" and replace with "from app.services import telegram"
    content = re.sub(r'from app\.services\.telegram import \((.*?)\)', 'from app.services import telegram', content, flags=re.DOTALL)
    content = re.sub(r'from app\.services\.telegram import [^\n]+\n', 'from app.services import telegram\n', content)
    
    # We need to make sure we don't have duplicate "from app.services import telegram"
    lines = content.split('\n')
    new_lines = []
    seen_telegram = False
    for line in lines:
        if line.strip() == 'from app.services import telegram':
            if seen_telegram:
                continue
            seen_telegram = True
        new_lines.append(line)
    content = '\n'.join(new_lines)
    
    # Replace function calls
    funcs = [
        "send_telegram_message",
        "send_telegram_message_return_id",
        "edit_telegram_message",
        "send_telegram_document",
        "send_telegram_photo",
        "send_telegram_video",
        "send_telegram_action"
    ]
    for func in funcs:
        # replace function( with telegram.function(
        # negative lookbehind to avoid telegram.telegram.function
        content = re.sub(r'(?<!\.)\b' + func + r'\(', f'telegram.{func}(', content)

    with open(filepath, "w") as f:
        f.write(content)

print("Router imports refactored.")
