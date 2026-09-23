with open('backend/app/services/weather_manager.py', 'r') as f:
    src = f.read()

# _get_tmd_prediction in WeatherManager currently does:
# return await adapter.predict(lat, lng, force_station, **kwargs)
# We want it to do:
# result = await adapter.predict(lat, lng, force_station, **kwargs)
# return result.model_dump() if result else None

src = src.replace("return await adapter.predict(lat, lng, force_station, **kwargs)",
                  "result = await adapter.predict(lat, lng, force_station, **kwargs)\n        return result.model_dump() if result else None")

with open('backend/app/services/weather_manager.py', 'w') as f:
    f.write(src)
