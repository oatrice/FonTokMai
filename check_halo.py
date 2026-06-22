import cv2
import numpy as np

img = cv2.imread("test_home.jpg")

# Crop around the blue cross (894, 657)
x, y = 894, 657
roi = img[y-30:y+30, x-30:x+30]

if roi is not None and roi.shape[0] > 0 and roi.shape[1] > 0:
    # Check for white pixels
    white_mask = (roi[:,:,0] > 200) & (roi[:,:,1] > 200) & (roi[:,:,2] > 200)
    white_count = np.sum(white_mask)
    print(f"White pixels near blue cross: {white_count}")
    
    # Save the ROI
    cv2.imwrite("backend/tmp/blue_cross_roi.png", roi)
else:
    print("Invalid ROI")
