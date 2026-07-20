from PIL import Image
import numpy as np

img = Image.open('radar/skn240_backup/skn240_1784219585.gif').convert('RGB')
arr = np.array(img)

pts = [(317, 6), (257, 92), (325, 68), (500, 675), (557, 687), (681, 220), (693, 162)]

for pt in pts:
    y, x = pt[0], pt[1]  # user meant (y,x) or (x,y)?
    try:
        print(f"Point {pt}: color at (y,x)={pt} is {arr[pt]}")
    except:
        pass
    try:
        print(f"Point {pt}: color at (x,y)={pt[::-1]} is {arr[pt[::-1]]}")
    except:
        pass

