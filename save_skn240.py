import urllib.request
url = "https://weather.tmd.go.th/skn/skn240_latest.jpg"
urllib.request.urlretrieve(url, "skn240_latest.jpg")
print("Saved")
