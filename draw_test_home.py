import cv2
img = cv2.imread("test_home.jpg")
cv2.circle(img, (760, 558), 20, (0, 255, 0), 5)
cv2.imwrite("/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/test_home_annotated.jpg", img)
