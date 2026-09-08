# PRODUCT REQUIREMENTS DOCUMENT

## Rilis Musik — Royalty Balance Adjustment & Legacy Reconciliation

**Version:** 1.0  
**Status:** Proposed  
**Target:** AI Development Agent  
**Scope:** Admin Royalty Adjustment + Legacy Royalty Reconciliation  
**Priority:** High

---

## 1. Product Context

Rilis Musik is a live music distribution/aggregation platform. Royalty data from Believe is provided as CSV, downloaded, and imported into the Rilis Musik system.

There is currently a reconciliation problem affecting a number of Labels that still have **legacy royalty balances** from the previous Believe system/data migration.

The affected data is specifically legacy data: old Believe royalty balances that remain available in Rilis Musik.

Current distinction:

- Labels with **legacy royalty balance = Rp0** are considered safe/settled.
- Labels with **legacy royalty balance > Rp0** are the affected population requiring reconciliation.
- New/current royalty data must not be unnecessarily mixed with the legacy reconciliation process.

Repeated attempts to correct the legacy display/calculation through the existing import/processing flow have not produced sufficiently reliable results.

Therefore, Rilis Musik needs a controlled mechanism for adding a verified royalty balance independently from the legacy CSV calculation.

---

## 2. Core Product Decision

Introduce an **Admin Royalty Balance Adjustment** mechanism.

For internal UI purposes, this may be presented as:

> **Inject Saldo**

Technically, it MUST be treated as a separate royalty source/ledger entry and **not as a direct overwrite of the Label's balance field**.

The adjustment must:

1. Add a verified amount to the Label's available royalty balance.
2. Exist independently from the Believe CSV legacy source.
3. Be fully auditable.
4. Be visible as a separate source in the Admin Console.
5. Immediately affect the royalty balance shown in the Label account.
6. Follow the existing withdrawal rules.
7. Not modify or overwrite the original legacy CSV data.
8. Not alter unrelated features or business logic.

---

## 3. Critical Scope Restriction — DO NOT MODIFY OTHER FEATURES

This PRD is specifically for the Royalty Balance Adjustment / Legacy Reconciliation mechanism.

The implementation MUST be performed **according to the existing Rilis Musik application structure, architecture, database conventions, routing, authentication, authorization, UI components, and business logic already built in the system.**

The AI Development Agent MUST:

- Inspect the existing implementation before making changes.
- Reuse existing components, services, APIs, models, tables, styles, and patterns wherever appropriate.
- Make the smallest safe changes necessary.
- Preserve all existing functionality outside this PRD.
- NOT redesign unrelated pages.
- NOT change unrelated workflows.
- NOT change existing withdrawal behavior except where necessary to recognize the adjusted balance as part of the existing available balance.
- NOT change royalty import behavior for new/current data unless technically required to integrate the separate adjustment source.
- NOT rewrite the royalty system unnecessarily.
- NOT perform broad refactoring unrelated to this requirement.
- NOT remove existing data.
- NOT alter historical CSV records.
- NOT change permissions or roles globally.

### Golden Rule

> **Implement this feature on top of the existing system. Do not rebuild the existing system around this feature.**

If an implementation decision would require changing an unrelated feature, preserve the existing behavior and document the conflict rather than making an uncontrolled change.

---

## 4. Problem Statement

The current legacy royalty data can display a different amount on the Rilis Musik website compared with the original Believe database/source.

Because the legacy data has already passed through CSV export, import, transformation, and processing, repeatedly changing the existing calculation/import logic introduces uncertainty.

The objective is therefore not to continuously repair the legacy calculation engine.

Instead:

> Preserve the legacy source as historical data and introduce a controlled adjustment layer that can establish a verified balance for affected Labels.

This creates a clean separation between:

- Original Believe legacy data
- Administrative reconciliation adjustments
- Future/new royalty data
- Withdrawals

---

## 5. Data Source Architecture

The royalty balance should conceptually support separate sources:

| Source | Description |
|---|---|
| `BELIEVE_LEGACY` | Historical data imported from Believe CSV. Must remain intact. |
| `ADMIN_ADJUSTMENT` | Manually added verified balance correction. Fully auditable. |
| `NEW_ROYALTY` | Current/future royalty data imported through the existing system. Existing behavior must remain unchanged. |
| `WITHDRAWAL` | Existing withdrawal/debit records. |

Conceptually:

```text
Available Balance
=
Legacy Royalty
+ Admin Adjustments
+ New Royalty
- Withdrawals
```

The actual implementation MUST follow the existing database and financial architecture.

Do not create duplicate balance systems if the existing architecture already has a suitable ledger/wallet mechanism.

---

## 6. Legacy Data Rules

Legacy Believe data must be treated as historical source data.

Required behavior:

- Do not overwrite the original legacy amount.
- Do not delete legacy records.
- Do not modify CSV source records simply to make the displayed balance match.
- Do not silently replace legacy values with manually entered values.
- Preserve the ability for Admin to distinguish legacy balance from adjustment balance.

The adjustment layer exists specifically so reconciliation can happen without corrupting the historical source.

---

## 7. Admin Action — Inject Saldo

Provide an Admin action:

> **Inject Saldo**

Recommended formal terminology internally:

> **Royalty Balance Adjustment**

The button should be available only to an appropriately authorized Admin role according to the existing Rilis Musik permission structure.

Do not introduce a new global role system unless the current architecture requires it.

---

## 8. Adjustment Flow

Recommended flow:

```text
Admin Console
     ↓
Select Label
     ↓
View Current Royalty Balance
     ↓
Enter Adjustment Amount
     ↓
Enter Reason
     ↓
Enter Reference / Source
     ↓
Review Adjustment
     ↓
Confirm
     ↓
Create Adjustment Ledger Entry
     ↓
Available Balance Updated
     ↓
Label Account Immediately Reflects New Balance
```

The action must not directly edit a balance number without creating a corresponding auditable record.

---

## 9. Required Adjustment Fields

Every adjustment should store, at minimum:

| Field | Requirement |
|---|---|
| Adjustment ID | Unique identifier |
| Label ID | Target Label |
| Amount | Monetary adjustment amount |
| Currency | Currency of adjustment |
| Adjustment Type | e.g. `LEGACY_RECONCILIATION` |
| Source | `ADMIN_ADJUSTMENT` |
| Reason | Required |
| Reference | Required/recommended for legacy reconciliation |
| Created By | Admin user ID |
| Created At | Timestamp |
| Status | Active / Voided |
| Related Legacy Balance | Recommended |
| Existing Balance Before Adjustment | Recommended |
| Balance After Adjustment | Recommended |

If the current architecture has equivalent fields, reuse them rather than creating redundant fields.

---

## 10. Reconciliation Information

For legacy reconciliation, Admin should be able to record the reference amount used to establish the correction.

Example:

```text
Label:
ABC Music

Believe Legacy Reference:
Rp 15.250.000

Current Rilis Musik Balance:
Rp 13.800.000

Adjustment:
+ Rp 1.450.000

Resulting Balance:
Rp 15.250.000
```

The system must make it possible to answer:

> **Why did this Label receive this adjustment?**

The answer must be available from the adjustment history/audit record.

---

## 11. Label Balance Behavior

The adjustment must immediately affect the royalty balance shown in the Label account.

Example:

```text
Existing Balance
Rp 13.800.000

Admin Adjustment
+ Rp 1.450.000

Available Balance
Rp 15.250.000
```

The Label should see:

```text
ROYALTY

Available Balance
Rp 15.250.000
```

The Label-facing experience should remain simple. Internal source breakdown is primarily an Admin function.

---

## 12. Withdrawal Rule — CRITICAL

The existing Rilis Musik withdrawal rule MUST be preserved.

### Current business rule

A Label can withdraw royalty only when its available balance is:

> **GREATER THAN Rp1.000.000**

The Label **cannot specify the withdrawal amount**.

When the balance qualifies for withdrawal, the Label must withdraw:

> **THE ENTIRE AVAILABLE BALANCE**

Therefore:

```text
Balance <= Rp1.000.000
→ Withdrawal unavailable

Balance > Rp1.000.000
→ Withdrawal available

Withdrawal amount
→ Always 100% of available balance
```

### Important integration rule

The Admin Adjustment must be included in the available balance used by the existing withdrawal system.

Example:

```text
Legacy Balance       Rp   900.000
Adjustment            Rp   300.000
──────────────────────────────────
Available Balance     Rp 1.200.000

Withdrawal available: YES

Withdrawal amount:
Rp 1.200.000
```

After successful withdrawal:

```text
Available Balance
Rp 0
```

---

## 13. Exact Threshold Behavior

The qualification condition is:

```text
balance > 1,000,000
```

Therefore:

| Available Balance | Can Withdraw? | Withdrawal Amount |
|---:|:---:|---:|
| Rp0 | No | — |
| Rp500.000 | No | — |
| Rp1.000.000 | No | — |
| Rp1.000.001 | Yes | Rp1.000.001 |
| Rp1.500.000 | Yes | Rp1.500.000 |
| Rp10.000.000 | Yes | Rp10.000.000 |

Do not change this threshold.

Do not introduce partial withdrawal.

Do not allow the Label to enter a custom withdrawal amount.

---

## 14. Admin Balance Display

The Admin Console should distinguish balance sources.

Recommended presentation:

```text
ROYALTY BALANCE

Available Balance
Rp 15.250.000

SOURCE BREAKDOWN

Believe Legacy
Rp 13.800.000

Manual Adjustment
+ Rp 1.450.000

────────────────────────

Available
Rp 15.250.000
```

The exact UI must follow the existing Rilis Musik design system.

Do not redesign unrelated sections of the Admin Console.

---

## 15. Adjustment History

Admin should have access to adjustment history.

Recommended table:

```text
ROYALTY ADJUSTMENTS

Adjustment ID | Label | Amount | Type | Status | Created By | Date
```

Example:

```text
AJ-00123 | ABC Music | +Rp1.450.000 | Legacy Reconciliation | Active | Admin | 08 Sep 2026
AJ-00122 | XYZ Music | +Rp2.100.000 | Legacy Reconciliation | Active | Admin | 08 Sep 2026
```

The history should use existing search/filter/table patterns where available.

---

## 16. Audit Trail

Royalty adjustments are financial records.

Every adjustment MUST be auditable.

The audit record must answer:

1. Who created it?
2. Which Label received it?
3. How much was added?
4. When was it created?
5. Why was it created?
6. What was the reference/source?
7. What was the balance before?
8. What was the balance after?
9. Is the adjustment active or voided?

Example:

```text
Adjustment ID:
AJ-00123

Label:
ABC Music

Type:
LEGACY_RECONCILIATION

Amount:
+ Rp1.450.000

Reference:
BELIEVE-LEGACY-2026

Reason:
Legacy royalty reconciliation against Believe database.

Balance Before:
Rp13.800.000

Balance After:
Rp15.250.000

Created By:
Admin User

Created At:
2026-09-08 17:42

Status:
ACTIVE
```

---

## 17. Adjustments Must Not Be Silently Edited

Once a financial adjustment has been created, its historical record should not be silently overwritten.

If an adjustment is incorrect, the preferred mechanism is:

```text
Original Adjustment
       ↓
VOID / REVERSE
       ↓
Create Correct Adjustment
```

Do not hard-delete financial adjustment records.

If the current system has no void/reversal concept, implement the smallest safe mechanism required to preserve the audit trail.

---

## 18. Label-Facing UI

The Label account should continue to present a simple available balance.

Recommended:

```text
ROYALTY

Available Balance
Rp 15.250.000

[Withdraw Royalty]
```

The existing withdrawal eligibility logic determines whether the action is available.

Do not expose internal reconciliation complexity to Labels unless an existing product requirement already requires source-level transparency.

---

## 19. Admin vs Label Separation

### Admin

Admin needs:

- Total available balance
- Legacy source amount
- Adjustment amount
- New/current royalty where applicable
- Adjustment history
- Audit information
- Reconciliation reference

### Label

Label needs:

- Available royalty balance
- Existing withdrawal action
- Existing withdrawal status/history

This separation is intentional:

```text
ADMIN
Full financial source visibility

        ↓

LABEL
Simple available balance
```

---

## 20. Migration / Reconciliation Strategy

This mechanism is intended primarily to resolve affected legacy balances.

### Phase 1 — Identify affected Labels

Identify Labels where:

```text
Legacy balance > Rp0
```

and where the displayed Rilis Musik amount requires reconciliation.

### Phase 2 — Verify reference

Compare the relevant legacy balance against the trusted Believe reference/database.

### Phase 3 — Create Adjustment

Admin creates a `LEGACY_RECONCILIATION` adjustment for the verified difference or verified required balance.

### Phase 4 — Label Balance Updates

The adjustment becomes part of the available balance immediately.

### Phase 5 — Label Withdrawal

When:

```text
Available Balance > Rp1.000.000
```

the existing withdrawal workflow allows the Label to withdraw the entire available balance.

### Phase 6 — Legacy Settlement

Once the Label has successfully withdrawn the remaining balance:

```text
Available Balance = Rp0
```

the legacy account is considered settled according to the migration strategy.

### Phase 7 — Future Data

Future/current royalty imports continue using the existing system.

Do not force future royalty through the legacy adjustment mechanism.

---

## 21. Important Distinction — Adjustment Is Not CSV Replacement

Do NOT implement:

```text
Believe CSV
     ↓
Overwrite legacy amount
```

Instead:

```text
Believe CSV
     ↓
Legacy Source
     │
     ├───────────────┐
     │               │
     ↓               ↓
Legacy Balance   Admin Adjustment
                     │
                     ↓
              Available Balance
```

The original source remains identifiable.

---

## 22. Idempotency & Duplicate Protection

The system must avoid accidental duplicate adjustments.

At minimum:

- Double-clicking Confirm must not create two adjustments.
- Refreshing after submission must not duplicate the adjustment.
- Repeated requests caused by network retry must be handled safely.
- Each adjustment must have a unique ID.
- If the application architecture supports idempotency keys, use them.

This is mandatory because the operation changes financial data.

---

## 23. Permissions & Security

Only authorized Admin users may create adjustments.

The implementation must reuse the existing authentication and authorization system.

Do not bypass:

- Admin authentication
- Role checks
- Permission checks
- Existing API authorization
- Existing security mechanisms

Do not expose the adjustment endpoint to ordinary Labels/users.

Server-side authorization is mandatory; UI hiding alone is insufficient.

---

## 24. Validation

The system must validate:

- Target Label exists.
- User is authorized.
- Amount is a valid monetary value.
- Currency is valid.
- Reason is provided.
- Reference is provided when required for legacy reconciliation.
- Amount uses valid monetary precision.
- Duplicate submission is prevented.
- The adjustment cannot create an inconsistent financial state.

Use the application's existing money/decimal handling.

**Do not use floating-point arithmetic for financial amounts if the current architecture provides a decimal/integer monetary representation.**

---

## 25. Error Handling

If an adjustment fails:

- Do not partially update the balance.
- Do not create an incomplete financial record.
- Show a clear error to Admin.
- Allow a safe retry.
- Preserve system consistency.

The operation should be atomic where supported:

```text
Create Adjustment
+
Update/derive Balance
=
One consistent transaction
```

If the existing architecture derives balance from ledger entries, create the ledger entry and allow the existing balance mechanism to derive the new balance.

---

## 26. Existing Withdrawal Workflow

The existing withdrawal system remains the source of truth for withdrawal execution.

The new adjustment mechanism should only ensure that the adjusted amount is recognized as available royalty.

Do not create a second withdrawal system.

Do not introduce:

- Partial withdrawals
- User-entered withdrawal amounts
- New withdrawal thresholds
- New payout methods
- New payout statuses

unless they already exist in the current system.

The existing rule remains:

> **If available balance is greater than Rp1.000.000, the Label can request withdrawal of the entire available balance.**

---

## 27. Data Integrity

The following must remain true:

```text
Available Balance
=
All valid royalty credits
-
All valid withdrawals/debits
```

Every adjustment must have a corresponding source record.

There must never be a situation where:

```text
Label displays Rp15.250.000

but

Admin cannot explain where Rp1.450.000 came from.
```

Every additional balance must be traceable.

---

## 28. Recommended Conceptual Data Model

Follow the current database architecture.

Conceptually:

```text
Royalty Ledger Entry

id
label_id
source
type
amount
currency
reference
reason
status
created_by
created_at
metadata
```

Possible sources:

```text
BELIEVE_LEGACY
ADMIN_ADJUSTMENT
NEW_ROYALTY
WITHDRAWAL
```

Possible adjustment type:

```text
LEGACY_RECONCILIATION
```

Do not create a new structure if the existing royalty/ledger system can safely support this through an extension.

---

## 29. UI/UX Direction

Maintain the existing Rilis Musik visual language.

Requirements:

- Reuse existing buttons, modal/dialog components, inputs, tables, badges, typography, spacing, and toast patterns.
- Make financial amounts visually clear.
- Use a confirmation step before committing.
- Make the action clearly identifiable as a financial adjustment.
- Avoid unnecessary visual complexity.
- Do not redesign unrelated screens.

Recommended action:

```text
[ + Inject Saldo ]
```

Recommended confirmation:

```text
Confirm Royalty Adjustment

Label:
ABC Music

Current Balance:
Rp13.800.000

Adjustment:
+ Rp1.450.000

New Balance:
Rp15.250.000

Reason:
Legacy royalty reconciliation

Reference:
BELIEVE-LEGACY-2026

[Cancel] [Confirm Adjustment]
```

---

## 30. Success State

After a successful adjustment:

```text
Royalty adjustment created successfully.

Adjustment:
+ Rp1.450.000

New Available Balance:
Rp15.250.000
```

The Label balance should reflect the new amount without requiring manual database intervention.

---

## 31. Empty State

If a Label has no manual adjustments:

```text
Manual Adjustments

No adjustments have been recorded for this Label.
```

Do not display fake/zero-value adjustment records.

---

## 32. Technical Implementation Instructions for AI Agent

Before modifying anything:

1. Inspect the current royalty database/schema.
2. Inspect the current Believe CSV import process.
3. Inspect how legacy royalty balances are currently calculated/stored.
4. Inspect the current Label wallet/balance implementation.
5. Inspect the existing withdrawal eligibility and withdrawal amount logic.
6. Inspect current Admin authentication/authorization.
7. Inspect existing audit/logging patterns.
8. Inspect existing UI components and modal/form patterns.
9. Inspect relevant API/service/controller routes.
10. Identify the smallest integration point for the new adjustment mechanism.

Then implement the feature.

### Do not assume the current architecture.

The AI Agent must inspect the codebase and adapt the PRD to what actually exists.

---

## 33. Implementation Principles

### Principle 1 — Preserve Existing System

Existing functionality is the baseline.

### Principle 2 — Separate Source

Manual reconciliation must not overwrite Believe legacy data.

### Principle 3 — Ledger First

Do not simply mutate a balance number.

### Principle 4 — Auditable

Every adjustment must be traceable.

### Principle 5 — Atomic

Financial changes must not produce partial states.

### Principle 6 — Existing Withdrawal Rules

Adjusted balance must flow into the existing withdrawal system.

### Principle 7 — Minimal Change

Only modify what is necessary to implement this PRD.

### Principle 8 — No Unrequested Refactor

Do not use this feature as a reason to rewrite unrelated parts of the application.

---

## 34. Acceptance Criteria

The implementation is accepted only if all of the following are true:

1. Admin can select an eligible Label and create a royalty adjustment.
2. The adjustment is stored as a separate auditable record/source.
3. The original Believe legacy source remains intact.
4. The adjustment immediately affects the Label's available balance.
5. Admin can see the adjustment separately from the legacy source.
6. Every adjustment records who, when, how much, why, and reference/source.
7. Existing withdrawal logic recognizes the adjusted balance.
8. A Label can withdraw only when available balance is **greater than Rp1.000.000**.
9. When eligible, the Label must withdraw the **entire available balance**.
10. The Label cannot enter a custom withdrawal amount.
11. A balance of exactly Rp1.000.000 does not qualify.
12. A balance of Rp1.000.001 qualifies and the withdrawal amount is Rp1.000.001.
13. Duplicate adjustment creation is prevented.
14. Unauthorized users cannot create adjustments.
15. Failed adjustments do not partially modify financial data.
16. Existing withdrawal workflows remain functional.
17. Existing royalty import workflows remain functional.
18. Existing Label functionality remains functional.
19. No unrelated Admin features are modified.
20. No legacy CSV records are deleted or silently overwritten.
21. Financial adjustment records cannot be silently hard-deleted.
22. The implementation follows the existing application's architecture and design system.
23. The implementation does not introduce a second independent withdrawal system.
24. The implementation does not change unrelated business rules.

---

## 35. Regression Test Requirements

### Balance

Test at minimum:

- Legacy balance = Rp0
- Legacy balance < Rp1.000.000
- Legacy balance = Rp1.000.000
- Legacy balance > Rp1.000.000
- Adjustment added to zero balance
- Adjustment added to non-zero balance
- Multiple adjustments for one Label

### Withdrawal

Test at minimum:

- Balance Rp1.000.000 → unavailable
- Balance Rp1.000.001 → available, full balance only
- Balance Rp5.000.000 → withdrawal amount Rp5.000.000
- Balance Rp15.250.000 → withdrawal amount Rp15.250.000
- After successful full withdrawal → balance Rp0

### Adjustment

Test:

- Valid adjustment
- Invalid amount
- Missing reason
- Missing reference where required
- Unauthorized Admin
- Double-click submission
- Network retry
- Page refresh after submission
- Concurrent Admin actions
- Attempt to manipulate adjustment through client-side request

### Data Integrity

Verify:

- Legacy data unchanged.
- Adjustment record exists.
- Balance is correct.
- Withdrawal is recorded correctly.
- Audit information is complete.
- No duplicate financial entries exist.

---

## 36. Definition of Done

This feature is complete when Rilis Musik has a reliable and auditable mechanism for reconciling legacy royalty balances without modifying the original Believe CSV data.

An authorized Admin must be able to:

```text
Identify Label
      ↓
Verify Believe Reference
      ↓
Create Royalty Adjustment
      ↓
Confirm
      ↓
Label Balance Updates
      ↓
Label Can Withdraw When > Rp1.000.000
      ↓
Label Withdraws Entire Balance
      ↓
Balance Returns to Rp0
```

The system must preserve the distinction between:

```text
Believe Legacy
        +
Admin Adjustment
        +
New Royalty
        -
Withdrawals
        =
Available Balance
```

Most importantly:

> **This PRD must be implemented by extending the existing Rilis Musik structure, not by rebuilding or altering unrelated functionality.**

The existing application, existing features, existing withdrawal rules, existing royalty import process, existing permissions, and existing UI conventions must remain intact unless a change is explicitly required by this PRD.

---

## 37. Final Instruction to AI Development Agent

Implement the requirements in this PRD against the **existing Rilis Musik production codebase**.

**Inspect first. Modify second.**

Do not assume the database structure, royalty calculation, wallet implementation, withdrawal implementation, or routing structure. Determine how they currently work and integrate the feature into the existing architecture.

The primary objective is to create a **separate, auditable royalty adjustment source for legacy reconciliation** while allowing the resulting amount to participate in the existing Label balance and withdrawal workflow.

Do not fix the legacy discrepancy by silently rewriting or overwriting the historical Believe data.

Do not introduce unrelated changes.

Do not redesign unrelated UI.

Do not change unrelated business logic.

Do not change the existing withdrawal rule:

> **Available balance must be greater than Rp1.000.000, and the Label must withdraw the entire available balance.**

If there is a conflict between this PRD and existing implementation, preserve existing production behavior where it is unrelated to this feature, identify the conflict, and implement the smallest safe change necessary to satisfy the PRD.

Before finalizing, perform regression testing on royalty balance, withdrawal, Label account display, Admin adjustment, permissions, legacy data integrity, and all affected existing workflows.
