# Sri Manakula Vinayagar Devasthanam — Google Auth Integration

**Module:** Authentication (Google Sign-In with Strict Phone Verification)
**Developer:** Abhinav
**Impact:** Minimal (Extends Day 2 Auth module without conflicts)

---

## Architecture Overview

The core requirement is that **no unverified accounts** should exist in the system. If a user signs up with Google, they MUST verify their phone number before the account is actually created. If they abort at the OTP step, the account should remain completely uncreated. For returning users, Google Login should instantly grasnt access without requiring an OTP.

Since native Supabase Google Auth instantly creates a database record upon Google sign-in, we will use a **Backend-Driven Verification Flow**. 

### Conflict Check
This flow **does not conflict** with the existing architecture. 
- The database schema already supports users having a `phone`. We simply ensure they also have an `email` field.
- The existing Day 2 OTP flow (MSG91) is preserved.
- The Supabase JWT token generation is untouched. We just manually manage the first-time user creation via the Supabase Admin SDK once the phone is verified.

---

## 1. Flow Breakdown

### A. Account Creation (Signup Flow)
1. **Frontend Trigger:** User clicks "Sign in with Google". The frontend uses the Google Identity Services SDK to obtain a `Google ID Token`.
2. **Backend Verification:** Frontend sends the `ID Token` to FastAPI (`POST /api/v1/auth/google/verify`).
3. **Database Check:** FastAPI securely verifies the token and checks if a user with that email already exists in Supabase. Result: **Does not exist**.
4. **Hold State:** FastAPI does NOT create the user. Instead, it generates a `signup_session_id` (UUID), caches the Google Email and Name in Redis (15-min TTL), and returns `{ "status": "requires_phone", "session_id": "..." }`.
5. **OTP Dispatch:** Frontend redirects to the phone verification screen. User submits their phone number and `session_id`. FastAPI triggers MSG91 to send the OTP.
6. **Final Creation:** User submits the OTP. FastAPI verifies it, retrieves the cached Google details from Redis, and uses `supabase.auth.admin.create_user()` to officially create the account with both the email and verified phone number.

### B. Account Login (Login Flow)
1. **Frontend Trigger:** User clicks "Sign in with Google" and obtains a `Google ID Token`.
2. **Backend Verification:** Frontend sends the token to FastAPI (`POST /api/v1/auth/google/verify`).
3. **Database Check:** FastAPI verifies the token and checks the database. Result: **User exists**.
4. **Instant Login:** Because the user exists (meaning they already verified their phone during signup), FastAPI instantly generates and returns the JWT / Session Tokens. No OTP is required.

---

## 2. Implementation Tasks

**Estimated Effort:** 4 hours
**Dependency:** Day 2 Auth module must be complete.

### 2.1 Update Auth Schemas (`models/schemas/auth.py`)
Add the following schemas:
- `GoogleAuthRequest` — `{ id_token: str }`
- `GoogleAuthResponse` — `{ status: str, session_id: str | None, access_token: str | None }`
- `GoogleOTPVerifyRequest` — `{ session_id: str, phone: str, otp: str }`

### 2.2 Google Token Verification Dependency
- Implement a utility to verify Google ID Tokens using the `google-auth` Python library.
- Validate the token's signature, issuer (`accounts.google.com`), and `aud` (your Google Client ID).
- Extract `email` and `name` from the payload.

### 2.3 Create Google Auth Router (`routers/auth/google.py`)

**`POST /api/v1/auth/google/verify`**
- Verify the `id_token`.
- Query Supabase: `SELECT * FROM users WHERE email = {email}`.
- **If exists:** Generate a Supabase session/JWT for the user and return `{ "status": "success", "access_token": "..." }`.
- **If not exists:** Generate `session_id = uuid4()`. Store `{ "email": email, "name": name }` in Redis at key `google_signup:{session_id}` with EX=900 (15 mins). Return `{ "status": "requires_phone", "session_id": session_id }`.

**`POST /api/v1/auth/google/send-otp`**
- Accept `session_id` and `phone`.
- Check if `session_id` exists in Redis. If not, return 400 (Session expired).
- Validate phone format.
- Generate 6-digit OTP and store in Redis at `otp:{phone}`.
- Trigger MSG91 API to send the OTP.

**`POST /api/v1/auth/google/verify-otp`**
- Accept `session_id`, `phone`, and `otp`.
- Verify the OTP from Redis.
- If valid, retrieve the Google Email/Name from Redis using `session_id`.
- Use Supabase Admin SDK to create the user:
  ```python
  supabase.auth.admin.create_user({
      "email": email,
      "phone": phone,
      "email_confirm": True,
      "phone_confirm": True,
      "user_metadata": { "full_name": name }
  })
  ```
- Generate and return the final access tokens.
- Delete the Redis keys.

---

## 3. Integration Check
- [ ] Redis caching logic implemented for holding the Google Profile state.
- [ ] Supabase Admin API key (`SUPABASE_SERVICE_ROLE_KEY`) is securely used for the final account creation.
- [ ] Users dropping off at the OTP screen do not result in orphaned rows in the `users` table.
