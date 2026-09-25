import re

def fix_file(path):
    with open(path, 'r') as f:
        content = f.read()

    # Replace patch("app.services.weather_manager._DEV_CONFIG", ...)
    # with update_dev_settings(...)
    # Wait, in tests it's better to just use get_dev_settings() and mutate it if they are unit tests.
    
    # Or just mock get_dev_settings
    content = content.replace('patch("app.services.weather_manager._DEV_CONFIG"', 'patch("app.core.dev_settings.update_dev_settings"')
    content = content.replace('from app.services.weather_manager import _DEV_CONFIG', 'from app.core.dev_settings import get_dev_settings, update_dev_settings')
    content = content.replace('_DEV_CONFIG.get', 'get_dev_settings().model_dump().get')
    content = content.replace('_DEV_CONFIG[', 'get_dev_settings().model_dump()[')
    
    # manual replace for specific patches
    with open(path, 'w') as f:
        f.write(content)

fix_file('backend/tests/test_manual_targeting.py')
fix_file('backend/tests/test_tmd_improvements.py')
