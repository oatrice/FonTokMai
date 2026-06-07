import cv2
import numpy as np
from PIL import Image

img = Image.open('/Users/oatrice/Downloads/radar_nowcast_full (1).gif')
img.seek(0)
palette = img.getpalette()
colors = []
for i in range(0, len(palette), 3):
    r, g, b = palette[i:i+3]
    colors.append((r,g,b))
    print(f"Color {i//3}: R={r}, G={g}, B={b}")
