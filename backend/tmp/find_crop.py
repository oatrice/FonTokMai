import imageio.v3 as iio
import numpy as np
import cv2
import sys

try:
    frames = iio.imread('https://weather.tmd.go.th/kkn/kkn240Loop.gif', index=None)
    img = frames[-1] # use last frame

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Threshold: anything brighter than 10 is considered
    _, thresh = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # Find the largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        print(f"Largest contour bounding box: crop_x={x}, crop_y={y}, crop_width={w}, crop_height={h}")
        
        # Let's also check horizontal intensity to find the legend width
        col_sums = np.sum(thresh, axis=0)
        # Find first column with significant data
        for i, val in enumerate(col_sums):
            pass # we can look at the output
            
    else:
        print("No contours found.")
        
except Exception as e:
    print(f"Error: {e}")
