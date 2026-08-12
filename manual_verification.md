# Manual Verification: Dynamic Radar Candidate Station Selection & Tak Pin Accuracy

## 📋 Verification Overview
Verified that updating `candidates = list(STATIONS.keys())` in `webhook_commands.py` enables dynamic selection of all registered radar stations (including `tak`). For test location `(17.2743, 99.3106)`, the system selects `tak` as the #1 nearest station, projecting user pin to exact pixel `(459, 259)`.

---

## 🧪 Verification Steps & Automated Commands

### 1. Run Unit Tests
Execute the pytest suite for Tak radar station, webhook commands, and e2e radar pipeline:

```bash
cd "/Users/oatrice/Software Project/FonMaYang/backend"
venv/bin/pytest tests/test_tak_radar.py tests/test_webhook.py tests/test_tmd_radar_e2e.py -v
```

**Expected Result:**
- All tests pass 100%.

---

### 2. Verify Candidate Station Selection Logic
Run Python CLI test to verify distance sorting across all registered STATIONS for location `(17.2743, 99.3106)`:

```bash
cd "/Users/oatrice/Software Project/FonMaYang/backend"
venv/bin/python3 -c "
import math
from app.services.tmd_radar_config import STATIONS

lat, lng = 17.2743, 99.3106
def station_distance(code):
    conf = STATIONS[code]
    return math.hypot(lat - conf.center_lat, lng - conf.center_lng)

sorted_stations = sorted(STATIONS.keys(), key=station_distance)
print('Selected primary station:', sorted_stations[0])
"
```

**Expected Output:**
- `Selected primary station: tak`
