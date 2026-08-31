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

## Test credentials
Read `/app/memory/test_credentials.md`; never place passwords in screenshots or reports.