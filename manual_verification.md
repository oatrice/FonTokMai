# 🧪 Manual Verification Artifact: Issue #207 (Vercel Cloud Run API Connection)

## Feature Overview
Dynamic configuration of Next.js API rewrites in `frontend/next.config.ts` using `process.env.BACKEND_URL` for Vercel production deployment and CORS Middleware in FastAPI backend.

---

## 📋 Verification Checklist

### Happy Path 1: Local Development Fallback
- **Pre-requisite**: Do NOT set `BACKEND_URL` in environment.
- **Command**:
  ```bash
  cd frontend
  npm run dev
  ```
- **Verification Step**:
  Open `http://localhost:3000/dashboard` in browser.
- **Expected Outcome**:
  Next.js proxies `/api/runway` to `http://localhost:8000/api/runway`. Runway counter data loads successfully.

### Happy Path 2: Production Vercel Deployment Backend Override
- **Pre-requisite**: Set `BACKEND_URL` environment variable.
- **Command**:
  ```bash
  export BACKEND_URL="https://fonmayang-backend-xyz.a.run.app"
  node -e "
  const fs = require('fs');
  const content = fs.readFileSync('frontend/next.config.ts', 'utf-8');
  console.log('Verified process.env.BACKEND_URL present:', content.includes('process.env.BACKEND_URL'));
  "
  ```
- **Expected Outcome**:
  Next.js API rewrite destination resolves dynamically to `https://fonmayang-backend-xyz.a.run.app/api/:path*`.

### Happy Path 3: CORS Validation in FastAPI Backend
- **Command**:
  ```bash
  curl -I -X OPTIONS http://localhost:8000/api/runway \
    -H "Origin: https://fonmayang.vercel.app" \
    -H "Access-Control-Request-Method: GET"
  ```
- **Expected Outcome**:
  HTTP Response headers contain `Access-Control-Allow-Origin: *` or `Access-Control-Allow-Origin: https://fonmayang.vercel.app`.
