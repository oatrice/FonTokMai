# Manual Verification Steps: Testing Infrastructure

## Prerequisites
- Node.js installed (v20+)
- Python 3.11+ installed

## 1. Verify Backend Tests
1. Navigate to the backend directory: `cd backend`
2. Activate the virtual environment: `source .venv/bin/activate`
3. Run the tests: `pytest tests/test_db.py`
4. Expected outcome: The tests should execute and pass without dependency errors.

## 2. Verify Frontend Unit Tests
1. Navigate to the frontend directory: `cd frontend`
2. Run the tests: `npm run test`
3. Expected outcome: Jest should run the `GlassNavbar.test.tsx` file and pass.

## 3. Verify E2E Setup
1. Navigate to the frontend directory: `cd frontend`
2. Run the E2E tests: `npm run test:e2e`
3. Expected outcome: Playwright should attempt to run the `home.spec.ts` test. (Note: initial browser download may be required via `npx playwright install` if running for the first time).

## 4. Verify CI/CD Pipeline
1. Check the GitLab Merge Request pipeline.
2. Expected outcome: `test_frontend` and `test_e2e` jobs should appear and execute alongside `unit_tests`.
