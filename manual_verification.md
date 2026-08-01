# Manual Verification Plan - DevOps Staging, Artifact Cleanup & Build Versioning

- **Branch**: `feat/226-180-229-devops-staging-versioning`
- **MR / Issue ID**: `#226, #180, #229`
- **Date**: `2026-07-31`

---

## 📌 Prerequisites & Environment Setup
1. Backend requires `.env` variables if running locally, or `ENVIRONMENT` and `COMMIT_SHA` to explicitly override versions.
2. Frontend requires `NEXT_PUBLIC_APP_VERSION`, `NEXT_PUBLIC_ENVIRONMENT`, and `NEXT_PUBLIC_COMMIT_SHA`.

```bash
# Launch backend locally
cd backend
ENVIRONMENT=development COMMIT_SHA=local-dev-123 poetry run uvicorn app.main:app --reload --port 8000

# Launch frontend locally
cd frontend
NEXT_PUBLIC_APP_VERSION=0.66.0 NEXT_PUBLIC_ENVIRONMENT=development NEXT_PUBLIC_COMMIT_SHA=local-dev-123 npm run dev
```

---

## 🧪 Verification Scenarios

### Scenario 1: Backend Health Check Returns Version Details
- **Goal**: Verify that the `/health` endpoint exposes correct versioning information based on the environment variables.
- **Steps**:
  1. Start the backend with the environment variables: `ENVIRONMENT=staging COMMIT_SHA=abcdef1`
  2. Send a request: `curl http://localhost:8000/health`
- **Expected Outcome**:
  - HTTP Status: `200 OK`
  - Response Body contains:
    ```json
    {
      "status": "ok",
      "version": "0.66.0",
      "environment": "staging",
      "commit_sha": "abcdef1"
    }
    ```

---

### Scenario 2: Frontend Displays Version Footer
- **Goal**: Verify that the frontend UI displays the injected frontend variables and the fetched backend variables in the footer.
- **Steps**:
  1. Ensure the backend is running on `localhost:8000`.
  2. Start the frontend server with env vars configured.
  3. Navigate to `http://localhost:3000` in the browser.
  4. Scroll down to the page footer.
- **Expected Outcome**:
  - The footer should display a string resembling:
    `v0.66.0 (local-d) [development] | Backend v0.66.0 (abcdef1) [staging]`

---

### Scenario 3: Cloud Run CI/CD Deployment Staging Mapping
- **Goal**: Verify that branch pushes trigger the correct Cloud Run deployment target.
- **Steps**:
  1. Push a commit to the `staging` branch (in GitLab).
  2. Check the GitLab CI/CD pipeline logs for the `deploy` job.
- **Expected Outcome**:
  - The deployment script logs: `Deploying branch staging to environment staging`
  - Cloud Run service being targeted is `fontokmai-api-staging`.
  - Deployment completes successfully and the post-deploy artifact cleanup script runs.

---

### Scenario 4: Artifact Registry Cleanup Script
- **Goal**: Verify that old images in Artifact Registry are cleaned up, keeping the latest 2.
- **Steps**:
  1. Run the script manually simulating `dev` environment:
     ```bash
     cd backend
     ./scripts/cleanup_artifact_registry.sh dev fontokmai-api-dev
     ```
- **Expected Outcome**:
  - The script executes successfully.
  - Logs indicate how many tags were found and which older tags (beyond the most recent 2) were deleted.

---

## 📸 Proof of Verification (Artifacts & Logs)
- **Automated Verification Summary**:
  - `pytest backend/tests/test_deploy_env_sync.py` passed successfully.
