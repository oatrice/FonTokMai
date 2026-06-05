# แผนการพัฒนา Batch H: Disasters & Natural Hazards Alerts (Issue #45)

เป้าหมายของ Batch H คือการเพิ่มระบบแจ้งเตือนภัยพิบัติและภัยธรรมชาติแบบ Proactive ได้แก่ พายุหมุนเขตร้อน (Tropical Cyclones), แผ่นดินไหว (Earthquakes), และไฟป่า/จุดความร้อน (Fires) โดยใช้ประโยชน์จาก Xweather API (AerisWeather) เป็นหลัก

> [!IMPORTANT]
> **การลด API Cost (Broad Geofencing Strategy)**
> เนื่องจากภัยพิบัติเป็นเหตุการณ์ระดับมหภาค (Macro-scale) ที่ครอบคลุมพื้นที่กว้างขวาง การยิง API เช็คสภาพอากาศรายบุคคล (เหมือนระบบเตือนฝนปัจจุบัน) จะทำให้ API Quota ของ Xweather (15,000 req/month) หมดลงอย่างรวดเร็ว ดังนั้นสถาปัตยกรรมใน Batch H จะเปลี่ยนไปใช้การดึงข้อมูลภัยพิบัติภาพรวม (Global/Regional Fetch) แล้วนำมาคำนวณระยะทางกับผู้ใช้ทั้งหมดในฝั่ง Backend แทน

## Open Questions

> [!WARNING]
> **ต้องการความเห็นจากผู้ใช้ก่อนเริ่มดำเนินการ:**
> 1. **แหล่งข้อมูลแผ่นดินไหวแบบ Real-time (Hybrid Approach):** ตามที่คุณต้องการ เราจะทำทั้ง 2 แบบควบคู่กัน!
>    - **Primary (Real-time):** เปิดการเชื่อมต่อ **WebSocket กับ EMSC** ตอนที่บอทเริ่มทำงาน เพื่อรับ Push ข้อมูลแผ่นดินไหวทันทีในระดับเสี้ยววินาที
>    - **Fallback (Reliability):** ให้ตัว Scheduler ยิงเช็ค **USGS GeoJSON Feed** ทุกๆ 1 นาที เผื่อกรณีที่ WebSocket หลุด (ซึ่งพบบ่อยใน Cloud Run) ระบบก็จะไม่พลาดการแจ้งเตือน
> 2. **ความถี่ในการดึงข้อมูลอื่นๆ (Polling Interval):** พายุ/ไฟป่า เช็คทุกๆ 30-60 นาทีจาก Xweather เหมือนเดิม
> 3. **รัศมีการแจ้งเตือน (Impact Radius Threshold) ที่ใช้งานจริง:**
>    - **แผ่นดินไหว:** ขนาด 7.0+ (1,000km), ขนาด 6.0+ (800km), ขนาด 4.5+ (300km)
>    - **พายุไต้ฝุ่น:** 1,000 km 
>    - **ไฟป่า/จุดความร้อน:** 200 km
> 4. **Database Schema:** บันทึกประวัติผ่าน `LocationRepository` ลง Firestore หรือ SQLite อัตโนมัติตามการตั้งค่า เพื่อป้องกันข้อมูลหายเมื่อ Cloud Run Scale

## Proposed Changes

---

### Database Schema

#### [NEW] `disaster_alerts_history` in `LocationRepository`
เพิ่มฟังก์ชันใน `LocationRepository` (ทั้ง SQLite และ Firestore) เพื่อเช็คและบันทึกประวัติ ป้องกันการเตือนซ้ำในเหตุการณ์เดิม
- `has_disaster_alert_been_sent(chat_id, event_id)`
- `mark_disaster_alert_sent(chat_id, event_id, event_type)`

---

### API Integration & Real-time Listeners

#### [NEW] `backend/app/services/earthquake.py`
สร้าง Service ใหม่เพื่อจัดการข้อมูลแผ่นดินไหวโดยเฉพาะเพื่อไม่ให้ไปกวนโควต้า Xweather:
- `start_emsc_websocket()`: ฟังก์ชัน Background Task (asyncio) ทำหน้าที่ต่อ WebSocket (wss://www.seismicportal.eu/standing_order/websocket) ทิ้งไว้เพื่อรับข้อมูลแผ่นดินไหวแบบ Push
- `fetch_usgs_geojson()`: ฟังก์ชันสำรองสำหรับดึง JSON จาก `earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson` เพื่อใช้เป็น Fallback

#### [MODIFY] `backend/app/services/xweather.py`
เพิ่มฟังก์ชันสำหรับการดึงข้อมูลระดับกว้าง (Broad Fetch):
- `get_active_tropical_cyclones()`: เรียกใช้ endpoint `/tropicalcyclones` แบบ `filter=active` เพื่อเอาพายุที่กำลังก่อตัวทั้งหมดบนโลก หรือเฉพาะโซน
- `get_recent_earthquakes()`: เรียกใช้ endpoint `/earthquakes` แบบ `filter=all` โดยกำหนดขนาดความรุนแรง (เช่น `minmag=4.0`) ในช่วง 24 ชั่วโมงที่ผ่านมา
- `get_active_fires()`: เรียกใช้ endpoint `/fires` โดยระบุ Bounding Box (พิกัดครอบคลุมไทยและประเทศเพื่อนบ้าน) เพื่อหาจุดความร้อน

---

### Scheduler & Core Logic (Geofencing)

#### [MODIFY] `backend/app/scheduler_tasks.py`
เพิ่ม Job ใหม่ `check_disasters_routine()` ที่แยกออกมาจาก `check_rain_routine()`
1. **Fetch Events:** ดึงข้อมูลภัยพิบัติทั้งหมด (พายุ, แผ่นดินไหว, ไฟป่า) จาก `XweatherService`
2. **Fetch Users:** ดึงพิกัดทั้งหมดจาก `user_locations`
3. **Spatial Matching:** คำนวณระยะทาง (Haversine formula) ระหว่างพิกัดของภัยพิบัติและพิกัดผู้ใช้แต่ละคน
4. **Filter Thresholds:** ตรวจสอบว่าระยะทางอยู่ในรัศมีเตือนภัยหรือไม่ (เช่น แผ่นดินไหว 100km, ไฟป่า 30km)
5. **Check History:** ตรวจสอบ `disaster_alert_history` ว่าเคยแจ้งเตือนเหตุการณ์ ID นี้ให้ผู้ใช้รายนี้หรือยัง
6. **Trigger Alert:** แจ้งเตือนไปยัง Telegram และบันทึกลง History

---

### Telegram Messaging

#### [MODIFY] `backend/app/services/telegram.py`
เพิ่ม Message Templates สำหรับภัยพิบัติให้มีความน่าเชื่อถือและเร่งด่วน:
- **แผ่นดินไหว:** แจ้งขนาด (Magnitude), ความลึก, ระยะห่างจากผู้ใช้
- **พายุหมุนเขตร้อน:** แจ้งชื่อพายุ, ความเร็วลมสูงสุด, ระยะห่าง, และทิศทางการเคลื่อนที่
- **ไฟป่า/จุดความร้อน:** แจ้งระยะห่างและความรุนแรงเบื้องต้น

## Verification Plan

### Automated Tests
- เขียน Unit Test ในการประเมินระยะทาง `Haversine distance` ว่าทำงานถูกต้องแม่นยำ
- Mock ข้อมูล Xweather API (แผ่นดินไหวจำลองที่ระยะ 50km และ 200km) เพื่อตรวจสอบว่า User ในรัศมีได้รับการแจ้งเตือน ในขณะที่ User นอกรัศมีไม่ได้รับการแจ้งเตือน

### Manual Verification
- รันคำสั่งบังคับเรียก `check_disasters_routine()` ด้วยข้อมูล Mock
- สังเกตการณ์แจ้งเตือนภัยพิบัติบน Telegram ว่ามีการ Format สวยงาม และอีโมจิสื่อถึงความฉุกเฉิน
- ตรวจสอบในฐานข้อมูลว่ามีการบันทึก `event_id` ป้องกันการเตือนซ้ำในรอบถัดไป
