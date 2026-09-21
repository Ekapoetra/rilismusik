# Vercel deployment — Rilis Musik frontend

This deployment keeps:

- **Frontend:** Vercel
- **FastAPI backend:** Emergent
- **MongoDB:** Emergent production database
- **R2 / Xendit / SMTP / background workers / scheduler:** Emergent

Vercel acts only as the frontend host and same-origin reverse proxy for `/api/*`.

## Vercel project settings

When importing the GitHub repository into Vercel:

1. Select the branch you want to preview.
2. Set **Root Directory** to `frontend`.
3. Framework should be detected as **Create React App**.
4. Add the environment variable below for **Preview** (and Production later when ready):

```env
EMERGENT_BACKEND_URL=https://YOUR-PUBLIC-EMERGENT-BACKEND-ORIGIN
```

Important:

- Use the backend **origin only**, without a trailing `/api`.
- Example: `https://example-backend.emergent.host`, not `https://example-backend.emergent.host/api`.
- Do **not** put MongoDB, JWT, Xendit secret, SMTP password, or R2 secret credentials in this frontend Vercel project.

Optional frontend variable, only if Google login is used:

```env
REACT_APP_GOOGLE_AUTH_URL=https://YOUR-GOOGLE-AUTH-URL
```

`REACT_APP_BACKEND_URL` is no longer required for the browser build. It may still be set for compatibility, but browser requests intentionally use relative `/api` URLs.

## Why the proxy exists

The frontend code uses `/api` in the browser. `vercel.ts` proxies those requests to the Emergent FastAPI backend while the browser stays on the Vercel domain.

This preserves the existing HttpOnly cookie authentication model and avoids exposing backend secrets to the browser.

## What remains on Emergent

Do not move these to Vercel as part of this frontend deployment:

- MongoDB connection
- FastAPI scheduler
- royalty import/recovery jobs
- balance audit jobs
- duplicate/replacement jobs
- Content ID maintenance
- R2 credentials
- Xendit secret credentials
- SMTP credentials

## Quick smoke test

After deployment:

1. Open `/login`.
2. Log in with a normal test account.
3. Refresh the page; the session should remain authenticated.
4. Open a protected dashboard.
5. Open `/label/royalty`.
6. Confirm an API request to `/api/royalty/months` returns 200.
7. Test Excel/CSV download.
8. Test a direct deep link such as `/label/royalty`; it should load instead of returning Vercel 404.

## Important for the withdrawal-report fix branch

The frontend Vercel deployment does **not** execute `backend/routes/royalty.py`.

To test the latest-withdrawal report fix end-to-end, the Emergent backend must also run the matching backend patch (or the PR must be merged and the Emergent backend republished).
