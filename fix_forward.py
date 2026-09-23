path = 'backend/app/services/weather_manager.py'
with open(path, 'r') as f:
    text = f.read()

text = text.replace(
    'async def _get_tmd_prediction(self, lat: float, lng: float, force_station: Optional[str] = None) -> Optional[Dict[str, Any]]:',
    'async def _get_tmd_prediction(self, lat: float, lng: float, force_station: Optional[str] = None, **kwargs) -> Optional[Dict[str, Any]]:'
)
text = text.replace(
    'return await adapter.predict(lat, lng, force_station)',
    'return await adapter.predict(lat, lng, force_station, **kwargs)'
)

with open(path, 'w') as f:
    f.write(text)

path = 'backend/app/services/tmd_radar/adapter.py'
with open(path, 'r') as f:
    text = f.read()

text = text.replace(
    'async def predict(self, lat: float, lng: float, force_station: Optional[str] = None) -> Dict[str, Any]:',
    'async def predict(self, lat: float, lng: float, force_station: Optional[str] = None, **kwargs) -> Dict[str, Any]:'
)

with open(path, 'w') as f:
    f.write(text)

path = 'backend/app/services/tmd_radar/nowcast_port.py'
with open(path, 'r') as f:
    text = f.read()

text = text.replace(
    'async def predict(self, lat: float, lng: float, force_station: Optional[str] = None) -> Dict[str, Any]:',
    'async def predict(self, lat: float, lng: float, force_station: Optional[str] = None, **kwargs) -> Dict[str, Any]:'
)

with open(path, 'w') as f:
    f.write(text)
