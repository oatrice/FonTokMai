import os
import re

TEST_DIR = 'tests'
for root, _, files in os.walk(TEST_DIR):
    for file in files:
        if file.startswith('test_') and file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()

            # Fix handle_rain_command imports
            content = content.replace(
                'from app.routers.webhook import handle_rain_command',
                'from app.routers.webhook_commands import handle_rain_command'
            )

            # Fix missing patches for devmock
            content = content.replace(
                'patch("app.routers.webhook.devmock_state_lock"',
                'patch("app.routers.webhook_devmock.devmock_state_lock"'
            )
            content = content.replace(
                'patch("app.routers.webhook.get_active_devmock_state"',
                'patch("app.routers.webhook_devmock.get_active_devmock_state"'
            )
            
            # The big issue: patch("app.services.telegram.XYZ") needs to be mapped to the file where it's actually used.
            # But the test might test multiple endpoints. 
            # Easiest solution for the tests: re-import the telegram functions in the modules 
            # BUT python mocking is hard. Let's just fix the routers to use `import app.services.telegram as telegram` instead of `from app.services.telegram import ...`
            pass

            with open(filepath, 'w') as f:
                f.write(content)
print("Done modifying test imports.")
