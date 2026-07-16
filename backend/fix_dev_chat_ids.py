import os
import re

ROUTER_FILES = [
    "backend/app/routers/webhook.py",
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

    # In webhook_utils.py, check_admin_access uses DEVELOPER_CHAT_IDS, replace with telegram.DEVELOPER_CHAT_IDS
    content = content.replace(" DEVELOPER_CHAT_IDS", " telegram.DEVELOPER_CHAT_IDS")
    # But wait, replacing literally might replace the import statement!
    # Let's clean up import DEVELOPER_CHAT_IDS from webhook_utils
    content = re.sub(r',\s*DEVELOPER_CHAT_IDS\b', '', content)
    content = re.sub(r'\bDEVELOPER_CHAT_IDS\s*,', '', content)
    content = re.sub(r'^\s*DEVELOPER_CHAT_IDS\b\s*$', '', content, flags=re.MULTILINE)
    
    # After removing from imports, let's fix usages:
    # "in DEVELOPER_CHAT_IDS" -> "in telegram.DEVELOPER_CHAT_IDS"
    # "set(DEVELOPER_CHAT_IDS)" -> "set(telegram.DEVELOPER_CHAT_IDS)"
    content = re.sub(r'\bDEVELOPER_CHAT_IDS\b', 'telegram.DEVELOPER_CHAT_IDS', content)
    
    # We might have generated telegram.telegram.DEVELOPER_CHAT_IDS, let's fix that
    content = content.replace("telegram.telegram.DEVELOPER_CHAT_IDS", "telegram.DEVELOPER_CHAT_IDS")
    
    with open(filepath, "w") as f:
        f.write(content)
print("Fixed DEVELOPER_CHAT_IDS")
