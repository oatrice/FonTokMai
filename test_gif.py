import urllib.request
import cv2
import numpy as np

url = "https://weather.tmd.go.th/skn/skn240Loop.gif"
urllib.request.urlretrieve(url, "skn240Loop.gif")
