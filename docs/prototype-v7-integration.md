# Prototype V7 integration

The admin workspace adopts the V7 visual language while using the existing authenticated API and MongoDB connection. No new database, connection string, migration, demo account, payroll formula, or financial action is introduced.

## Connected views

| View | Source / behavior |
| --- | --- |
| Platform dashboard | `/api/admin/dashboard/v7`, existing dashboard metrics and permission-gated activity logs |
| Work details | Paginated active records from authorized modules, with links to existing operational pages |
| My Work / Team Monitor | Existing work queue service and its effective delegation rules |
| Staff overview | Existing personal/team attendance, performance and leave APIs |
| Leave submission | Existing `/api/admin/leave` validation, persistence and approval workflow |
| Compensation / payroll / payslips | Links to existing permission-protected modules; existing calculations and exports retained |
| Navigation, notification, chat, profile, theme | Existing providers, authenticated identity and components retained |

`/admin/dashboard` uses the new dashboard. `/admin/workspace` is the staff hub. Existing detailed operational pages retain their workflows inside the V7 shell; this change is not a pixel-for-pixel rewrite of every form in the prototype.

## Data semantics

- Active work is deduplicated by source collection and record ID. Total equals new plus in-progress; waiting is a subset of in-progress. A business record can still have multiple distinct work stages in the existing work queue. These measures intentionally differ.
- Preview lists show at most five records. Their length is never used as the overall count; details support pages of up to 100 rows.
- Completed today counts work stages within the current WIB day and the work types visible through the existing ownership/delegation service. It is not a staff productivity score.
- Stage percentages reflect known status transitions. Unsupported percentages remain unavailable.
- Ticket statuses include `waiting_admin` and `waiting_label`. Financial and sensitive sources are permission-gated on the server, before collection reads.
- Sales metrics retain the existing Xendit payment definition. Royalty income is the latest imported report at its stored exchange rate. Total-entity trends describe additions, not changes in the historical total.
- Attendance uses first-login evidence, existing schedules and status corrections. No fake check-out times or work durations are created.
- KPI uses existing backend configuration and evidence. Missing scores stay unavailable and are excluded from the displayed average. Attendance is not added to the KPI score.
- Prototype-only demo identities, simulated AI advice, random chart history and time-correction approval flows are not introduced into the product.
- Failed dashboard reads return 503 and an explicit retry state. Requests are cancelled on filter/account changes; previous account data is not retained. Background refresh retains the current panel until a response arrives.

## Deployment

Deploy backend and frontend together, preferably backend first. The backend already reads `MONGO_URL` and `DB_NAME` from its environment. Keep these values in the deployment secret store. The browser continues to call relative `/api` with the existing cookie authentication and refresh flow.

No production database credentials were available in the implementation workspace. Production MongoDB connectivity, real-account smoke tests, final permissions against current production roles, and deployment are still required. Do not treat the local QA preview as a live database session.

The adapter reads the matching active records in authorized collections to calculate exact counts. For installations with very large active backlogs, measure this endpoint and consider moving the rollup/pagination into indexed aggregation before increasing its polling frequency. The frontend refresh interval is 60 seconds.

## Validation

```sh
python -m unittest discover -s backend/tests -p test_prototype_v7.py -v
cd frontend
yarn test --watchAll=false --runInBand src/components/admin/v7
yarn build
```

The backend contract suite uses dependency stubs and requires FastAPI but no MongoDB connection. It covers permission denial, authorized collection selection, sensitive-field exclusion, deduplication, pagination, status semantics, service failure and the WIB day boundary. Frontend tests cover navigation filtering, stale response cancellation, account isolation and refresh/error behavior.

Local compilation used an isolated npm dependency installation because the Yarn installation did not finish resolving in this environment. Direct dependency versions were retained; the optional `@emergentbase/visual-edits` development overlay was excluded only from that temporary installation, and an AJV peer dependency was installed there. The repository package manifest was not changed. Run the repository's normal Yarn installation/CI before deployment.

Rollback consists of reverting the integration commit and redeploying; no data migration rollback is needed.
