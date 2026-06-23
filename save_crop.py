import cv2, numpy as np, urllib.request
url = 'https://weather.tmd.go.th/skn/skn240_latest.jpg'
arr = np.asarray(bytearray(urllib.request.urlopen(url).read()), dtype=np.uint8)
img = cv2.imdecode(arr, -1)

# I will draw a cross at 436, 392 (the config center)
cv2.drawMarker(img, (436, 392), (255, 0, 0), cv2.MARKER_CROSS, 20, 2)

# Save the crop
cv2.imwrite("/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/crop.jpg", img[300:500, 300:600])
