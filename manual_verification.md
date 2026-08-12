# Manual Verification Plan: Radar Retry, Failover Notice & Photo Compression

## 1. Retry Logic & Live Telegram Progress Notice
- **Scenario**: When TMD radar fetching (e.g. `phs`) encounters a timeout or connection issue on local/production.
- **Verification Steps**:
  1. Trigger `/rain_pro` or `/rain` for Phitsanulok (`phs`).
  2. If the static image fetch times out, the backend retries automatically up to 3 times.
  3. During retry attempts, the Telegram loading message is updated to show retry progress:
     > `⚠️ ไม่สามารถเชื่อมต่อเรดาร์ พิษณุโลก (phs) ได้ (พยายามใหม่รอบ 2/3)...`
- **Expected Outcome**: User is kept informed in real-time on Telegram rather than hanging or failing silently.

---

## 2. Station Failover Notification
- **Scenario**: When primary station (`phs`) fails after max retries and system falls back to secondary station (`chn` ชัยนาท).
- **Verification Steps**:
  1. Run command `/rain_pro default` when PHS radar is offline or timing out.
  2. System detects failure on PHS and automatically fails over to Chainat (`chn`).
  3. Verify log output:
     > `[FAILOVER] Primary station phs (พิษณุโลก) failed. Falling back to station chn (ชัยนาท).`
  4. Verify Telegram message text contains explicit failover notice:
     > `⚠️ หมายเหตุ: เรดาร์พิษณุโลก (phs) ขัดข้อง/หมดเวลาเชื่อมต่อ ระบบจึงสลับไปใช้เรดาร์ชัยนาท (chn) แทนชั่วคราว`

---

## 3. Telegram Photo Automatic Compression
- **Scenario**: Generated PNG images (`radar_latest.png`, `radar_tracking.png`) exceed 400KB.
- **Verification Steps**:
  1. Send photo via `send_telegram_photo`.
  2. Verify log output shows size reduction:
     > `[TELEGRAM] Compressed photo 'radar_latest.png' from 1,399,319 to 245,120 bytes`
- **Expected Outcome**: Payload size drops by ~80% (from 1.4MB to < 250KB), accelerating Telegram photo delivery.

---

## Automated Test Suite Verification
- Ran `pytest backend/tests/test_radar_retry_and_compression.py`: All 2/2 tests PASSED.
- Ran `pytest backend/tests/test_phitsanulok_radar.py backend/tests/test_admin_radar_router.py backend/tests/test_nationwide_radar.py backend/tests/test_deploy_env_sync.py`: All 12/12 tests PASSED.
