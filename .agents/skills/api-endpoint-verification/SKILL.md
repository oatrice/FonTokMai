---
name: api-endpoint-verification
description: Forces the AI to verify and cross-reference FastAPI endpoint prefixes before writing shell scripts, client code, or API calls.
---

# API Endpoint Verification

When the user asks you to write code that interacts with the backend API (such as a Bash script, Frontend client code, or `curl` commands), **you MUST verify the exact API path before writing the code.**

## The Problem
Previously, the AI hallucinated the API path (e.g., guessing `/api/v1/scheduler/` instead of the actual `/api/v1/cron/`) based purely on file names (`scheduler.py`) and context, leading to broken scripts. 

## Your Rules
1. **Never guess API endpoints.** Do not rely on your general knowledge or the names of the python files.
2. **Always cross-reference.** Before writing the script or code, use `grep_search` or `view_file` to inspect the backend router files (located in `backend/app/routers/` or similar API directories) to find the exact `prefix` or `@router` definitions.
3. **Confirm the Base URL.** Ensure you construct the full URL correctly (e.g., `${BASE_URL}/api/v1/cron/endpoint`).

If you fail to verify the endpoint and guess the path, your code will fail and it is considered a severe error.
