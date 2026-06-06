# Manual Verification Guide

**Issue 60: OCR & Firestore Caching**
- Step 1: Ensure that `GEMINI_API_KEY` and `OCR_SPACE_API_KEY` are configured in your `.env` file (or `GOOGLE_APPLICATION_CREDENTIALS` is set for Cloud Vision) before starting the local server.
- Step 2: Trigger a radar fetch via Telegram (by sending a location and waiting for TMD Radar data).
- Expected Result: The system should extract the timestamp via the OCR Fallback Chain (Cloud Vision -> Gemini -> OCR.space) successfully. Open Firestore and verify that a new document with the frame's MD5 hash is created in the `radar_frame_cache` collection.
- Step 3: Trigger the radar fetch again for the same frame.
- Expected Result: The system should retrieve the timestamp from the Firestore cache, skipping the OCR step.

**Issue 51: Force Weather Data Source**
- Step 1: Open the Telegram bot chat.
- Step 2: Send the command `/rain tomorrow`.
- Expected Result: The bot should reply with weather information fetched explicitly from Tomorrow.io.
- Step 3: Send the command `/rain tmd-radar`.
- Expected Result: The bot should reply with rain predictions calculated directly by the TMD Radar processor.

**Issue 53: Compare API Integration**
- Step 1: Send a location pin to the Telegram bot.
- Step 2: Click the "📊 เทียบข้อมูล" (Compare Data) inline button.
- Expected Result: The response text should cleanly list `tmd-radar` predictions alongside other APIs (like Rainbow and Tomorrow.io) without causing any image formatting bugs.
- Step 3: Check the inline buttons underneath the compare results.
- Expected Result: You should see "✅ บังคับใช้ <Provider>" buttons for each provider. Clicking one should immediately force the bot to fetch and display data from that specific provider.
