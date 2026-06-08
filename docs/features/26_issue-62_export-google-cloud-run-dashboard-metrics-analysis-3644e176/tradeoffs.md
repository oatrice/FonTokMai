# Trade-offs: Internal API Endpoint vs Native APM

ในการทำระบบ Monitor ข้อมูล Cron Jobs (เช่น `check_rain_and_alert` และ `fetch_tmd_radar_routine`) ในโปรเจกต์นี้ เราเลือกใช้วิธี **สร้าง HTTP Endpoint (`/api/v1/metrics/export`) แบบ JSON/CSV** ควบคู่กับการบันทึก Metrics ลง Firestore/SQLite แทนที่จะใช้เครื่องมือ Native APM อย่าง Google Cloud Monitoring, BigQuery หรือ Grafana

เอกสารนี้รวบรวมข้อดีข้อเสียของการตัดสินใจดังกล่าว (Architecture Trade-offs)

## 🟢 ข้อดีของการทำ Endpoint แบบ Custom (JSON/CSV)

1. **ฟรีและเบาบาง (Cost-effective & Lightweight)**: 
   - ไม่มีค่าใช้จ่ายเพิ่มเติมสำหรับ Metric Storage หรือ Query Engine แยกต่างหาก (เช่น ค่าใช้จ่ายของ BigQuery หรือ Custom Metrics ใน Cloud Monitoring)
   - ไม่ต้องติดตั้ง Agent หรือผูก SDK ขนาดใหญ่ (Telemetry SDKs) เข้ากับโปรเจกต์

2. **ทำงานร่วมกับทีม (Accessibility)**: 
   - บุคคลที่ไม่มีสิทธิ์เข้าถึง GCP IAM ก็สามารถดึงข้อมูล CSV ไปประมวลผลต่อใน Excel หรือ Google Sheets ได้ง่ายๆ โดยใช้เพียงแค่ `X-Cron-Secret`

3. **ปรับแต่งตาม Business Logic ได้ 100% (High Customizability)**: 
   - สามารถระบุข้อมูลเฉพาะเจาะจง (เช่น `alerts_sent`, `locations_checked`, หรือ `extra_data`) ฝังลงไปในแต่ละ metric record ได้ทันทีและดึงออกมาใช้งานในรูปแบบที่ตรงความต้องการของแอปโดยเฉพาะ

## 🔴 ข้อเสีย (สิ่งที่เครื่องมือ Native APM ทำได้ดีกว่า)

1. **ไม่มีการแจ้งเตือนอัตโนมัติ (Lack of Real-time Alerting)**: 
   - Endpoint ของเรามีไว้เพื่อถูกดึง (Pull-based) แต่ไม่สามารถทำเป็น Alert Rule เช่น "หาก Error Rate สูงกว่า 5% ใน 10 นาที ให้ยิงเข้า Slack ทันที" แบบที่ Cloud Monitoring ทำได้

2. **ขาดการแสดงผล (No Built-in Visualization)**: 
   - เครื่องมืออย่าง Grafana หรือ Cloud Monitoring สามารถวาดกราฟ Time-series, Histogram หรือ Heatmap ได้ทันที ในขณะที่ Endpoint ของเราได้ข้อมูลออกมาเป็นตัวเลข/ตัวอักษร ต้องนำไปพล็อตด้วยเครื่องมืออื่น

3. **ประสิทธิภาพในระยะยาว (Scale & Aggregation Issues)**: 
   - หากเก็บข้อมูลระยะยาวหลายเดือน การ Query เพื่อทำ Aggregation (หา Min, Max, Avg) ในฝั่ง Application ด้วยการดึงเอกสารจำนวนมากจาก Firestore/SQLite จะมี Overhead สูงและอาจทำให้ระบบช้าหรือเกิด Memory OOM 
   - ในขณะที่ BigQuery ถูกออกแบบให้ทำ Columnar scan กับข้อมูลนับล้าน record ได้ในเสี้ยววินาที

4. **การจัดการสิทธิ์ความปลอดภัย (Security)**: 
   - ต้องพึ่งพากลไก Custom Auth (`X-Cron-Secret`) ซึ่งต่างจากการใช้ Service Account (IAM) ของ Google ที่สามารถตั้งค่า Role/Permission ได้รัดกุมกว่า

## สรุป

แนวทาง Endpoint นี้เหมาะเป็น **Lightweight Audit** ที่ตอบโจทย์การวิเคราะห์ผลการทำงานย้อนหลังในช่วงสัปดาห์ (Weekly Reporting) โดยเน้นความง่ายในการเข้าถึงและการลงทุนที่ต่ำ หากในอนาคตจำเป็นต้องมีการตรวจสอบระดับวินาที (Sub-minute monitoring) หรือมีการแจ้งเตือน (Real-time alerting) ควรพิจารณาอัปเกรดไปใช้ Google Cloud Monitoring ร่วมกับ OpenTelemetry แทน
