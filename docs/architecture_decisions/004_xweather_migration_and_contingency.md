# ADR 004: Xweather Migration and Advanced Nowcasting

## Status
Implemented (v0.16.0)

## Context
ในตอนแรก (อ้างอิงจาก ADR 003) เรามีแผนจะแก้ปัญหา False Positives และการทำ Nowcasting ด้วยการแปลงรูปภาพเรดาร์จาก RainViewer (Raster) เป็นตัวเลข dBZ และคำนวณการเคลื่อนที่ของกลุ่มฝน (Advection) เองด้วยความเร็วลม (Wind Vectors) แต่การคำนวณด้วยตัวเองมีความซับซ้อนสูง ลมผิวพื้นไม่ตรงกับลมที่พัดเมฆ และ RainViewer ได้ยกเลิกการให้ใช้ API เชิงพาณิชย์สำหรับองค์กรแล้ว

เราจึงตัดสินใจเปลี่ยนแนวทาง (Pivot) ย้ายไปใช้ **Xweather (AerisWeather)** ซึ่งเป็นผู้ให้บริการระดับ Enterprise ที่มีฟีเจอร์พยากรณ์ล่วงหน้าระดับนาที (Minutecast), Vector Polygons, และมี AI Storm Tracking สำเร็จรูปที่ไม่ต้องเขียนสูตรฟิสิกส์คำนวณเอง

## Decisions

### 1. Integrate Xweather API (Issues #32-35)
ระบบจะดึงศักยภาพสูงสุดของ Xweather มาใช้ในกรณีดังนี้:
- ใช้ `minutecast` สำหรับการเตือนฝนรายนาทีอย่างแม่นยำ
- ใช้ `advisories` สำหรับเตือนภัยพิบัติฉุกเฉิน (Severe Weather, Floods)
- ใช้ `lightning/closest` สำหรับเตือนภัยฟ้าผ่า
- ใช้ `stormcells` สำหรับคำนวณทิศทางพายุสำเร็จรูป (ไม่ต้องคำนวณ Wind Vector เอง)

### 2. Contingency Plan: Free Tier Limits / Trial Expiration
เนื่องจาก Xweather มีระบบ Pay-As-You-Go และบัญชีฟรีจำกัดที่ 15,000 requests/เดือน ในกรณีที่หมดอายุ Trial หรือโควต้าเต็ม เราได้วางแผนรับมือด้วยระบบ **Graceful Degradation** ดังนี้:
- **Core Fallback Strategy:** ระบบ `WeatherManager` มีระบบ Circuit Breaker ดักจับ Error 401, 403, 429 และสลับการทำงานกลับไปดึงข้อมูลฝนจาก **Tomorrow.io** (Minutecast fallback) และ **Rainbow.ai** (Global fallback) โดยอัตโนมัติ เพื่อให้ผู้ใช้ยังคงได้รับการเตือนฝนตกพื้นฐาน
- **Degraded Mode สำหรับฟีเจอร์ขั้นสูง:** ฟีเจอร์ที่ทำงานได้เฉพาะตอนมี Xweather (เช่น การเตือนฟ้าผ่า, กรวยเตือนภัยพายุ) จะหยุดทำงาน (Gracefully fail) อย่างเงียบๆ โดยไม่ทำให้ Core Feature พัง ผู้ใช้เพียงแค่จะไม่ได้รับข้อความล้ำๆ ชั่วคราวจนกว่าโควต้าเดือนใหม่จะมา
- **Rate Limit Optimization:** หากพบว่า 15,000 requests/เดือน ไม่เพียงพอ ระบบอาจพิจารณาทำ Caching ในระดับเขต (District-level caching) หากมีผู้ใช้หลายคนอยู่ในรัศมีเดียวกัน

## Consequences
- **Positive:** ทีมพัฒนาสามารถส่งมอบฟีเจอร์เตือนภัยระดับสูงได้เร็วมาก โดยอิงจาก AI ที่ถูกวิจัยมาดีแล้วของ Xweather
- **Positive:** มีแผนสำรองชัดเจน (Resilience) บอทจะยังคงทำหน้าที่หลักได้แม้ Xweather API key จะถูกระงับ
- **Negative:** เกิดความซับซ้อนทางฝั่ง Business Logic เล็กน้อยในการซ่อน/แสดง ฟีเจอร์เตือนฟ้าผ่าตามสถานะของ API Key
