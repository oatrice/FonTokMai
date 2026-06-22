from app.services.ocr_service import OCRService
import cv2
import asyncio

async def test():
    ocr = OCRService()
    img = cv2.imread("skn240_latest.jpg")
    results = ocr.reader.readtext(img)
    for res in results:
        print(res[1], res[0])

asyncio.run(test())
