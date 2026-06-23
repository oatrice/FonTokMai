import cv2
import numpy as np
import sys
import glob

# Try to find user images in artifacts dir
artifact_dir = '/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/'
images = glob.glob(artifact_dir + 'user_img*.jpg')
if not images:
    # maybe they are media files?
    images = glob.glob(artifact_dir + '.tempmediaStorage/*.jpg')

for img_path in images:
    img = cv2.imread(img_path)
    if img is None: continue
    
    # Red color range
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
    mask = mask1 | mask2
    
    # We want to ignore the red pixels from the radar echo itself (if any).
    # But let's just find the center of the largest red blob.
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) > 10:
            M = cv2.moments(largest)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                print(f"Red blob found in {img_path.split('/')[-1]} at {cX}, {cY} with area {cv2.contourArea(largest)}")
            
