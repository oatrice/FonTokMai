import numpy as np

img = np.array([[[87, 96, 65]]], dtype=np.uint8)
img_float = img.astype(np.float32)

IGNORED_COLORS = [
    (255, 255, 255), (0, 0, 0), (204, 204, 204), (32, 45, 93), (153, 153, 153),
    (110, 127, 91), (108, 125, 89), (87, 156, 73), (79, 151, 67), (84, 148, 89),
    (77, 159, 74), (61, 156, 64), (66, 172, 71), (75, 169, 73), (73, 170, 77),
    (68, 159, 64), (77, 162, 79), (67, 156, 74), (77, 156, 77), (65, 159, 71),
    (66, 156, 68), (79, 160, 67), (71, 161, 73), (76, 161, 78), (69, 155, 84),
]

DBZ_COLOR_MAPPING = {
    (0, 128, 0): 25.0, (73, 160, 71): 25.0, (42, 157, 37): 25.0, (88, 171, 81): 25.0,
    (5, 174, 5): 25.0, (84, 198, 52): 25.0, (86, 138, 74): 25.0,
    (255, 255, 0): 35.0, (248, 248, 4): 35.0, (241, 242, 12): 35.0, (224, 224, 37): 35.0, (215, 217, 91): 35.0,
    (255, 128, 0): 45.0, (235, 153, 6): 45.0, (243, 168, 14): 45.0, (220, 154, 26): 45.0, (250, 167, 3): 45.0,
    (255, 0, 0): 50.0, (239, 2, 2): 50.0, (198, 2, 2): 55.0, (214, 4, 3): 50.0, (169, 5, 5): 55.0, (220, 40, 10): 50.0,
    (255, 0, 255): 60.0,
}

ignored_min_dists = np.full(img.shape[:2], float('inf'), dtype=np.float32)
best_ignored = None
for ic in IGNORED_COLORS:
    ic_arr = np.array(ic, dtype=np.float32)
    dist = np.sqrt(np.sum((img_float - ic_arr)**2, axis=-1))
    if dist[0,0] < ignored_min_dists[0,0]:
        best_ignored = ic
    better_mask = dist < ignored_min_dists
    ignored_min_dists[better_mask] = dist[better_mask]

print(f"Closest ignored color: {best_ignored}, dist: {ignored_min_dists[0,0]}")

min_dists = np.full(img.shape[:2], 25.0, dtype=np.float32)
best_intensity = np.zeros(img.shape[:2], dtype=np.uint8)
best_rain = None

for color, dbz in DBZ_COLOR_MAPPING.items():
    c_arr = np.array(color, dtype=np.float32)
    dist = np.sqrt(np.sum((img_float - c_arr)**2, axis=-1))
    if dist[0,0] < min_dists[0,0]:
        best_rain = color
    valid_mask = dist < ignored_min_dists
    better_mask = valid_mask & (dist < min_dists)
    min_dists[better_mask] = dist[better_mask]
    best_intensity[better_mask] = int(dbz * 4)

print(f"Closest rain color: {best_rain}, dist: {min_dists[0,0] if min_dists[0,0]<25 else '>25'}")
print(f"Intensity: {best_intensity[0,0]}")

