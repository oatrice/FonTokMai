# แผนการดำเนินงาน: Issue #9: Implement In-Game ModAPI for 0-latency live events

เป้าหมายหลักคือการเปลี่ยนสถาปัตยกรรมการรับข้อมูลเหตุการณ์ในเกมจากการอ่านไฟล์ `.wowsreplay` ไปเป็นการใช้ In-Game Mod ที่ส่งข้อมูลแบบ Real-time (0-latency) ผ่าน HTTP POST Webhooks กลับมาที่ CastBuddy FastAPI server

## ข้อมูลที่ได้รับการยืนยันแล้ว
1. **เรื่อง `simulation_loop`:** เราจะ **ไม่ลบ** ทิ้งครับ แต่จะเก็บไว้เป็นโหมดสำหรับการจำลองข้อมูล (Mock/Test mode) เพื่อให้สามารถทดสอบ UI หรือระบบอื่นๆ ได้โดยไม่ต้องเปิดเกมจริง
2. **เรื่องโครงสร้าง Mod เดิม:** จากการตรวจสอบในโปรเจกต์ ปัจจุบันยังไม่มีโครงสร้างหรือ boilerplate ใดๆ ของ WoWS Mod เดิมอยู่เลย (มีเพียงแค่เอกสารที่เคยกล่าวถึงใน Issue #5) ดังนั้นเราจะสร้างโครงสร้างไฟล์สำหรับ Mod ขึ้นมาใหม่ทั้งหมดตั้งแต่ต้น

## User Review Required

> [!IMPORTANT]
> 1. World of Warships (BigWorld engine) มักจะใช้ Python เวอร์ชันเก่า (เช่น Python 2.7) สำหรับ Mod API ภายในเกม ดังนั้นโค้ดของฝั่ง Mod จะต้องถูกเขียนโดยใช้ Standard Library ที่เข้ากันได้กับสภาพแวดล้อมนั้น (เช่น `urllib2` หรือ `httplib`)
> 2. เนื่องจากเรายังไม่มี Boilerplate ของเกมนี้เลย การเขียน Mod อาจจะต้องอิงจากเอกสารทั่วไป หรืออาจจะทำเป็นโครงสร้างพื้นฐานส่ง HTTP Request ไว้ก่อน และหากติดตั้งในเกมแล้วมี Error เราอาจจะต้องพึ่งพาการส่ง Log Error จากฝั่งผู้ใช้มาเพื่อแก้ไขในภายหลัง

## Proposed Changes

### 1. ฝั่ง CastBuddy Server (FastAPI)
เปิดรับ Webhook จาก In-Game Mod

#### [MODIFY] [server.py](file:///Users/oatrice/Software-projects/CastBuddy/api/server.py)
- เพิ่ม Endpoint ใหม่ `POST /api/events`
- นำ Payload ที่ได้รับส่งเข้าไปประมวลผลผ่าน `process_raw_event(payload)` เพื่อให้ออกเป็นเสียง (TTS) และขึ้นจอ OBS ทันที
- ปรับโครงสร้างเล็กน้อยเพื่อแยกระหว่างโหมดเปิดใช้งานจริง (รับ Webhook) กับโหมดจำลอง (`simulation_loop`)

### 2. ฝั่ง World of Warships Mod
สร้างสคริปต์ Mod ตั้งต้นเพื่อดักจับเหตุการณ์และส่งออกไปที่ Server

#### [NEW] [CastBuddyMod.py](file:///Users/oatrice/Software-projects/CastBuddy/wows_mod/CastBuddyMod.py)
- สร้างโฟลเดอร์ `wows_mod/` ใน Root Project
- สร้างสคริปต์ `CastBuddyMod.py` ซึ่งจะพยายาม Hook ไปที่ระบบของเกม เช่น `events.onBattleStart` (ถ้ามี API รองรับ) 
- สร้างฟังก์ชันส่ง HTTP POST request แบบ non-blocking หรือแบบง่ายผ่าน `urllib2` ไปที่ `http://127.0.0.1:8000/api/events` ทันทีที่เกิดเหตุการณ์

## Verification Plan

### Automated Tests
- เพิ่ม/ปรับปรุง Test case ในฝั่งเซิร์ฟเวอร์สำหรับ Endpoint `POST /api/events` ว่าสามารถรับและตอบสนองต่อ JSON event ได้อย่างถูกต้อง (ตามกระบวนการ TDD)

### Manual Verification
- รันเซิร์ฟเวอร์ `CastBuddy`
- ลองนำไฟล์ `CastBuddyMod.py` ไปใส่ในโฟลเดอร์ `res_mods/<version>/` ของตัวเกม World of Warships
- เปิดเกมและเข้าสู่โหมด Training Room (หรือโหมดปกติ) 
- ตรวจสอบว่าเหตุการณ์ในเกมถูกส่งกลับมาที่ Dashboard และ OBS ได้แบบ Real-time
