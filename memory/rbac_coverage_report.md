# RBAC Permission Coverage Report (PRD §74)

Generated after Phase B2/C/D/E/F (Unified Admin Roles & Permissions).

- Total permissions in catalog: **76**
- Covered by central path-map `permission_for_request`: **53**
- Referenced by explicit/handler enforcement (assert/has_permission/dict): **76**
- Covered by EITHER mechanism: **76 / 76**
- Orphan (no enforcement reference found): **0**
- Remaining `Depends(require_super_admin)` endpoints (intentional system authority): **6**
- Remaining legacy `role not in (admin_*)` competing checks: **0** (target 0 → legacy bridge removed)

Notes: Super Admin has implicit access to all permissions (`has_permission` short-circuit). New permissions are default-deny to dynamic roles and surfaced via the Configuration Required review.

| Permission | Type | Sensitive | Destructive | PathMap | Handler |
|---|---|---|---|---|---|
| `dashboard.view` | view |  |  | ✓ | ✓ |
| `work.view` | view |  |  |  | ✓ |
| `work.manage` | standard |  |  |  | ✓ |
| `analytics.view` | view |  |  | ✓ | ✓ |
| `analytics.manage` | standard |  |  | ✓ | ✓ |
| `labels.view` | view |  |  | ✓ | ✓ |
| `labels.manage` | standard |  |  | ✓ | ✓ |
| `labels.package` | direct | ✓ |  | ✓ | ✓ |
| `labels.package.request` | sensitive | ✓ |  | ✓ | ✓ |
| `labels.package.request.view` | view |  |  |  | ✓ |
| `labels.package.approve` | approval | ✓ |  |  | ✓ |
| `labels.rate` | direct | ✓ |  | ✓ | ✓ |
| `labels.rate.request` | sensitive | ✓ |  | ✓ | ✓ |
| `labels.rate.request.view` | view |  |  | ✓ | ✓ |
| `labels.rate.approve` | approval | ✓ |  | ✓ | ✓ |
| `labels.blacklist` | direct | ✓ |  | ✓ | ✓ |
| `labels.blacklist.request` | sensitive | ✓ |  | ✓ | ✓ |
| `labels.blacklist.request.view` | view |  |  |  | ✓ |
| `labels.blacklist.approve` | approval | ✓ |  |  | ✓ |
| `labels.accounts` | standard |  |  | ✓ | ✓ |
| `labels.bank` | standard |  |  | ✓ | ✓ |
| `labels.bank.verify` | approval | ✓ |  | ✓ | ✓ |
| `kyc.view` | view |  |  | ✓ | ✓ |
| `kyc.review` | standard |  |  | ✓ | ✓ |
| `artists.view` | view |  |  | ✓ | ✓ |
| `artists.manage` | standard |  |  | ✓ | ✓ |
| `releases.view` | view |  |  | ✓ | ✓ |
| `releases.review` | standard |  |  | ✓ | ✓ |
| `releases.go_live` | sensitive | ✓ |  |  | ✓ |
| `releases.takedown` | sensitive | ✓ |  |  | ✓ |
| `releases.delete` | sensitive | ✓ | ✓ |  | ✓ |
| `payments.view` | view |  |  | ✓ | ✓ |
| `payments.manage` | standard |  |  | ✓ | ✓ |
| `payments.refund` | standard |  |  |  | ✓ |
| `royalty.view` | view |  |  | ✓ | ✓ |
| `royalty.import` | standard |  |  | ✓ | ✓ |
| `royalty.publish` | sensitive | ✓ |  |  | ✓ |
| `royalty.manage` | standard |  |  | ✓ | ✓ |
| `royalty.delete` | standard |  |  | ✓ | ✓ |
| `withdraw.view` | view |  |  | ✓ | ✓ |
| `withdraw.manage` | standard |  |  | ✓ | ✓ |
| `withdraw.approve` | approval | ✓ |  |  | ✓ |
| `withdraw.pay` | sensitive | ✓ |  |  | ✓ |
| `wami.view` | view |  |  | ✓ | ✓ |
| `wami.manage` | standard |  |  | ✓ | ✓ |
| `addon.view` | view |  |  |  | ✓ |
| `addon.manage` | standard |  |  |  | ✓ |
| `support.view` | view |  |  | ✓ | ✓ |
| `support.manage` | standard |  |  | ✓ | ✓ |
| `cms.view` | view |  |  | ✓ | ✓ |
| `cms.manage` | standard |  |  | ✓ | ✓ |
| `contracts.view` | view |  |  | ✓ | ✓ |
| `contracts.manage` | standard |  |  | ✓ | ✓ |
| `access.users.view` | view |  |  | ✓ | ✓ |
| `access.users.manage` | standard |  |  | ✓ | ✓ |
| `access.roles.view` | view |  |  | ✓ | ✓ |
| `access.roles.manage` | standard |  |  | ✓ | ✓ |
| `ui.settings.view` | view |  |  | ✓ | ✓ |
| `ui.settings.manage` | standard |  |  | ✓ | ✓ |
| `migration.view` | view |  |  | ✓ | ✓ |
| `migration.manage` | standard |  |  | ✓ | ✓ |
| `migration.claims` | standard |  |  | ✓ | ✓ |
| `activity.view` | view |  |  | ✓ | ✓ |
| `notifications.view` | view |  |  | ✓ | ✓ |
| `automation.manage` | standard |  |  | ✓ | ✓ |
| `staff.view` | view |  |  | ✓ | ✓ |
| `staff.manage` | standard |  |  | ✓ | ✓ |
| `staff.attendance.view` | view |  |  |  | ✓ |
| `staff.attendance.correct` | standard |  |  |  | ✓ |
| `staff.leave.approve` | standard |  |  |  | ✓ |
| `staff.config.manage` | standard |  |  | ✓ | ✓ |
| `performance.view_own` | standard |  |  |  | ✓ |
| `performance.view_team` | standard |  |  |  | ✓ |
| `performance.view_details` | standard |  |  |  | ✓ |
| `performance.config.manage` | standard |  |  |  | ✓ |
| `performance.period.manage` | standard |  |  |  | ✓ |

## Orphan permissions (no enforcement reference)
- none