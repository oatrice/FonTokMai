from PIL import Image
im = Image.open("skn240Loop.gif")
im.seek(0)
im.save("frame0.png")
