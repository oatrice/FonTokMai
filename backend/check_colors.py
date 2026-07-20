import numpy as np

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1] # The last frame

colors_to_test = [
    (87, 96, 65),
    (69, 78, 47),
    (130, 145, 106),
]

for tgt in colors_to_test:
    diff = np.abs(img.astype(np.int32) - np.array(tgt))
    dist = np.sum(diff, axis=-1)
    # find where dist < 5
    y_coords, x_coords = np.where(dist < 5)
    print(f"Color {tgt} appears in {len(x_coords)} pixels.")
