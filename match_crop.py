import cv2, numpy as np, urllib.request

url = 'https://weather.tmd.go.th/skn/skn240_latest.jpg'
arr = np.asarray(bytearray(urllib.request.urlopen(url).read()), dtype=np.uint8)
img = cv2.imdecode(arr, -1)

template = cv2.imread('/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/user_img3.jpg')
# Remove the pin from template for matching
# The pin is around 360, 360 with radius ~20
# Actually, the user's bot drew the pin. The base image doesn't have it.
# We can just match using TM_CCOEFF_NORMED
res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
print("Best match at:", max_loc, "with confidence", max_val)

# If matched, where is the pin?
pin_x_in_template = 360
pin_y_in_template = 360
global_x = max_loc[0] + pin_x_in_template
global_y = max_loc[1] + pin_y_in_template
print("Pin in original image:", global_x, global_y)
# Adjust for crop
crop_x = 72
crop_y = 28
print("Pin in crop coordinates:", global_x - crop_x, global_y - crop_y)
