# Rilis Musik on Vercel

The frontend and FastAPI API remain in the existing Vercel project. `vercel_production_app:app` replaces the restricted preview wrapper while retaining each route's authentication, role, KYC and ownership checks. MongoDB Atlas and the existing private R2 bucket remain the data stores.

## Background processing

An explicit private `queue` service in the same Vercel project runs Queues subscribers for imports, cached analytics, emails and scheduled work. Queue messages contain a task ID. Arguments reside in private R2; MongoDB records a dispatch outbox, execution lease and completion. Repeated completed deliveries do not execute again. Failed dispatches are recoverable. This does not promise exactly-once email delivery after a provider succeeds but a process terminates before recording completion.

CSV inputs already in R2 are streamed without staging multi-gigabyte files in `/tmp`. Checkpoints resume completed rows and deterministic row IDs prevent duplicate insertion after interruption. Analytics build in staging and preserve the previous live collection until the replacement is complete. Publishing royalty credits now uses an atomic per-label import marker to prevent duplicate balance increments if execution stops between the balance write and ledger insertion.

Recurring private queue ticks are seeded when the Production deployment serves an existing production domain. Preview deployments do not start recurring financial/email jobs. Old deployment ticks stop scheduling after a new production deployment takes over. A queue backlog or prolonged outage can delay work; inspect Vercel Queues and the application's task status rather than manually publishing incomplete imports.

## Uploads

Files above 3 MiB use signed direct uploads to R2, then invoke the existing upload handler with the same authenticated request. Finalization preserves its role, ownership, content and business validation. Generic media uploads support up to 200 MiB per file; royalty CSVs retain their separate streaming upload path. Abandoned transient uploads expire after two hours and are cleaned by bounded maintenance jobs.

## Deployment and verification

Deploy the branch with Production environment variables. Keep the current maintenance deployment available for rollback. `/api/runtime-health` publishes one harmless private queue probe per deployment and returns `background_jobs: ready` only after the consumer completes; it exposes no account data or secrets. `/api/admin/deployment-check` retains superadmin authentication for collection counts. Verify Preview build, private queue delivery, database connection, login and the initial dashboard before promoting Production. Do not test real payouts or send customer emails as a deployment check.

Required existing environment values: MongoDB (`MONGO_URL`, `DB_NAME`), auth (`JWT_SECRET`, `FRONTEND_URL`), R2 storage and SMTP; Xendit settings for live payment features. Google login needs matching frontend `REACT_APP_GOOGLE_CLIENT_ID` and backend `GOOGLE_CLIENT_ID`. Queue authentication uses Vercel's deployment identity, so no new queue secret is needed. `UPLOAD_DIR` and deployment mode are set by the Vercel entrypoint; the old preview environment value does not reactivate the preview write guard.

Offline checks cover task replay, overlapping delivery, dispatch recovery, CSV continuation and exact money totals, interrupted publish credits, cross-instance analytics scheduling, upload ownership/content/role checks and production route authentication. The Services builder uses explicit queue triggers instead of relying on automatic subscriber discovery. Live queue availability and real Google OAuth require deployment verification.
