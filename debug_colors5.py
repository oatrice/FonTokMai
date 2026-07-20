import numpy as np

data = np.load('backend/tests/test_kkn240_frames.npz', allow_pickle=True)
img = data['frames'][-1]

IGNORED_COLORS = [
    (255, 255, 255), (0, 0, 0), (204, 204, 204), (32, 45, 93), (153, 153, 153),
    (110, 127, 91), (108, 125, 89), (87, 156, 73), (79, 151, 67), (84, 148, 89),
    (77, 159, 74), (61, 156, 64), (66, 172, 71), (75, 169, 73), (73, 170, 77),
    (68, 159, 64), (77, 162, 79), (67, 156, 74), (77, 156, 77), (65, 159, 71),
    (66, 156, 68), (79, 160, 67), (71, 161, 73), (76, 161, 78), (69, 155, 84),
    (62, 101, 144), (192, 192, 192)
]

DBZ_COLOR_MAPPING = {
    (0, 128, 0): 25.0, (73, 160, 71): 25.0, (42, 157, 37): 25.0, (88, 171, 81): 25.0,
    (5, 174, 5): 25.0, (84, 198, 52): 25.0, (86, 138, 74): 25.0,
    (255, 255, 0): 35.0, (248, 248, 4): 35.0, (241, 242, 12): 35.0, (224, 224, 37): 35.0, (215, 217, 91): 35.0,
    (255, 128, 0): 45.0, (235, 153, 6): 45.0, (243, 168, 14): 45.0, (220, 154, 26): 45.0, (250, 167, 3): 45.0,
    (255, 0, 0): 50.0, (239, 2, 2): 50.0, (198, 2, 2): 55.0, (214, 4, 3): 50.0, (169, 5, 5): 55.0, (220, 40, 10): 50.0,
    (255, 0, 255): 60.0,
}

pixels = img.reshape(-1, 3)
unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
sorted_idx = np.argsort(-counts)
unique_colors = unique_colors[sorted_idx]
counts = counts[sorted_idx]

rain_pixels = 0
for i in range(1000):
    c = unique_colors[i]
    min_dist_ignore = min(np.linalg.norm(c - np.array(ic)) for ic in IGNORED_COLORS)
    min_dist_rain = min(np.linalg.norm(c - np.array(rc)) for rc in DBZ_COLOR_MAPPING.keys())
    
    if min_dist_rain < min_dist_ignore and min_dist_rain < 45:
        rain_pixels += counts[i]
        if counts[i] > 100:
            print(f"RAIN Color: {c}, Count: {counts[i]}, Dist Ignore: {min_dist_ignore:.1f}, Dist Rain: {min_dist_rain:.1f}")

print(f"Total rain pixels: {rain_pixels}")
