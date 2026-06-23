import cv2, numpy as np
img = cv2.imread('/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/frame0.png')
# Since the template has annotations, we match a smaller patch of the map background from user_img3.jpg
# Or better, we can manually identify where the pin in user_img3.jpg is.
# In user_img3.jpg, Sakon Nakhon is visible on the left. The pin is to the right.
# In frame0.png, Sakon Nakhon is at 370, 334.
# The blue pin in user_img3.jpg is about 96 pixels right, 0 pixels down from Sakon Nakhon.
# 370 + 96 = 466. 334 + 0 = 334.
