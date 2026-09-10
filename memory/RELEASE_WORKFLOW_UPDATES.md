# Release workflow update — 2026-09-10 / Iter70

## User-approved requirements
1. **URL Web Artist / Channel YouTube Asli** on label submission is optional. Nonempty URLs still validated.
2. Track-level featuring for Single, EP and Album; select an owned saved artist or add a new artist. Track featuring is independent of release-level featuring.
3. Maximum **7 distinct successfully submitted releases per label account per WIB day**. Draft saving does not consume quota. Same release resubmitted on the same day counts once; submitting on another day consumes that day's quota. Reset00:00 Asia/Jakarta. Display quota to label.
4. Admin/label release lists show artwork in the title/artist area. Web releases use canonical uploaded artwork. Explicit `imported_legacy` releases allow owner label/admin `releases.review` to upload or replace dashboard-only art marked **Cover internal — tidak mengubah DSP**. Canonical artwork and DSP delivery remain unchanged; actual DSP cover changes require Edit Cover support workflow.
5. Admin/support marks a Takedown support ticket **Selesai**: linked Live release becomes canonical status `taken_down`. Reject/cancel/other categories do not trigger this transition.

## Implementation
### Optional URL / featuring
- `validate_artist_web_url` permits missing/empty value and validates nonempty URLs; submission required-field list no longer includes that URL.
- UI field marked optional, info-step validation/copy updated. Missing URL rendered as a dash in metadata.
- `TrackIn.featured_artists` uses existing artist-credit schema. Save/edit/read/submit preserve arrays and compatible legacy featuring fields. All release+track credits validated before profile writes; batch resolver supports validation-only planning and profile/name dedupe. Owned saved artist IDs resolve to canonical social-link snapshots; foreign IDs fail.
- Shared artist editor reused for track featuring; track detail lists its own guests, not release-level guests. Single/EP/Album allowed. Rejected releases now editable/resubmittable alongside Draft/Need Revision to honor the approved retry rules.

### Quota
- `GET /api/releases/submission-quota[?release_id=...]`: own-label count, limit, remaining, pending, WIB day/reset timestamp and `already_counted` for current release.
- `label_daily_submissions`: Mongo `_id=label_id:WIB-day`, max7 atomic pending/committed entries; seeded with earlier successful web submissions on first access that day.
- Per-release operation lease prevents duplicate concurrent submit. Failure releases pending reservation; successful status/history atomically carries `quota_token`/`submission_day`, allowing interrupted ledger updates to reconcile from the receipt. Quota remains consumed after a successfully submitted release is later deleted.
- Mongo commit condition checks `$$NOW` in Asia/Jakarta against reserved day; a commit crossing midnight is rejected rather than assigned to the wrong day. New day's ledger naturally resets without a cron job.
- Dashboard/list/wizard show quota with30-second/focus refresh. Full quota disables a new submission, not draft saving, and does not falsely mark valid files invalid. Same-day previously counted release remains allowed at7/7.

### Artwork
- `POST/GET /api/releases/{id}/internal-cover`; uploads require verified active label owner or admin review permission. `releases.view` admins, including Finance, may read but not replace artwork unless they also have review.
- Private R2 `release-internal/` prefix blocked by generic public file route. Authenticated cookie/Bearer image route returns no-store/nosniff. JPG/PNG validation,10MB/25MP limits,100px minimum, normalized max1600px image.
- Separate `release_internal_covers` object record and release `internal_cover_url`/`internal_cover_updated_at`; never change `cover_url`, general metadata timestamp, UPC, ISRC or DSP status on artwork edit. Concurrent replacement serialized, failures compensated, previous object cleanup and audit recorded.
- `ReleaseArtwork` shared by both list/detail views; full-image contain fit, placeholder fallback, internal badge, upload/replace dialog explicitly directs DSP changes to Edit Cover support.

### Takedown
- Only `support.manage` completion of the linked Takedown ticket can invoke the narrow sync service. Release ownership must match ticket label. Live -> taken_down records status history, actor/time/ticket ID and activity log once; already taken_down is idempotent.
- Invalid/missing/non-live release leaves ticket unfinished. Cancelled/rejected ticket must be reopened before completion. If ticket update fails, compensate only this operation's unchanged release transition. Reopening a completed ticket does not restore Live.
- UI confirmation before Done, admin/label synced-status message. No external DSP call is made: admin's completion records that the takedown process is complete.

## Verification / resolved findings
- Initial `iteration_70.json`:7/8 backend cases passed; internal-cover upload500 fixed by replacing incorrectly manually invoked `require_label(request,user)` with proper FastAPI `Depends(require_kyc_for_label_user)` on the upload route. Access/KYC policy was not weakened.
- Targeted internal-cover retest now passes. Corrected erroneous test expectation that Finance could not read covers: `releases.view` explicitly permits reading; finance write403 verified. Total8 backend scenario groups passed across initial/targeted runs.
- Real R2/browser: canonical web thumbnail loads; label uploads legacy internal art; admin sees/replaces it; badge/refresh/authenticated image loads work, no row navigation side effect. Canonical cover/UPC unchanged after both edits. Responsive320/768/1024/1440 verified for lists/artwork/track editor.
- Browser: empty URL advances, new track guest and saved artist `Simpan` persist independently after save/reload; release guest unchanged. At7/7 draft still saves, new submit disabled with correct quota message and truthful valid-files status. Rejected same-day-counted release editable and submit enabled at7/7. No actual UI submit was sent during these fixture-state checks, avoiding more external emails.
- Found a real admin editor race: two initial ticket GET responses could overwrite user-selected Done/note. Network timing confirmed second response after selection. Fixed with request sequencing and dirty-field protection; native option values kept separate from translated labels. This was NOT a generic i18n state bug. Confirm-cancel leaves state unchanged; confirm applies Done and linked taken_down, label sees synced message, one release history entry verified.
- Final frontend build compiled successfully without lint warnings (`/tmp/iter70-final-build.log`); existing bundle-size advisory remains nonblocking. Cover retest: `test_reports/pytest/iter70_internal_cover_retest.xml`.
- All owned main UI user/label/releases, quota ledger, artist, support ticket, canonical/internal R2 artwork and operation locks cleaned by exact IDs. No real user release/package/balance/CSV modified. Existing admin credentials unchanged, temporary credentials retired in memory.

## Important outstanding observation
**P1 — SMTP notification timeouts during concurrent submit testing.** The test agent exercised real parallel submissions and existing asynchronous email fanout logged connection timeouts for some notifications. Submitted release records, quota enforcement and in-app status remained successful. SMTP queue/throttling/retry behavior was NOT changed or verified as fixed in this scope. Avoid repeating bulk external mail tests; use isolated outbound transport suppression for future stress tests. Do not claim all notification email deliveries passed.

## Next
- User acceptance of the5 requested changes.
- Prioritize SMTP fanout reliability separately. Optional enhancement: queue and retry failed notification emails with admin-visible delivery status.
- Existing other backlog remains deferred; no payments, automatic DSP cover changes or additional providers introduced.

## References
Backend: `release_submission_quota.py`, `release_internal_cover.py`, `ticket_takedown_service.py`, `release_workflow_service.py`, `artist_social_service.py`, `releases.py`, `tickets.py`, `models.py`.
Frontend: `useSubmissionQuota.js`, `SubmissionQuota.jsx`, `ReleaseArtwork.jsx`, release-form state/artist/track/assets editors, release list/detail pages, admin TicketDetail request/dirty guards.
Reports: `iteration_70.json`, `iteration_70_followup.json`; tests `backend/tests/test_iter70_release_quota_cover_takedown.py`.