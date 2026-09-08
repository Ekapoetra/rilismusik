# Royalty Balance Adjustment — Implementation & Verification

Date: 2026-09-08. Source: `ROYALTY_ADJUSTMENT_PRD.md` (original uploaded PRD, preserved).

## Explicit user decisions
- Super Admin plus existing `royalty.manage` permission; no global default role expansion.
- Zero starting balance is eligible. Adjustment amount itself must be a positive integer IDR; reason and reference mandatory.
- **Per-label legacy month boundary (B)** selected by the administrator. No inferred global historical cutoff.

## Implemented flow
1. Admin opens **Inject Saldo** (`/admin/royalty-adjustments`), searches/selects label. Also available in admin label detail.
2. Administrator enters amount, last legacy report month, reason, reference and optional verified Believe reference amount.
3. Server-owned 15-minute preview shows total before/after and source breakdown. Preview changes no financial balance.
4. Confirmation writes one complete audit-bearing credit to the existing `balance_transactions` journal. ID `_id = id = AJ-<preview UUID>` is the idempotency constraint.
5. History is searchable/paginated/filterable, with expandable audit details. Void retains the original amount/identity/reference and records reversing status, reason, actor, time and before/after balances.
6. Void/create cannot run during active withdrawal; paid/allocated credits cannot be voided. No financial hard-delete endpoint.

## Architecture
- `royalty_adjustment_models.py`: strict integer-IDR request/response contracts; unknown input fields rejected.
- `royalty_adjustments.py`: admin-only router, label picker, summary, preview/create/history/void. Every route checks existing `royalty.manage`.
- `royalty_adjustment_service.py`: non-mutating source summary, explicit boundary classification, snapshot fingerprint and preview storage.
- `royalty_adjustment_mutations.py`: authoritative one-record credit/void, idempotent retry, concurrency and audit.
- `royalty_adjustment_balance.py`: outstanding adjustment amount = active journal credits minus adjustment portion of paid withdrawals; derived cache refresh.
- `financial_lock.py`: cross-worker per-label Mongo lease (120 seconds, renewed every 20 seconds), shared by adjustment and withdrawal mutations. No unsupported multi-document transactions on standalone Mongo.
- `balance_utils.py`: single-label and bulk available balances include outstanding adjustments before subtracting active withdrawal reservations.
- Existing caches/audit/legacy-period edit/import replacement preserve the manual component; no parallel wallet or duplicate royalty rows.
- Frontend: `pages/admin/RoyaltyAdjustments.jsx`, reusable `components/admin/royalty-adjustments/`, `hooks/useRoyaltyBalance.js`.

### Source classification
- Available, non-settled CSV rows up to the administrator's selected month are Believe Legacy for this reconciliation; later eligible CSV rows are new royalties.
- Before any explicit boundary exists, overview truthfully shows unclassified Believe CSV rather than guessing which records are legacy.
- Most recent recorded boundary is used in the label overview; voiding a credit does not erase its classification audit.
- Monetary CSV values, fees, exchange rates, import contents and existing payout cutoffs are not changed by credit or void.

### Withdrawal integration
- Eligibility is **strictly greater than Rp1,000,000**, not greater-or-equal. Existing KYC/bank/contract and request/payment windows remain.
- Request always reserves the full available balance; client-supplied partial amounts are ignored.
- Complete withdrawal document atomically stores `adjustment_ids`, `adjustment_amount_idr`, `royalty_amount_idr`, and `adjustment_only`. Sensitive allocation fields are omitted from label-facing request/history/computed responses.
- Approval/payment/rejection use the existing workflow. Paid status consumes credits exactly once; rejection releases reservation. Adjustment-only payout has no CSV report range and does not move CSV cutoff.
- Label dashboard and royalty page present simple available balance; visible-page/focus refresh at 15-second intervals updates these views. Withdrawal page uses canonical computed balance when loaded/requested.

## API prefix `/api/royalty/admin/adjustments`
- GET `/labels?q=` — limited searchable label choices, available to royalty managers without granting labels.view.
- GET `/labels/{id}/summary?legacy_period_to=YYYY-MM`
- POST `/labels/{id}/preview`
- POST `/labels/{id}` with `{preview_id}`
- GET `/labels/{id}?q=&status=active|voided&page=&limit=`
- POST `/labels/{id}/{adjustment_id}/void` with `{reason}`

## Final verification
- **17/17 new backend/financial tests, zero skips/XFAIL**, combined run: `test_reports/pytest/royalty_adjustments_final.xml`.
- **5 existing regressions passed**: source-balance reconciliation, admin label available balance, import replacement, legacy-edit preview and legacy-edit commit.
- Confirmed 13,800,000 + 1,450,000 = 15,250,000, full payout; adjustment-only full payout; future CSV after payout; strict 1,000,000 vs 1,000,001 eligibility; reject/void; paid void refusal; double-pay refusal; concurrency; stale previews; pre-write failure; durable post-write retry.
- Main browser retest: 8 consecutive modal open/close cycles, 900,000 + 300,000 = 1,200,000, preview retained across refresh, successful actual credit and void back to 900,000. Responsive 320/768/1024/1440 passed.
- Main browser advanced acceptance: custom role with ONLY royalty.manage can navigate and create credit while `/api/admin/labels` remains 403; history 7 records paginates 5+2; search/status filtering and actor audit correct.
- Initial Iter62/63 report warnings are resolved in `test_reports/iteration_63_followup.json`: dialog readiness decoupled from history reload, existing legacy test polls jobs with authorized user, async test database isolated per loop. **No app test hooks or weaker production authorization added.**
- Final paid-endpoint tests execute real authenticated FastAPI handlers against real isolated Mongo fixtures in process, with the email sender **MOCKED in that same process**. Successful credit/void/public UI calls use real APIs. Fault cases are intentionally simulated in tests only; no mocked production integration or new payment provider.
- Final frontend production build and Python compilation passed. QA users/labels/credits/previews/locks/custom UI role all confirmed zero remaining. No actual user balance/CSV was reconciled automatically, and no real money transfer was executed.

## Next actions / limitations
- User acceptance: manually reconcile an intended label against a verified Believe reference and the correct per-label legacy month.
- Existing production website has not been directly verified; all implementation validation used the current preview environment.
- Optional P2: export adjustment audit history to Excel/CSV. Existing unrelated backlog remains unchanged.