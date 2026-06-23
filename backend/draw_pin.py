import cv2
img = cv2.imread('/Users/oatrice/Software Project/FonMaYang/test_raw_gif.png')
cv2.circle(img, (404, 297), radius=14, color=(0, 0, 255), thickness=-1)
cv2.circle(img, (371, 334), radius=5, color=(0, 255, 0), thickness=-1)
cv2.imwrite('annotated_skn240.png', img)
