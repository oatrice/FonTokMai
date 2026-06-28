import json

predictions = [
    {"dbz": 0.0, "time_offset": 0},
    {"dbz": 25.0, "time_offset": 15},
    {"dbz": 0.0, "time_offset": 30},
    {"dbz": 0.0, "time_offset": 45},
    {"dbz": 0.0, "time_offset": 60},
    {"dbz": 0.0, "time_offset": 75},
    {"dbz": 0.0, "time_offset": 90},
]

time_offset_min = 0.0
rain_events = []
in_rain = False
start_idx = -1
max_dbz = 0.0
max_idx = -1

for i, p in enumerate(predictions):
    dbz = p["dbz"]
    if dbz >= 15.0:
        if not in_rain:
            in_rain = True
            start_idx = i
            max_dbz = dbz
            max_idx = i
        else:
            if dbz > max_dbz:
                max_dbz = dbz
                max_idx = i
    else:
        if in_rain:
            in_rain = False
            rain_events.append({
                "start_idx": start_idx,
                "stop_idx": i,
                "max_dbz": max_dbz,
                "max_idx": max_idx
            })

if in_rain:
    rain_events.append({
        "start_idx": start_idx,
        "stop_idx": -1,
        "max_dbz": max_dbz,
        "max_idx": max_idx
    })

active_event = None
for event in rain_events:
    stop_idx = event["stop_idx"]
    if stop_idx == -1:
        active_event = event
        break
    
    stop_time = predictions[stop_idx]["time_offset"]
    if stop_time - time_offset_min > 0:
        active_event = event
        break

def dbz_label(dbz: float) -> str:
    return "ฝน"

def fmt_eta(m: float) -> str:
    return f"~{m} min"

if not active_event:
    print("NO RAIN: ☀️ ยังไม่มีแนวโน้มฝนตก")
else:
    start_idx = active_event["start_idx"]
    stop_idx = active_event["stop_idx"]
    max_dbz = active_event["max_dbz"]
    max_idx = active_event["max_idx"]
    
    start_time = predictions[start_idx]["time_offset"]
    start_dbz = predictions[start_idx]["dbz"]
    lbl_start = dbz_label(start_dbz)
    
    adj_start = start_time - time_offset_min
    
    if adj_start <= 0:
        print("RAIN NOW")
    else:
        print(f"RAIN LATER: ⏱ ฝนกำลังจะมาใน {fmt_eta(start_time)}")

