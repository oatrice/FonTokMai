Closes #192

## Overview
Implement a secure Stripe webhook listener that processes payment and subscription events while storing zero PII (Personally Identifiable Information).

# Walkthrough: MR 2 - Zero-PII Stripe Webhook Listener

## Objective
Implement a secure Stripe webhook listener that processes payment and subscription events while storing zero PII (Personally Identifiable Information).

## Changes Made
1. **Added `stripe` dependency**: Updated `requirements.txt`.
2. **Created Stripe Webhook Router**: Added `backend/app/routers/stripe_webhook.py` which listens to `/api/webhooks/stripe`.
   - Validates the Stripe signature using `STRIPE_WEBHOOK_SECRET`.
   - Extracts ONLY non-PII fields: `customer_id`, `transaction_id`, and `amount_total`.
   - Does not log or extract names, emails, addresses, or payment card details.
3. **Transaction Service**: Created `backend/app/services/transaction_service.py` to handle the pseudo-anonymous data storage.
4. **App Registration**: Registered the `stripe_webhook` router in `backend/app/main.py`.
5. **Testing**: Implemented TDD-based tests in `backend/tests/test_stripe_webhook.py` to ensure signature validation and zero-PII data extraction logic work correctly.

## Impact
- Increases the security of the FonMaYang system by minimizing the storage of sensitive financial information.
- Safely processes one-time payments and subscriptions.
- Complies with data minimization and GDPR/PDPA best practices.

# Manual Verification: Zero-PII Stripe Webhook Listener

## Pre-requisites
- Ensure the backend is running.
- Set a dummy `STRIPE_WEBHOOK_SECRET` in your `.env` file (e.g., `whsec_test_secret`).
- Install `stripe-cli` if not already installed.

## Verification Steps
1. **Start the backend server:**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Trigger a test event using Stripe CLI:**
   ```bash
   stripe trigger checkout.session.completed
   ```

3. **Verify Application Logs:**
   - Look for the log: `Saving zero-PII transaction: pi_... for customer cus_... with amount ...`
   - Verify that NO emails, names, or addresses are printed in the log.
   
4. **Invalid Signature Test:**
   - Send a raw POST request to `/api/webhooks/stripe` using Postman or cURL.
   - Include a fake `Stripe-Signature: invalid` header.
   - Assert that the response is `400 Bad Request`.

## Expected Outcome
The system should smoothly receive the webhook from Stripe, validate its cryptographic signature, extract only the pseudonymous reference IDs, and log the pseudo-anonymous transaction.
