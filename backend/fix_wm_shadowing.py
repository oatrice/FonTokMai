import os
import re

for filepath in ["backend/app/routers/webhook_callbacks.py", "backend/app/routers/webhook_location.py", "backend/app/routers/webhook_commands.py", "backend/app/routers/worker.py"]:
    if not os.path.exists(filepath):
        continue
    with open(filepath, "r") as f:
        content = f.read()

    # Change local variable weather_manager to wm
    content = content.replace("weather_manager = weather_manager.WeatherManager()", "wm = weather_manager.WeatherManager()")
    # Also change usages of the local variable. Since they might be weather_manager.predict_rain, we should be careful.
    # It's actually safer to just do a smart regex or simply replace specific method calls
    
    # We replaced it to `wm = ...`, now let's change `weather_manager.` to `wm.` BUT ONLY for the methods of the instance
    content = content.replace("weather_manager.predict_rain", "wm.predict_rain")
    content = content.replace("weather_manager.compare_all_apis", "wm.compare_all_apis")
    content = content.replace("weather_manager.get_advanced_alerts", "wm.get_advanced_alerts")
    
    with open(filepath, "w") as f:
        f.write(content)
print("Fixed weather_manager variable shadowing.")
