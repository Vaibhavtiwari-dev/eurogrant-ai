# Secret Rotation Policy

This document outlines the steps for rotating critical secrets in EuroGrant AI.

## JWT Secret Key (`JWT_SECRET`)
**Frequency:** Every 90 days, or immediately if compromised.
**Procedure:**
1. Generate a new secret: `openssl rand -hex 32`
2. Update `.env` file or environment variables in staging/production.
3. Restart backend service.
**Impact:** All active sessions will be invalidated. Users will need to log in again.

## Database Password (`POSTGRES_PASSWORD`)
**Frequency:** Every 180 days.
**Procedure:**
1. Connect to Postgres as superuser.
2. `ALTER USER eurogrant WITH PASSWORD 'new_secure_password';`
3. Update `.env` with the new password.
4. Restart backend and worker containers.

## Redis Password (`REDIS_PASSWORD`)
**Frequency:** Every 180 days.
**Procedure:**
1. Update `.env` with the new password.
2. Restart Redis container and all dependent services (backend, worker, beat).

## Stripe Secret Key (`STRIPE_SECRET_KEY`)
**Frequency:** Only if compromised.
**Procedure:**
1. Roll the key in the Stripe Dashboard.
2. Update the `.env` value.
3. Restart the backend service.

## OpenAI API Key (`OPENAI_API_KEY`)
**Frequency:** Every 90 days.
**Procedure:**
1. Create a new key in the OpenAI Dashboard.
2. Update the `.env` value.
3. Restart the backend service.
4. Delete the old key from OpenAI.
