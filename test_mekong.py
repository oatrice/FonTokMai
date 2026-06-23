import cv2, numpy as np
img = cv2.imread('/Users/oatrice/Documents/2569-06-22 19.59.49.jpg')
y = 354
for x in range(0, img.shape[1]):
    b, g, r = img[y, x]
    if b > g and b > r and b > 100:
        print(f"Blue pixel at X={x}, B={b}, G={g}, R={r}")
