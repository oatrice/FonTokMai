# Manual Verification Guide

## Step 1: Set up Local Development Environment (Two Bots Strategy)
- Ensure your `.env` has `TELEGRAM_BOT_TOKEN` set to your **DevBot** token, and `ENVIRONMENT=development`.
- Run the FastAPI server locally: `cd backend && uvicorn app.main:app --reload --port 8000`
- Open a LocalTunnel to expose port 8000: `npx localtunnel --port 8000 --subdomain fontokmaidev` (or use your custom subdomain).
- Set the DevBot webhook to your local tunnel URL: 
  ```bash
  curl -s -X POST "https://api.telegram.org/bot<DEV_BOT_TOKEN>/setWebhook" -d url="https://fontokmaidev.loca.lt/api/v1/telegram/webhook"
  ```

## Step 2: Trigger the Webhook Manually via Telegram
- Open your Telegram DevBot.
- Send a Location attachment (Share Location).
- **Expected Result:** The bot should reply with the new extended meteorological data format containing rain intensity and duration, e.g.:
  > 🌧️ ฝนกำลังตกอยู่ที่พิกัดของคุณ ณ ขณะนี้
  > 💧 ความรุนแรง: หนัก (Heavy)
  > ⏱️ คาดว่าจะตกต่อเนื่องประมาณ: 30 นาที
  > (พร้อมปุ่มเรดาร์ต่างๆ)

## Step 3: Verify CI/CD Cloud Run Deployment (Issue #15)
- Go to your GitLab Repository -> Settings -> CI/CD -> Variables.
- Ensure `$GCP_PROJECT_ID` and `$GCP_SA_KEY` (Base64 encoded JSON) are set and marked as `Protected` and `Masked`.
- Create a Merge Request and merge it into the `main` branch.
- Navigate to the GitLab CI/CD Pipeline page.
- **Expected Result:** The pipeline should successfully run the `test` stage, followed by the `deploy_cloud_run` stage. The logs in `deploy_cloud_run` should show successful deployment to Cloud Run and the `curl` command successfully updating the Telegram Webhook to the newly deployed Cloud Run URL.
