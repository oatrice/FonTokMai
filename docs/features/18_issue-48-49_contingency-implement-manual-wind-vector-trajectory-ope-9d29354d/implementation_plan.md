# แผนการผนวก Open-Meteo เข้ากับระบบ WeatherManager

## เป้าหมาย (Goal Description)
เพื่อเพิ่มแหล่งข้อมูล Open-Meteo (ซึ่งเป็นบริการฟรีและ Open-Source) เข้ามาเสริมความแข็งแกร่งให้กับระบบพยากรณ์อากาศและแจ้งเตือนภัยของ FonMaYang โดยมีเป้าหมายหลัก 2 ประการซึ่งสอดคล้องกับ Issues ที่มีอยู่บน GitLab:
1. **Issue #48 (Contingency):** เป็นระบบสำรองสำหรับคำนวณทิศทางพายุ (Wind Vector Trajectory) แบบ manual ในกรณีที่ Xweather API ล่มหรือหมดอายุ
2. **Issue #49 (Research):** เพิ่ม Open-Meteo เข้าไปในระบบ `compare_all_apis` เพื่อใช้เปรียบเทียบความแม่นยำกับ Xweather, Tomorrow.io และ Rainbow.ai

## สิ่งที่ต้องการให้ผู้ใช้ทบทวน (User Review Required)

> [!IMPORTANT]
> **ตำแหน่งใน Fallback Chain:**
> สำหรับฟังก์ชัน `predict_rain` เราควรใส่ Open-Meteo ไว้ตรงจุดไหนของ Fallback Chain?
> - **Option A:** ใส่ไว้ท้ายสุดเป็นตัวสำรองลำดับสุดท้าย (Xweather → Tomorrow.io → Rainbow → Open-Meteo) เนื่องจากโมเดลของ Open-Meteo อาจไม่ได้เน้น Nowcasting ในพื้นที่เฉพาะเจาะจงระดับ 1-5 นาทีเหมือน Rainbow
> - **Option B:** ยังไม่ใส่ใน Fallback Chain ของ `predict_rain` แต่ใช้เฉพาะฟังก์ชัน Contingency ของลม (Issue #48) และระบบ Compare (Issue #49) ไปก่อนเพื่อเก็บข้อมูลประเมินความแม่นยำ

> [!WARNING]
> **การคำนวณ Stormcell (Issue #48):** 
> หาก Xweather ขัดข้อง เราสามารถใช้ข้อมูลความเร็วลมและทิศทางลมจาก Open-Meteo ได้ แต่เราต้องมีการเขียนสมการคำนวณ Advection (การเคลื่อนตัวของเซลล์ฝน) ด้วยตัวเอง (อ้างอิงจาก Issue #31) ต้องการให้เริ่มพัฒนาอัลกอริทึมนี้ในรอบนี้เลยหรือไม่?

## คำถามเพิ่มเติม (Open Questions)

- Open-Meteo มีโมเดลสภาพอากาศหลากหลาย (เช่น ICON, GFS) เราควรใช้ค่าเริ่มต้นที่ระบบ auto-select ให้ หรือต้องการเจาะจงโมเดลที่เหมาะกับโซนเอเชียตะวันออกเฉียงใต้ (เช่น ICON ของ DWD) หรือไม่?
- ต้องการให้เพิ่มฟังก์ชัน Mocks สำหรับ Open-Meteo (เช่น `mock_open_meteo_state`) สำหรับการทดสอบด้วยหรือไม่?

## การเปลี่ยนแปลงที่นำเสนอ (Proposed Changes)

### Backend Services

#### [NEW] `backend/app/services/open_meteo.py`
- สร้างคลาส `OpenMeteoService` (สืบทอดจาก `WeatherBase` หรือเขียนแยก)
- ฟังก์ชัน `predict_rain_by_location`: ดึงข้อมูลปริมาณฝน (Minutely/Hourly)
- ฟังก์ชัน `get_wind_vector`: ดึงข้อมูลทิศทางลม (`wind_direction_10m`) และความเร็วลม (`wind_speed_10m`)

#### [MODIFY] `backend/app/services/weather_manager.py`
- **`__init__`**: เพิ่มการเรียกใช้ `self.open_meteo_svc = OpenMeteoService()`
- **`compare_all_apis`**: เพิ่ม Task ของ `open_meteo` เข้าไปในลิสต์ของการเรียก API แบบขนานเพื่อนำผลลัพธ์มาเปรียบเทียบใน Dashboard หรือ Logger
- **`get_advanced_alerts`**: แก้ไขบล็อก `except Exception as e:` (ตาม TODO เดิม) ให้มีการเรียก `OpenMeteoService.get_wind_vector()` มาคำนวณระยะห่าง/ทิศทางพายุ (Stormcell fallback) หาก Xweather พัง
- **`predict_rain`**: (รอการตัดสินใจ) อาจจะเพิ่มเป็นชั้น Fallback พิเศษ

### ทดสอบและการตั้งค่า

#### [MODIFY] `backend/requirements.txt`
- เพิ่มไลบรารี `openmeteo-requests`, `requests-cache`, `retry-requests` ตาม Best Practice ที่ Open-Meteo แนะนำ (หากจำเป็น)

#### [NEW] `backend/tests/test_open_meteo.py`
- เพิ่ม Unit Test เพื่อตรวจสอบการดึงข้อมูลทิศทางลมและปริมาณฝน รวมถึงการทดสอบ Fallback 

## แผนการตรวจสอบ (Verification Plan)

### Automated Tests
- รัน `pytest backend/tests/test_open_meteo.py` เพื่อทดสอบว่า API สามารถดึงข้อมูลทิศทางลมและฝนได้จริง
- รัน Unit Tests เพื่อยืนยันว่า หากจำลอง (Mock) ให้ Xweather พัง ระบบจะสามารถสลับไปดึงข้อมูลทิศทางลมจาก Open-Meteo ได้สำเร็จ

### Manual Verification
- เรียก Endpoint `/weather/compare` ผ่าน Postman หรือ Swagger UI เพื่อดูว่าผลลัพธ์มี `endpoint: open_meteo` โผล่ขึ้นมาพร้อมกับเจ้าอื่นๆ หรือไม่
- สร้าง Alert ปลอมเพื่อให้ระบบเข้าสู่กระบวนการ `get_advanced_alerts` แล้วลองปิด Xweather ดูว่าระบบดึงข้อมูล Stormcell ด้วย Open-Meteo มาแสดงแทนได้หรือไม่
