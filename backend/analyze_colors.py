import numpy as np
from app.services.tmd_radar.clustering import TMDClusteringMixin

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1]

mask = TMDClusteringMixin().extract_rain_mask(img)
# Let's count how many pixels have dbz >= 10.0 before our weak colors addition
# Let's write a clean version of extract_rain_mask without weak colors
def extract_clean(img):
    img_float = img.astype(np.float32)
    from app.services.tmd_radar_config import DBZ_COLOR_MAPPING, IGNORED_COLORS
    min_dists = np.full(img.shape[:2], 25.0, dtype=np.float32)
    best_intensity = np.zeros(img.shape[:2], dtype=np.uint8)
    
    ignored_min_dists = np.full(img.shape[:2], float('inf'), dtype=np.float32)
    for ic in IGNORED_COLORS:
        ic_arr = np.array(ic, dtype=np.float32)
        dist = np.sqrt(np.sum((img_float - ic_arr)**2, axis=-1))
        better_mask = dist < ignored_min_dists
        ignored_min_dists[better_mask] = dist[better_mask]
        
    for color, dbz in DBZ_COLOR_MAPPING.items():
        c_arr = np.array(color, dtype=np.float32)
        dist = np.sqrt(np.sum((img_float - c_arr)**2, axis=-1))
        valid_mask = dist < ignored_min_dists
        better_mask = (dist < min_dists) & valid_mask
        min_dists[better_mask] = dist[better_mask]
        intensity = int(min(255, max(50, dbz * 4)))
        best_intensity[better_mask] = intensity
    return best_intensity

clean_mask = extract_clean(img)
y_clean, x_clean = np.where(clean_mask > 0)
print(f"Clean rain pixels: {len(x_clean)}")

# Check values at P1, P2, P3 in clean_mask
for name, (x, y) in [("P1", (317, 6)), ("P2", (257, 92)), ("P3", (325, 68))]:
    val = clean_mask[y, x]
    print(f"{name} clean_intensity: {val} (dbz={val/4.0})")

