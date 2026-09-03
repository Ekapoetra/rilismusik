# Authentication Testing Playbook

## MongoDB checks
- Verify admin/test users exist without exposing `password_hash` in API responses.
- Verify indexes for user email, login attempts, and reset-token expiry.

## API checks
1. Log in through `POST /api/auth/login` and save cookies.
2. Confirm `access_token` and `refresh_token` are HttpOnly and Secure.
3. Call `GET /api/auth/me` with the saved cookies and verify the same user.
4. Confirm invalid passwords increment lockout attempts and successful login clears them.
5. Confirm authenticated API calls also accept the existing Bearer-token fallback.
6. Log in with two independent cookie jars and confirm both `/auth/me` calls remain 200.
7. For a user with `token_version > 0`, refresh device A and confirm device A and B both remain 200.
8. Increment `token_version` and confirm access + refresh tokens on every device become invalid.
9. Google callback detection must use `useLocation().hash` synchronously before protected routes.
10. Exchange `session_id` only from backend; only an existing active `role=label` with the same verified Google email may login.
11. Unknown/admin/artist Google emails must not auto-register and must receive 403.
12. Google Login must issue the same app JWT cookie pair and independent `sid` used by password login.

## Google Auth implementation playbook
- Frontend provider URL comes only from `REACT_APP_GOOGLE_AUTH_URL`.
- Redirect is computed exactly as `window.location.origin + "/label/dashboard"`.
- `AppRoutes` checks `useLocation().hash` for `session_id` before any protected route renders.
- `AuthContext` skips initial `/auth/me` while the callback hash is present.
- Backend exchanges the temporary ID through `EMERGENT_AUTH_SESSION_URL` using `X-Session-ID`.
- Only an existing active `role=label` with a matching Google email is accepted; no Google auto-registration.
- Provider session tokens are never returned or stored raw. Only SHA-256 hashes and audit metadata are persisted.
- Each provider `session_id` is single-use. App access/refresh cookies still use token-version revocation and an independent `sid`.

## Forgot/reset password implementation playbook
- Forgot password always returns the same 200 response for known and unknown emails.
- Tokens are random, expire, are single-use, and are never returned in the public response.
- Transactional links use the same trusted HTTPS request origin when Host/Origin match; foreign origins are ignored.
- Successful reset hashes the new password, marks all reset tokens used, increments `token_version`, and invalidates every prior device session.

## CORS checks
- Public preview/production requests are same-origin (`/api`). Kubernetes/Cloudflare may answer public OPTIONS before FastAPI.
- Send the credentialed preflight directly to backend port 8001 with the configured `FRONTEND_URL` origin.
- Expect that exact origin in `Access-Control-Allow-Origin`.
- Expect `Access-Control-Allow-Credentials: true`.
- Verify unconfigured origins do not receive credentialed CORS approval.
- For a configured custom apex domain, verify both apex and `www` variants are allowed.
- Browser API/file requests must stay relative (`/api/...`) even when `REACT_APP_BACKEND_URL` uses the other domain alias.

## Frontend checks
- Auth requests use credentials.
- Protected routes wait for auth initialization and redirect unauthenticated users.
- Login/register validation errors render as text and do not crash the page.
- Label users may create/edit only their own Draft atau Need Revision release.
- `super_admin` dan `admin_release` dapat menjalankan release workflow actions.
- Admin lain dapat membaca metadata release, tetapi tidak melihat mutation controls dan menerima HTTP 403 dari `/api/releases/{id}/admin/action`.
- Invoice/payment status changes tidak mengubah autentikasi atau sesi pengguna.

## Test credentials
Read `/app/memory/test_credentials.md`; never place passwords in screenshots or reports.