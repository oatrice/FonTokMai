# Task List: Issue #2 (FastAPI On-demand Routers)

## TDD Cycle
- `[x]` เขียน Failing Tests (RED) สำหรับ API `GET /api/v1/weather/predict`
- `[x]` สร้าง Pydantic Schema สำหรับ Request/Response
- `[x]` สร้าง FastAPI Router และเรียกใช้ `RainbowService` (GREEN)
- `[x]` สร้าง `main.py` เพื่อเชื่อมต่อ Router ทั้งหมด
- `[x]` Refactor โค้ดให้สวยงามและเป็นระเบียบ

## Future Improvements (Noted)
- `[ ]` **Enhancement:** นำ `RainViewerService` มาทำงานร่วมกับ `RainbowService` ผ่าน `asyncio.gather` เพื่อตรวจสอบความสดใหม่ของข้อมูลเรดาร์ (Data Freshness / Delay Monitor $\Delta t$) โดยส่งค่า `is_delayed` แนบไปใน Response ด้วย
