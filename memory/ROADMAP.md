# RILIS MUSIK — Prioritized Roadmap

## P0 — External production blocker
- **Repair Hostinger SMTP credentials.** Preview logs show `535 authentication failed`; release submission email and monthly royalty email remain retry-safe but cannot deliver until credentials are corrected.
- After credentials are corrected, send one controlled release-submission email and one manually triggered monthly summary, then confirm Hostinger delivery logs.
- Publish current code to production and run a controlled user acceptance pass for multi-device auth, bank approval, PPR invoice, and PDF download.

## P1 — Product follow-up
- Add Admin Finance UI for monthly email delivery status/retry (backend status endpoint already exists).
- Add explicit bank-change history timeline and cancellation before approval.
- Add bulk download/archive for generated copyright letters.
- Add migration/report for legacy PPR releases whose invoices were created before the new post-approval flow.

## P2 — Quality & operations
- Link remaining CMS settings dynamically across all landing sections.
- Move FastAPI deprecated `on_event` startup/shutdown hooks to lifespan handlers.
- Add background job notification deep-links by exact job kind instead of the generic migration page.
- Add an optional daily operations digest for failed imports, failed emails, and pending approvals.

## Completed in current cycle
- Multi-device JWT sessions and global revocation.
- Login password visibility.
- Safe admin deletion/restoration and `admin_marketing` access.
- Two-sided bank-account approval.
- Expanded release metadata and submission notifications.
- Post-approval combined PPR invoice.
- Content ID YouTube link.
- Add-on edit/delete/archive.
- Copyright PDF with CMS signature/stamp.
- Monthly royalty emails and background completion notifications.