# Invoicing System — Handoff

## Project Goal

Build a complete invoicing system with invoice creation, modification, numbering, rendering, payment tracking, and customer statements. Includes line-level discounts, customer tier discounts, VAT calculations, payment terms, vouchers, credit notes, and ID normalization.

## House Rules (Apply to All Requests)

These rules are fundamental to this project and must be followed in all future work:

1. **Money is always integer cents.** Never store or return fractional amounts. When a calculation gives a fraction of a cent, round it using `roundCents()` from `src/money.js`. This ensures consistency across all monetary values.

2. **Never throw for bad input.** Return `fail(CODE)` from `src/result.js` instead, and add every new error code to `ERRORS` in `src/errors.js` with a one-line message. This provides consistent error handling across the API.

3. **Never mutate an argument.** Always return new objects and arrays instead. This ensures functions are predictable and don't have side effects.

4. **Run `npm test` before marking a request done.** All tests must pass before considering work complete.

5. **Dates are YYYY-MM-DD strings, all arithmetic in UTC.** Never use machine local time. Use `isValidDate()`, `addDays()`, and `daysBetween()` from `src/dates.js` for date operations.

6. **Always normalize customer IDs.** Use `normalizeId()` from `src/customers.js` to trim and uppercase all customer IDs before comparing or storing them. This handles real-world data like `'c-007 '` and `'C-007'`.

7. **No computed amount may ever go below zero.** Clamp totals and any calculated amount at 0 using `Math.max(0, value)`.

## Key Decisions

### Invoice Numbering

Format: `INV-<year>-<counter>`, where:
- Year comes from the invoice's issue date (YYYY)
- Counter is 4 digits, zero-padded (0001, 0002, ..., 9999)
- Counter restarts at 0001 every January

### Credit Note Numbering

Format: `CN-<year>-<counter>`, with same structure as invoices but:
- Separate counter from invoices (CN-2024-0001 can coexist with INV-2024-0001)
- Linked to a specific invoice via invoiceNumber field

### Line Discounts

- Each line has a `discountPercent` field (0-100, can have decimals like 12.5)
- Explicit `discountPercent` (even 0) always wins over tier discount
- If not provided, line gets customer's tier discount
- Invalid discounts (outside 0-100 or non-numeric) return `DISCOUNT_INVALID`
- Line discount = `lineTotal × discountPercent / 100`, rounded per line

### Customer Tier Discounts

Applied automatically when a line has no explicit `discountPercent`:
- **gold**: 5%
- **silver**: 2.5%
- **standard**: 0%

Percentages stored in `TIER_DISCOUNTS` in `src/customers.js` for centralized management.

### VAT Calculation

- VAT is computed **per line on the amount after discount**: `(lineTotal - lineDiscount) × vatRate / 100`
- Each line's VAT is rounded individually using `roundCents()`
- Invoice VAT = sum of line VATs (NOT a percentage of invoice total)
- VAT rates: 21% (standard), 9% (reduced), 0% (zero-rated)

### Invoice Totals Calculation

`invoiceTotals()` returns `{ subtotal, discount, vat, voucher, total }`:
- `subtotal` = sum of all line totals
- `discount` = sum of all line discounts
- `vat` = sum of all rounded line VATs
- `voucher` = fixed amount voucher (if applied), 0 otherwise
- `total` = `subtotal - discount + vat - voucher`, clamped at 0

### Payment Terms

Invoices support three term types (set at creation, default NET30):
- **NET14**: Payment due 14 days after issue date
- **NET30**: Payment due 30 days after issue date
- **EOM**: Payment due on the last day of the issue date's month

Each invoice stores `terms` and `dueDate` fields.

### Vouchers

- One per invoice (draft only)
- Fixed amount in cents, applied after VAT
- Reduces invoice total: `total = subtotal - discount + vat - voucher`

### Payments

- Invoices can have multiple payments
- Status transitions: issued → partially_paid → paid
- `balanceDue()` = invoice total minus sum of all payments, clamped at 0
- Only 'issued' or 'partially_paid' invoices can receive payments

### Credit Notes

- Track refunds on issued, partially_paid, or paid invoices
- Cannot exceed the invoice's total
- Separate from payments (accounting record)
- Own CN-YYYY-NNNN numbering sequence, separate from invoices

### Customer Statements

- Aggregates a customer's outstanding invoices
- Includes only 'issued' or 'partially_paid' invoices with issueDate <= statement date
- Shows each invoice's due amount (balance after payments)
- Totals all amounts due across all included invoices

### Customer-Facing Amounts

Every amount displayed to a customer must go through `formatEuros()` from `src/money.js`. This ensures consistent formatting (€ sign, thousands separators, two decimals) everywhere.

### ID Normalization

All customer IDs are normalized (trimmed and uppercased) before storage or comparison. This handles real-world data from other systems that may have inconsistent casing and spaces.

## What Has Been Built

### Core Invoice Operations (`src/invoices.js`)

- **`createInvoice({ customerId, issueDate, lines, terms })`** — Creates a draft invoice with enriched line items. Normalizes customer ID, validates date, applies tier discounts, calculates due date from terms (default NET30). Returns `ok(invoice)` or `fail(CODE)`.

- **`lineTotal(line)`** — Calculates total for a single line: `qty × unitPrice` in cents.

- **`lineDiscount(line)`** — Calculates discount for a line: `lineTotal × discountPercent / 100`, rounded per line in cents.

- **`lineVat(line)`** — Calculates VAT for a line: `(lineTotal - lineDiscount) × vatRate / 100`, rounded per line in cents.

- **`invoiceTotals(invoice)`** — Calculates invoice totals, returns `{ subtotal, discount, vat, voucher, total }` in cents.

- **`addLine(invoice, { sku, qty, discountPercent })`** — Adds a line to a draft invoice. If the SKU already exists, increases quantity. Applies tier discount for new lines without explicit `discountPercent`. Validates qty and SKU. Refuses to modify non-draft invoices (NOT_DRAFT).

- **`removeLine(invoice, sku)`** — Removes a line from a draft invoice by SKU. Refuses to remove the last line (NO_LINES) or modify non-draft invoices (NOT_DRAFT).

- **`issueInvoice(invoice, existingNumbers)`** — Issues a draft invoice by assigning the next available invoice number and changing status to 'issued'. Refuses if status isn't 'draft' (NOT_DRAFT).

- **`applyVoucher(invoice, { code, amount })`** — Applies a fixed-amount voucher to a draft invoice. Validates amount is positive integer. Prevents multiple vouchers per invoice (VOUCHER_EXISTS). Refuses non-draft invoices (NOT_DRAFT).

### Invoice Numbering (`src/numbering.js`)

- **`nextInvoiceNumber(existingNumbers, issueDate)`** — Generates the next invoice number for a given year. Takes an array of existing numbers (any order) and issue date. Returns `INV-<year>-<counter>` format with proper zero-padding.

### Rendering (`src/render.js`)

- **`renderInvoiceText(invoice)`** — Renders an invoice as plain text:
  - First line: `DRAFT` or the invoice number (e.g., `INV-2024-0001`)
  - Second line: customer name
  - One line per item: `qty × name @ €unitPrice = €lineTotal` (with discount details if applicable)
  - Subtotal line (if discount > 0 or VAT > 0)
  - Discount line (if discount > 0): `Discount: -€amount`
  - VAT line (if VAT > 0): `VAT: €amount`
  - Final line: `Total: €amount`
  - All amounts formatted via `formatEuros()`.

### Payments (`src/payments.js`)

- **`recordPayment(invoice, { amount, date })`** — Records a payment on an issued or partially_paid invoice. Validates amount is positive integer. Prevents overpayments (OVERPAYMENT). Updates status to 'paid' when balance reaches zero, 'partially_paid' while owed. Returns `ok(newInvoice)` with payment added to invoice.payments array.

- **`balanceDue(invoice)`** — Returns the total amount still owed on an invoice: `total - sumOfPayments`, clamped at 0.

### Credit Notes (`src/credits.js`)

- **`createCreditNote(invoice, { amount, reason, date }, existingNumbers)`** — Creates a credit note for an issued, partially_paid, or paid invoice. Validates amount is positive integer and does not exceed invoice total (CREDIT_TOO_HIGH). Generates CN-YYYY-NNNN number with separate counter from invoices. Returns `ok(creditNote)` with fields: `{ number, invoiceNumber, customerId, amount, reason, date }`.

### Customer Statements (`src/statements.js`)

- **`statement(customerId, invoices, asOf)`** — Generates a customer statement showing outstanding invoices. Returns `ok({ customerId, invoices, totalDue })`. Filters invoices to only those with matching customer, status 'issued' or 'partially_paid', and issueDate <= asOf. Each invoice record has: `{ number, issueDate, dueDate, total, due }` (due from balanceDue). Invoices sorted by issueDate. totalDue is sum of all due amounts.

### Date Utilities (`src/dates.js`)

- **`isValidDate(text)`** — Validates a date string in YYYY-MM-DD format. Checks format and actual date correctness (e.g., handles leap years). Returns boolean.

- **`addDays(dateStr, n)`** — Adds `n` days to a date string (can be negative). All arithmetic in UTC. Returns date in YYYY-MM-DD format.

- **`daysBetween(a, b)`** — Calculates days between two dates: `b - a`. All arithmetic in UTC. Returns number of days (can be negative).

### Customer Management (`src/customers.js`)

- **`normalizeId(id)`** — Trims whitespace and converts to uppercase. Used before all customer ID comparisons and storage.

- **`getCustomer(id)`** — Looks up a customer by ID. Normalizes input ID before lookup. Returns `ok(customer)` or `fail('CUSTOMER_NOT_FOUND')`.

- **`listCustomers()`** — Returns all customers as copies (immutable).

- **`validateCustomer(c)`** — Validates a customer object has id, name, and valid email.

- **`TIER_DISCOUNTS`** — Constant object: `{ gold: 5, silver: 2.5, standard: 0 }`. Central place for tier discount percentages.

### Error Codes (`src/errors.js`)

Complete list in `ERRORS` object:
- `AMOUNT_INVALID` — Amount must be a whole, positive number of cents.
- `CREDIT_TOO_HIGH` — Credit note amount cannot exceed the invoice total.
- `CUSTOMER_INVALID` — A customer needs an id, a name and a valid email.
- `CUSTOMER_NOT_FOUND` — No customer with that id.
- `DATE_INVALID` — Date must be in YYYY-MM-DD format and a valid date.
- `DISCOUNT_INVALID` — Discount must be a number between 0 and 100.
- `LINE_NOT_FOUND` — No line with that SKU on the invoice.
- `NO_LINES` — Invoice must have at least one line.
- `NOT_DRAFT` — Only draft invoices can be modified.
- `NOT_ISSUED` — Invoice must be issued or partially paid to record a payment.
- `OVERPAYMENT` — Payment cannot exceed the amount still owed.
- `QTY_INVALID` — Quantity must be a positive integer.
- `TERMS_INVALID` — Terms must be NET14, NET30, or EOM.
- `UNKNOWN_SKU` — No product with that SKU in the catalogue.
- `VOUCHER_EXISTS` — Invoice can only have one voucher.

### Existing Modules (Unchanged)

- **`src/money.js`** — `roundCents()`, `formatEuros()`, `parseEuros()`
- **`src/result.js`** — `ok()`, `fail()` for result values
- **`src/catalogue.js`** — Product catalogue with `getProduct()`, `listProducts()`
- **`data/customers.json`** — Customer database with id, name, email, country, tier
- **`data/catalogue.json`** — Product database with sku, name, unitPrice, vatRate

## Test Coverage

All tests pass. Run with `npm test`:

- **`test/invoices.test.js`** (193 tests) — Tests for createInvoice, addLine, removeLine, issueInvoice, lineTotal, lineDiscount, lineVat, invoiceTotals, applyVoucher, payment terms. Covers validation, discounts, tier discounts, VAT, vouchers, terms (NET14, NET30, EOM), error cases, immutability, edge cases.

- **`test/customers.test.js`** (12 tests) — Tests for getCustomer, listCustomers, validateCustomer, normalizeId. Covers normalization, mixed case/spaces, tier validation.

- **`test/numbering.test.js`** (7 tests) — Tests for nextInvoiceNumber. Covers year handling, counter incrementing, zero-padding, unordered input.

- **`test/render.test.js`** (22 tests) — Tests for renderInvoiceText. Covers draft/issued display, customer names, line formatting, discount rendering, VAT rendering, amount formatting.

- **`test/dates.test.js`** (25 tests) — Tests for isValidDate, addDays, daysBetween. Covers format validation, date correctness, leap years, month/year boundaries, UTC arithmetic.

- **`test/payments.test.js`** (19 tests) — Tests for recordPayment, balanceDue. Covers payment recording, status transitions (issued → partially_paid → paid), payment validation, overpayment prevention, balance calculation.

- **`test/statements.test.js`** (17 tests) — Tests for statement. Covers customer filtering, status filtering, date filtering, sorting by issueDate, totalDue calculation, partial payments, immutability, mixed invoice statuses.

- **`test/credits.test.js`** (21 tests) — Tests for createCreditNote. Covers credit note creation for issued/partially_paid/paid invoices, CN numbering with separate counter, amount validation, credit limit enforcement, year-based counter resets.

- **`test/money.test.js`** (5 tests) — Tests for roundCents, formatEuros, parseEuros (existing, all passing).

- **`test/catalogue.test.js`** (4 tests) — Tests for product catalogue (existing, all passing).

**Total: 220 passing tests** across all modules.

## Code Organization

```
src/
  invoices.js       # Core invoice operations (create, add/remove lines, issue, totals, vouchers)
  payments.js       # Payment recording and balance calculations
  credits.js        # Credit note generation
  statements.js     # Customer statement generation
  numbering.js      # Invoice number generation
  render.js         # Invoice text rendering
  dates.js          # Date utilities (validation, arithmetic)
  customers.js      # Customer lookup, ID normalization, tier discounts
  errors.js         # Error codes and messages
  money.js          # Money formatting and parsing (existing)
  catalogue.js      # Product catalogue (existing)
  result.js         # Result type (ok/fail) (existing)

test/
  invoices.test.js  # 193 tests
  payments.test.js  # 19 tests
  credits.test.js   # 21 tests
  statements.test.js # 17 tests
  customers.test.js # 12 tests
  numbering.test.js # 7 tests
  render.test.js    # 22 tests
  dates.test.js     # 25 tests
  money.test.js     # 5 tests (existing)
  catalogue.test.js # 4 tests (existing)

data/
  customers.json    # Customer database with tiers
  catalogue.json    # Product catalogue with VAT rates
```

## How to Run Tests

```bash
npm test
```

All 220 tests must pass before any work is considered complete.

For specific test file:
```bash
npm test test/invoices.test.js
```

## What's Unfinished

1. **Persistence** — No database or file storage yet. Data is all in-memory. Would need to implement storage layer and handle invoice/credit note number sequence persistence.

2. **Additional rendering formats** — Only plain text rendering exists. PDF, HTML, or other formats would be future additions.

3. **Invoice amendments** — Amendments or replacement invoices for corrections after issuance. Currently credit notes are used for refunds, but full amendment workflow isn't implemented.

4. **Advanced payment workflows** — No scheduled payments, payment reminders, dunning, or recurring invoices. No payment method tracking (card, bank transfer, etc.).

5. **Bulk operations** — No support for batch creating, modifying, or cancelling invoices.

6. **Reporting and analytics** — No summary reports, revenue analytics, customer reports, tax reports (aggregate VAT by rate), or dashboards.

7. **Multi-currency** — All amounts are in EUR. Multi-currency support would need currency conversion and separate VAT handling per currency.

8. **Invoice cancellation** — No workflow to cancel or void already-issued invoices.

9. **Attachments and notes** — No way to attach documents or add internal notes to invoices.

10. **Audit trail** — No history of who changed what and when on an invoice.

## Next Steps for Future Work

Start by understanding the existing tests (run `npm test` to see all passing cases). Each module is independent with clear interfaces, so work can progress feature-by-feature. Remember the house rules—especially the no-mutation and no-throw rules—as they drive the API design throughout the codebase.

When starting work on any new feature, remember the house rules above and this handoff document.
