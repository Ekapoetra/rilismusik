# Content ID — Creator Copyright Declarations

## Original request and approved scope
User requested additional fields ONLY for label **Pengajuan Content ID**: creator full legal name according to KTP, NIK, digital signature uploaded as PNG/JPG or drawn on screen, automatically generated copyright declaration PDF downloadable from admin support tickets for manual submission to Believe. Formal-premium design, **no company letterhead and no letter number**.

User selected BOTH single signer for a full release and one letter per creator with selected songs. Implemented as one creator by default with Select All Songs, plus Add Creator/per-creator song assignments. User additionally requires a creator/author KTP photo, available in admin support. All identity/signature/KTP fields are mandatory before new claim submission.

Source example: `https://customer-assets-cm19k8pv.emergentagent.net/job_lanjut-core/artifacts/rghe4e88_SURAT%20PERNYATAAN%20KEPEMILIKAN%20HAK%20CIPTA%20ATAS%20LAGU.docx`.
Template includes the supplied ownership/noninfringement assertion, legal-responsibility paragraph, closing declaration, domicile, city/date/signature, and KTP appendix. Domicile and signing-city inputs added to match the example; signing date generated server-side in Asia/Jakarta, not the example's fixed city/date. Joint-author wording avoids asserting sole authorship when creators share a selected song.

## Implemented — 2026-09-09 (Iter68–69)
- Claim-only UI with track selection, 1–20 creators, unique 16-digit NIK strings preserving leading zeros, name/domicile/signing city, sole/joint authorship, required KTP and signature, and recorded label consent. Existing YouTube links and originality checklist retained. Content ID revoke and other ticket categories unchanged; old claim tickets display an empty document section rather than requiring retroactive uploads.
- `signature_pad` for actual canvas input, undo/clear, upload alternate, responsive stroke preservation. Dot-only input is not accepted as a completed signature; server rejects uniformly blank/tiny signatures and crops only blank margins with padding so real strokes remain readable in the letter.
- PNG/JPEG decoded/validated/re-encoded without EXIF. Signature up to5MB, KTP up to10MB,25MP cap. Images fit without stretching/cropping important content. File checks do **not** verify whether the identity is genuine or whether the signer is legally the author.
- Formal unbranded A4 ReportLab PDF per creator, selected tracks/ISRC and release UPC, visual signature, and separate KTP appendix. Long metadata and many tracks paginate. Letter is an immutable snapshot; changing a release later does not rewrite it. No CMS signature/stamp, company logo, letter number or automatic Believe request.
- Real private R2 storage under `contentid-private/`; no client-supplied keys/URLs, no public/signed R2 URLs returned. Common public file route blocks this prefix, including normalized paths. Authenticated owner/support-authorized binary routes return no-store and nosniff. General ticket payload stores document summaries, not full NIK or storage keys. Dedicated metadata route is authorized/no-store; UI initially masks NIK and can show private KTP/signature previews.
- Creator files are held locally until submit; staged uploads are bound to owner+release+kind, reserved during PDF generation and immutable after ticket creation. All selected songs must be assigned, one form per NIK, and no cross-owner/cross-release/reused-bound assets accepted.
- Generation completes BEFORE ticket insertion/notification. Failure returns assets to staged and compensates partial PDFs; stable request UUID prevents duplicate tickets on retry. Existing-ticket retry repairs reserved bindings. Maintenance handles24h unused staged uploads and stale interrupted generation requests; submitted documents are not expired by that cleanup.
- Asset/identity reads and PDF downloads generate audit events containing IDs/counts, not full NIK/signature/KTP contents.

## Files / API
- Models: `backend/contentid_models.py`, claim fields in `backend/models.py`.
- Service: `routes/contentid_assets.py`, `contentid_pdf.py`, `contentid_service.py`, integration in `tickets.py` and `server.py`.
- Frontend: `ContentIdClaimForm.jsx`, `CreatorSignature.jsx`, `CreatorImageInput.jsx`, `contentIdForm.js`, `ReleaseSelectOptions.jsx`; existing support form and label/admin details; shared `ContentIdDocuments.jsx`.
- `POST /api/tickets/content-id/assets` — owner upload (multipart release_id/kind/file/signature_mode).
- `GET/DELETE /api/tickets/content-id/assets/{id}` — authorized private read / uploader-only unbound deletion.
- `GET /api/tickets/content-id/tickets/{ticket_id}` — authorized declaration metadata.
- `GET /api/tickets/content-id/tickets/{ticket_id}/{document_id}/pdf` — authorized attachment download.
- Existing `POST /api/tickets/label/create`: new claims require `content_id_request_id`, selected `content_id_track_ids`, `content_id_creators[]`, and `content_id_consent:true` in addition to existing claim fields.
- Collections: `contentid_assets`, `contentid_declarations`, `contentid_requests`; summary refs on `support_tickets`. Existing Cloudflare R2/JWT cookie integration reused. No new credentials or auth-provider changes.

## Verified
- Final combined backend regression **14/14 passed**: `test_reports/pytest/contentid_final.xml` using `test_iter68_content_id_claim.py` + `test_iter69_content_id_followup.py`. Includes real R2, multiple creators, immutability, access isolation, validation, failure rollback in isolated unit tests, and long-PDF pagination. Framework `python_multipart` deprecation warning is nonblocking.
- Actual drawn-signature browser submission succeeded; owner downloaded PDF and viewed KTP/NIK; support admin downloaded PDF and viewed KTP/signature. Canvas ink survived320/768/1024/1440 resizing with no document/modal overflow. Admin preview and download-after-dialog-close passed at these widths.
- PDF pages visually inspected: clear drawn signature, correct selected tracks, full uncropped fake KTP on appendix, no letterhead/letter number. Synthetic artifacts: `test_reports/iter68_ui_drawn_final.pdf`, `iter68_ui_drawn_final/page_1.png`, `page_2.png`; multi-creator sample and pagination artifacts from Iter69 retained locally.
- Final `CI=false yarn build` compiled successfully, no lint warnings (`/tmp/contentid-final-build.log`). Existing bundle-size advisory remains nonblocking.

## Important testing lessons / closed findings
1. Edge changes `Cache-Control: no-store, private` to `no-store, no-cache, must-revalidate`. Original tests incorrectly asserted exact equality. RFC9111§5.2.2.5 no-store prohibits both shared and private cache storage; corrected tests require no-store, no public directive, Age0, and test actual unauthorized access after owner download. No weakening of app privacy headers.
2. First modal forced clicks were swallowed by the existing KYC loading gate when the test wait used a nullable expression that passed before DOM existed. Proper selector: `[data-testid="label-route-content"]:not([aria-hidden="true"])` must be attached. **KYC remains fail-closed. Do NOT apply the suggested optimistic-unverified-access workaround.** Modal then opens reliably; repeated open/cancel passed.
3. Multi-expression JSX release options picked up invalid inline spans; `ReleaseSelectOptions` creates native text-only options. Final browser asserted zero `option span` nodes and unchanged selected release IDs.
4. Forced PDF click immediately during dialog exit animation is not actionable. Wait for private-image dialog to become hidden; admin download then passes. No API download defect.

## Cleanup / limitations / next actions
- Temporary main account `iter66-ui-bebbb29e@example.com`, its release/label and other test fixtures retired. Final cleanup removed exactly2 private assets,1 PDF declaration,1 owned UI ticket and corresponding R2 objects/comments/notifications/audit IDs after preserving only synthetic local samples. No real user KTP, release/package/balance or CSV modified.
- Isolated cleanup initially imported R2 module before loading env; corrected env loading order and verified deletion. Application integration itself was operational throughout.
- Tests require a seeded isolated fixture (`python /app/tests/iter66_ui_fixture.py seed`); they skip cleanly when it is absent. Renderer dependency `pypdfium2` is test-only; production PDF uses already installed ReportLab/Pillow.
- Signature is a visual uploaded/drawn image, **not a certified electronic signature**. No automatic identity/authorship verification and no guarantee of Believe acceptance. Admin/creator must review the legal statement before sending it manually.
- Next: user acceptance on actual creator data and preferred wording. Optional future enhancement: a private PDF preview before final ticket submission. Other backlog remains deferred.