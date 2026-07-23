# Task Plan: MR 6 (Issue #198: Milestone Presentation & Security Lock)

## Overview
Implement an anonymized milestone progress indicator and a security kill-switch to unlink public leaderboards during database breaches.

## Acceptance Criteria
- [x] Milestone progress bar endpoint returns anonymized donation totals.
- [x] Kill-switch immediately hides/anonymizes user attribution.
- [x] Waiting list state is activated when the donation lock is enabled (kill-switch active).

## Developer Tasks (TDD)
1. **Write Tests (`backend/tests/test_milestone_lock.py`)**
   - Test that default milestone state returns anonymized donation totals.
   - Test that kill-switch activation returns a waiting list state and anonymizes users.
2. **Implement Feature (`backend/app/routers/milestones.py`)**
   - Create milestone endpoints.
   - Implement the kill-switch logic.
3. **Refactor & Run Tests**
   - Ensure all tests pass with `pytest tests/ -v`.

## QA Tasks
- Verify API responses using `pytest tests/ -v`.
- Generate `walkthrough.md` and `manual_verification.md` for MR review.
