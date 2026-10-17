# Invoicekit: Handoff

## Project Goal

Build a complete invoicing system for a service business. The system manages creating, editing, issuing, and rendering invoices with proper numbering and formatting.

## House Rules (Apply to All Requests)

1. **Money is always an integer number of cents.** Never store or return fractional amounts. When a calculation produces fractional cents, round using `roundCents()` from `src/money.js`.

2. **Never throw for bad input.** Return `fail(CODE)` from `src/result.js` instead. Add every new error code to `ERRORS` in `src/errors.js` with a one-line message.

3. **Never mutate an argument.** Return new objects and arrays instead.

4. **Run `npm test` before you say a request is done.**

5. **All amounts shown to customers use `formatEuros()`** from `src/money.js`. This applies to anything rendered for customer display going forward.

6. **No amount may ever go below zero; clamp at 0.** This applies to line discounts, invoice discounts, totals, VAT, and any other computed amount.

7. **Dates are always YYYY-MM-DD strings and all date arithmetic uses UTC, never local time.** Use `isValidDate()`, `addDays()`, and `daysBetween()` from `src/dates.js`.

8. **Customer IDs are always normalized (trimmed and uppercased) before comparison or storage.** Use `normalizeId()` from `src/customers.js`.

## Key Decisions Made

- **Invoice numbering format:** `INV-<year>-<counter>` where counter is 4 digits, zero-padded, starting at 0001 and restarting every year.
- **Invoice statuses:** `draft` (editable), `issued` (numbered and locked), `partially_paid` (has payments but balance remains), `paid` (all balance paid). Only draft invoices can be modified (no edits after issuing).
- **Error handling:** Uses result-style `{ ok: boolean, value?, error?, details? }` pattern. Never throws exceptions for validation errors.
- **Customer-facing output:** All monetary amounts must go through `formatEuros()` for consistency.
- **Line discounts:** Per-line `discountPercent` (0–100, can have decimals). Line discount = `lineTotal × discountPercent / 100`, rounded per line.
- **Tier-based discounts:** Gold 5%, Silver 2.5%, Standard 0%. Applied automatically when a line has no explicit `discountPercent`.
- **VAT calculation:** VAT is computed per line on the line amount **after discount is applied** (i.e., `(lineTotal - lineDiscount) × vatRate / 100`). Each line's VAT is rounded independently. Invoice VAT is the sum of rounded line VATs.
- **Invoice totals formula:** `total = subtotal - discount + vat - voucher` (where all components are clamped at 0). Vouchers apply after VAT and are optional.
- **Rendering:** VAT is shown on its own line (when > 0) just above the total in plain-text output.

## What Has Been Built

### Core Files

| File | Purpose |
|------|---------|
| `src/money.js` | Money formatting and parsing (pre-existing: `roundCents`, `formatEuros`, `parseEuros`) |
| `src/result.js` | Result pattern for error handling (pre-existing: `ok()`, `fail()`) |
| `src/errors.js` | All error codes and messages |
| `src/catalogue.js` | Product catalogue (pre-existing: `getProduct()`, `listProducts()`) |
| `src/customers.js` | Customer database with ID normalization and tier discounts |
| `src/invoices.js` | Core invoicing functions (create, edit, issue, calculate totals with discount and VAT) |
| `src/numbering.js` | Invoice number generation with year-based counter |
| `src/render.js` | Plain-text invoice rendering with VAT display |
| `src/dates.js` | **NEW** UTC-based date utilities (`isValidDate`, `addDays`, `daysBetween`) |
| `src/payments.js` | **NEW** Payment tracking and balance calculation |
| `src/statements.js` | **NEW** Customer account statements showing outstanding invoices |
| `src/credits.js` | **NEW** Credit notes for refunds on issued invoices |

### Implemented Functions

#### `src/customers.js`
- `normalizeId(id)` — Trim whitespace and convert to uppercase
  - Example: `' c-001 '` → `'C-001'`
  - Used by `getCustomer()` and `createInvoice()`

- `getCustomer(id)` — Fetch customer by normalized ID
  - Normalizes ID before lookup
  - Returns `{ ok: true, value: customer }` or `{ ok: false, error: 'CUSTOMER_NOT_FOUND' }`

- `TIER_DISCOUNTS` constant — Discount percentages by tier
  - `gold: 5`, `silver: 2.5`, `standard: 0`

#### `src/invoices.js`
- `createInvoice({ customerId, issueDate, lines, terms? })` — Create a draft invoice
  - Normalizes `customerId` before use and storage
  - Lines input: `{ sku, qty, discountPercent? }` arrays
  - Applies tier discount to lines without explicit `discountPercent`
  - Output lines expanded with catalogue data: `{ sku, name, qty, unitPrice, vatRate, discountPercent? }`
  - `terms` defaults to `'NET30'`; can be `'NET14'`, `'NET30'`, or `'EOM'`
  - Sets `invoice.dueDate` based on terms: NET14 = issueDate + 14 days, NET30 = issueDate + 30 days, EOM = last day of issue month
  - Errors: `CUSTOMER_NOT_FOUND`, `DATE_INVALID`, `NO_LINES`, `QTY_INVALID`, `UNKNOWN_SKU`, `DISCOUNT_INVALID`, `TERMS_INVALID`

- `lineTotal(line)` — Calculate base total for a single line (qty × unitPrice, rounded)

- `lineDiscount(line)` — Calculate discount amount for a single line
  - Formula: `(lineTotal × discountPercent / 100)`, rounded, clamped at 0

- `lineVAT(line)` — Calculate VAT for a single line
  - VAT applied to `(lineTotal - lineDiscount)`
  - Formula: `((lineTotal - lineDiscount) × vatRate / 100)`, rounded, clamped at 0

- `invoiceTotals(invoice)` — Calculate invoice totals
  - Returns `{ subtotal, discount, vat, voucher, total }`
  - `total = subtotal - discount + vat - voucher` (clamped at 0)
  - `voucher` is 0 if no voucher applied

- `addLine(invoice, { sku, qty, discountPercent? })` — Add or increase a line
  - Accepts optional `discountPercent`
  - Applies tier discount if no explicit discount
  - Status must be `draft`, or returns `NOT_DRAFT`
  - Same validation as create (QTY_INVALID, UNKNOWN_SKU, DISCOUNT_INVALID)

- `removeLine(invoice, sku)` — Remove a line
  - Returns `LINE_NOT_FOUND` if SKU not on invoice
  - Returns `NO_LINES` if would remove last line
  - Status must be `draft`, or returns `NOT_DRAFT`

- `issueInvoice(invoice, existingNumbers)` — Change status from draft to issued
  - Assigns next invoice number
  - Returns `NOT_DRAFT` if already issued
  - Takes array of existing numbers for numbering logic

- `applyVoucher(invoice, { code, amount })` — Apply a fixed-amount voucher to an invoice
  - `amount` must be a positive integer (cents)
  - Invoice status must be `draft`, or returns `NOT_DRAFT`
  - Only one voucher per invoice, or returns `VOUCHER_EXISTS`
  - Sets `invoice.voucher = { code, amount }`
  - Errors: `NOT_DRAFT`, `VOUCHER_EXISTS`, `AMOUNT_INVALID`
  - Returns `ok(newInvoice)`

#### `src/dates.js`
- `isValidDate(text)` — Validate YYYY-MM-DD format in UTC
  - Checks format, valid month (1–12), valid day-of-month (including leap years)
  - Example: `'2025-02-29'` → false (not a leap year), `'2024-02-29'` → true

- `addDays(dateStr, n)` — Add n days to a date in UTC
  - Returns new date string in YYYY-MM-DD format
  - Handles negative values
  - Example: `addDays('2025-01-31', 1)` → `'2025-02-01'`

- `daysBetween(a, b)` — Calculate whole days between two dates (b minus a) in UTC
  - Returns negative if a > b
  - Example: `daysBetween('2025-01-01', '2025-01-05')` → 4

#### `src/numbering.js`
- `nextInvoiceNumber(existingNumbers, issueDate)` — Calculate next invoice number
  - Format: `INV-<year>-<counter>` (4-digit counter, zero-padded)
  - Restarts counter each year
  - Ignores malformed numbers gracefully

#### `src/render.js`
- `renderInvoiceText(invoice)` — Plain-text invoice for display
  - Line 1: Invoice number or "DRAFT"
  - Line 2: Customer name
  - Lines 3+: Item lines with `qty × name @ unitPrice = lineTotal`
  - Final line: `Total: ` with formatted total
  - All amounts use `formatEuros()`

#### `src/payments.js`
- `recordPayment(invoice, { amount, date })` — Record a payment towards an invoice
  - `amount` must be a positive integer (cents)
  - Invoice status must be `issued` or `partially_paid`, or returns `NOT_ISSUED`
  - Amount must not exceed balance due, or returns `OVERPAYMENT`
  - Errors: `NOT_ISSUED`, `AMOUNT_INVALID`, `OVERPAYMENT`
  - Sets status to `paid` when balance reaches 0, otherwise `partially_paid`
  - Returns `ok(newInvoice)` with payment added to `invoice.payments` array

- `balanceDue(invoice)` — Calculate total amount still owed
  - Returns `invoiceTotals(invoice).total - sum(payments)`
  - Returns 0 if fully paid or no payments yet
  - Works on invoices in any status

#### `src/statements.js`
- `statement(customerId, invoices, asOf)` — Generate a customer account statement
  - `customerId` is normalized before use
  - Returns `ok({ customerId, invoices, totalDue })`
  - `invoices` array contains only invoices with:
    - Matching normalized `customerId`
    - Status `issued` or `partially_paid`
    - `issueDate` on or before `asOf` (YYYY-MM-DD)
  - Each invoice in the statement is: `{ number, issueDate, dueDate, total, due }`
  - `due` is calculated from `balanceDue(invoice)`
  - Invoices sorted by `issueDate` ascending
  - `totalDue` is the sum of all `due` amounts
  - Errors: `CUSTOMER_NOT_FOUND` (normalized customer ID doesn't exist)

#### `src/credits.js`
- `createCreditNote(invoice, { amount, reason, date }, existingNumbers)` — Create a credit note for an issued invoice
  - `amount` must be a positive integer (cents)
  - `reason` is a text description of the refund reason
  - `date` is the credit note issue date (YYYY-MM-DD)
  - Invoice status must be `issued`, `partially_paid`, or `paid`, or returns `NOT_ISSUED`
  - Amount must not exceed invoice total, or returns `CREDIT_TOO_HIGH`
  - Returns `ok(creditNote)` with: `{ number, invoiceNumber, customerId, amount, reason, date }`
  - Credit note number format: `CN-<year>-<counter>` (4-digit counter, zero-padded, separate from invoice counters)
  - `existingNumbers` can contain both invoice and credit note numbers
  - Errors: `NOT_ISSUED`, `AMOUNT_INVALID`, `CREDIT_TOO_HIGH`

### Error Codes Defined

| Code | Message |
|------|---------|
| `AMOUNT_INVALID` | Amount must be a whole, positive number of cents. |
| `CUSTOMER_INVALID` | A customer needs an id, a name and a valid email. |
| `CUSTOMER_NOT_FOUND` | No customer with that id. |
| `UNKNOWN_SKU` | No product with that SKU in the catalogue. |
| `DATE_INVALID` | Invoice date must be a real date in YYYY-MM-DD format. |
| `NO_LINES` | Invoice must have at least one line item. |
| `QTY_INVALID` | Line item quantity must be a positive integer. |
| `NOT_DRAFT` | Can only modify invoices with status "draft". |
| `LINE_NOT_FOUND` | That SKU is not on this invoice. |
| `DISCOUNT_INVALID` | Discount percent must be a number between 0 and 100. |
| `NOT_ISSUED` | Invoice must be issued or partially paid to record a payment. |
| `OVERPAYMENT` | Payment amount exceeds the balance due. |
| `TERMS_INVALID` | Payment terms must be NET14, NET30, or EOM. |
| `VOUCHER_EXISTS` | Invoice already has a voucher applied. |
| `CREDIT_TOO_HIGH` | Credit note amount exceeds the invoice total. |

### Test Coverage

| File | Tests | Coverage |
|------|-------|----------|
| `test/invoices.test.js` | 149 | createInvoice, lineTotal, lineDiscount, lineVAT, invoiceTotals, addLine, removeLine, issueInvoice, discounts, VAT, tier discounts, ID normalization, payment terms, vouchers |
| `test/dates.test.js` | 23 | isValidDate (formats, leap years), addDays (boundaries, negative values), daysBetween (calculations, consistency) |
| `test/numbering.test.js` | 10 | nextInvoiceNumber (edge cases, year boundaries, malformed data) |
| `test/render.test.js` | 12 | renderInvoiceText (formats, amounts, customer lookup, VAT display) |
| `test/payments.test.js` | 14 | recordPayment (validation, status transitions, multiple payments), balanceDue (calculations, edge cases) |
| `test/statements.test.js` | 16 | statement (customer filtering, date filtering, status filtering, sorting, totals, edge cases) |
| `test/credits.test.js` | 19 | createCreditNote (validation, status checks, numbering, year handling, edge cases) |
| **Total** | **221** | All new functionality |

**Total test suite:** 221 passing tests (includes pre-existing tests for money, catalogue, customers, result)

## Unfinished Work

The following features have not been implemented but are likely needed:

- **Persistence** — No database or file storage (all in-memory); all data must be passed as parameters
- **Invoice state transitions** — Only draft → issued → (partially_paid / paid); no cancelled, refunded, or voided states
- **PDF rendering** — Only plain text rendering exists; no PDF generation
- **Internationalization** — Hard-coded euro formatting (EUR); dates always in YYYY-MM-DD format
- **Line amendments** — No ability to change qty or discount on existing issued lines
- **Email delivery** — No email integration for sending invoices or credit notes
- **Remittance advice** — No support for payment instructions or bank details
- **Credit note application** — Credit notes are created but not automatically applied to reduce invoice balance

## Invoice Object Structure

A complete invoice looks like:

```javascript
{
  customerId: "C-001",              // normalized (uppercase, trimmed)
  issueDate: "2025-10-07",          // YYYY-MM-DD in UTC
  status: "draft" | "issued" | "partially_paid" | "paid",
  number: "INV-2025-0001",          // only if issued
  terms: "NET30",                   // "NET14", "NET30", or "EOM" (always set)
  dueDate: "2025-11-06",            // YYYY-MM-DD (always set)
  lines: [
    {
      sku: "DEV-HOUR",
      name: "Development (hour)",
      qty: 5,
      unitPrice: 9500,              // cents, without VAT
      vatRate: 21,                  // percent
      discountPercent: 5            // optional; applied if present, else tier discount
    }
    // ...
  ],
  voucher: {                        // optional; one per invoice, draft only
    code: "PROMO10",
    amount: 5000                    // cents, applied after VAT
  },
  payments: [                       // optional; created when first payment recorded
    {
      amount: 30000,                // cents
      date: "2025-10-08"            // YYYY-MM-DD
    }
    // ...
  ]
}
```

### Totals Calculation

Calling `invoiceTotals(invoice)` returns:

```javascript
{
  subtotal: 47500,       // sum of all lineTotal()
  discount: 2375,        // sum of all lineDiscount()
  vat: 9506,             // sum of all lineVAT() (computed on discounted amount)
  voucher: 5000,         // voucher amount (0 if no voucher)
  total: 54631           // subtotal - discount + vat - voucher (clamped at 0)
}
```

## How to Run Tests

```bash
npm test
```

Runs all tests with Node's built-in test runner. Output shows test names and summary at the end.

To run a specific test file:
```bash
node --test test/invoices.test.js
```

## How to Continue

When picking up this work:

1. **Start here:** Read this entire HANDOFF.md for project context and current state
2. **Verify setup:** Run `npm test` to confirm all 221 tests pass
3. **Understand patterns:** Read key files (`src/invoices.js`, `src/payments.js`) to see how the system works
4. **Review tests:** Look at test files to understand testing patterns and edge cases
5. **Plan new work:** Identify what feature to build next, write tests first, then implement
6. **Follow house rules:** 
   - All money as cents (integers only)
   - All errors via `fail()`, never throw
   - Never mutate arguments (return new objects)
   - Dates always YYYY-MM-DD in UTC
   - No amounts below zero (clamp at 0)
   - Customer IDs normalized everywhere
7. **Add new error codes:** Update `src/errors.js` with any new error codes
8. **Run tests:** Always run `npm test` before considering work complete
9. **Update HANDOFF.md:** Document any new rules, decisions, or architectural changes

## Key Implementation Notes

- **Discount calculation happens per-line:** Each line's discount is computed from its own total, not the invoice subtotal. This allows different discount percentages on different lines.

- **Tier discounts are automatic:** When `createInvoice()` or `addLine()` is called without an explicit `discountPercent`, the customer's tier discount is applied. Standard tier (0%) does not set `discountPercent` on the line (cleaner JSON).

- **VAT uses the discounted amount:** This is critical for correct tax calculation. VAT = `(lineTotal - lineDiscount) × vatRate / 100`. This affects all math involving VAT.

- **Customer IDs are normalized everywhere:** Both `getCustomer()` and `createInvoice()` normalize the ID. The invoice stores the normalized ID. This prevents issues like `'c-001'`, `'C-001'`, and `' c-001 '` being treated as different customers.

- **All date math is in UTC:** The `dates.js` module never uses local time. This is critical for cross-timezone consistency (e.g., an invoice dated 2025-01-01 in UTC is always 2025-01-01, never affected by the server's local timezone).

- **Rendering includes VAT line:** When `renderInvoiceText()` is called, it now shows "VAT: €XXX.XX" just above the total (only if VAT > 0). This is required for EU invoices.

- **Payment terms determine due dates:** Terms default to NET30 (30 days from issue). NET14 is 14 days from issue. EOM is the last day of the issue month, regardless of when in the month the invoice is issued. All due dates are calculated using UTC date arithmetic via `calculateDueDate()` helper.

- **Vouchers are applied after VAT:** A voucher is a fixed-amount deduction (in cents) applied to the invoice total AFTER VAT calculation. Only one voucher per invoice, and only drafts can have vouchers applied (vouchers are removed if invoice is issued). Voucher amount is included in `invoiceTotals()` output.

- **Credit notes track refunds:** Credit notes are issued against invoices that have been issued, partially paid, or paid (no credit notes on drafts). Each credit note has its own number sequence (CN-YYYY-NNNN) separate from invoice numbers, but both types are tracked in the same `existingNumbers` array. Credit note amounts cannot exceed the invoice total.

## Data Files

The system loads from JSON files in `/data/`:

- `customers.json` — Customer list (id, name, email, country, tier: "gold" | "silver" | "standard")
- `catalogue.json` — Product catalogue (sku, name, unitPrice in cents, vatRate in percent: 0, 9, or 21)

These are pre-existing, read-only within the codebase, and always accessed via the catalogue/customers modules (not directly).
