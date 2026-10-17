# Invoicing System Handoff

## Project Goal

Building a comprehensive invoicing system for a business that issues invoices to customers for products and services from a catalogue. The system manages invoice creation, editing, numbering, rendering, payment tracking, and handles line-level discounts, VAT, customer tier pricing, vouchers, and credit notes.

## House Rules (All Requests)

These rules apply to every request in this project:

1. **Money is always integer cents.** Never store or return fractional amounts. When a calculation produces a fraction of a cent, round it using `roundCents()` from `src/money.js`.

2. **Never throw for bad input.** Return `fail(CODE)` from `src/result.js` instead, and add every new error code to `ERRORS` in `src/errors.js` with a one-line message.

3. **Never mutate an argument.** Return new objects and arrays instead. This is critical for immutability.

4. **No amount we compute may ever go below zero.** Clamp all calculated amounts to 0 (subtotal, discount, VAT, total, line discounts, line VATs, vouchers, etc.).

5. **Dates are YYYY-MM-DD strings in UTC.** All date arithmetic and comparisons happen in UTC using the utilities in `src/dates.js`, never in local timezone.

6. **Customer IDs are normalized.** All customer IDs are trimmed of whitespace and converted to uppercase using `normalizeId()` from `src/customers.js` before comparison or storage.

7. **Run `npm test` before you say a request is done.** All changes must pass the full test suite (currently 272 tests).

8. **Exchange rates** for currency conversion are stored in `RATES` in `src/money.js`: EUR: 1, USD: 1.085, GBP: 0.8425 (units of that currency per euro). Always use `convert()` to convert amounts between currencies.

## Key Decisions

- **Invoice numbers** are formatted as `INV-<year>-<counter>`, where year is the issue date's year and counter is 4 digits, zero-padded, starting at 0001 and resetting every year. Example: `INV-2026-0042`.
- **Credit note numbers** are formatted as `CN-<year>-<counter>`, with their own independent counter separate from invoices, also resetting yearly.
- **Customer amounts shown to end users** (in rendered output) always go through `formatEuros()` from `src/money.js`. This ensures consistent euro formatting with thousands separators and two decimals.
- **Invoice statuses**: `draft` (editable), `issued` (with number, locked), `partially_paid` (partially paid), `paid` (fully paid).
- **Line discounts** are per-line: a line can carry `discountPercent` (0–100, decimals allowed). If not specified, the customer's tier discount is applied (gold 5%, silver 2.5%, standard 0%). Explicit discounts (even 0) always override tier discounts.
- **VAT is computed per line** on the line's amount **after its discount**, and is rounded per line using `roundCents()`. The invoice's total VAT is the sum of all line VATs, never a percentage of invoice total.
- **Invoice totals** return `{ subtotal, discount, vat, voucher, total }`, where `total = subtotal - discount + vat - voucher`.
- **VAT is shown in rendered output** on its own line (only if VAT > 0) just above the total.
- **Customer tiers and their discounts** are kept in one place: `TIER_DISCOUNTS` in `src/customers.js` (gold: 5, silver: 2.5, standard: 0).
- **Payment terms** default to NET30; supported values are NET14, NET30, and EOM (due on last day of issue month).
- **Vouchers** are fixed-amount discounts applied after VAT; one per invoice (drafts only).
- **Payments** record the amount, date, and update invoice status (issued → partially_paid or paid).
- **Credit notes** represent refunds; amount cannot exceed invoice total; numbered separately from invoices.

## What Has Been Built

### src/invoices.js
Core invoice operations and calculations:
- `createInvoice({ customerId, issueDate, lines, terms })` — Creates a draft invoice. Normalizes customer ID, validates using `isValidDate()`, and enriches lines with product details. Applies tier discounts when `discountPercent` is undefined on a line. Accepts optional `terms` (NET14, NET30 [default], EOM) and calculates `dueDate`. Stores normalized customer ID.
- `lineTotal(line)` — Returns qty × unitPrice in cents.
- `lineDiscount(line)` — Returns discount in cents (line total × discountPercent ÷ 100, rounded and clamped to 0).
- `lineVat(line)` — Returns VAT in cents (amount after discount × vatRate ÷ 100, rounded and clamped to 0).
- `invoiceTotals(invoice)` — Returns `{ subtotal, discount, vat, voucher, total }` where total = subtotal - discount + vat - voucher (all clamped to 0).
- `addLine(invoice, { sku, qty, discountPercent })` — Adds a line to a draft invoice (with optional discount). Validates `discountPercent` (0–100, must be a number).
- `removeLine(invoice, sku)` — Removes a line from a draft invoice. Prevents removal of the last line.
- `issueInvoice(invoice, existingNumbers)` — Assigns an invoice number and changes status to 'issued'.
- `applyVoucher(invoice, { code, amount })` — Applies a fixed-amount voucher (draft invoices only). One voucher per invoice. Sets `invoice.voucher = { code, amount }`.

### src/payments.js
Payment tracking and recording:
- `recordPayment(invoice, { amount, date })` — Records a payment on an issued or partially_paid invoice. Amount must be a positive integer; cannot exceed balance due. Updates status: 'issued' → 'partially_paid' or 'paid'. Adds to `invoice.payments` array (creates if missing).
- `balanceDue(invoice)` — Returns the amount still owed (total minus payments, clamped to 0).
- `totalPaid(invoice)` — Returns the sum of all recorded payments.

### src/statements.js
Customer account statements:
- `statement(customerId, invoices, asOf)` — Generates a statement for a customer as of a given date. Returns `{ customerId, invoices, totalDue }` where invoices lists issued/partially_paid invoices on or before asOf, sorted by issueDate, each with `{ number, issueDate, dueDate, total, due }`. Normalizes customer ID and validates date.

### src/credits.js
Credit note management:
- `createCreditNote(invoice, { amount, reason, date }, existingNumbers)` — Creates a credit note (refund) for an issued, partially_paid, or paid invoice. Amount must be positive integer and not exceed invoice total. Returns `{ number, invoiceNumber, customerId, amount, reason, date }`. Credit note numbers (CN-YYYY-NNNN) are independent of invoice numbers, with their own yearly counter.

### src/dates.js
Date validation and arithmetic (all in UTC):
- `isValidDate(text)` — Validates dates in YYYY-MM-DD format (rejects invalid dates like Feb 30, non-leap-year Feb 29, etc.).
- `addDays(dateStr, n)` — Adds n days to a date (UTC arithmetic). Returns YYYY-MM-DD string. Handles positive/negative days, month/year boundaries, leap years.
- `daysBetween(a, b)` — Returns whole number of days from date a to date b (UTC). Positive if b is later.

### src/customers.js
Customer management with ID normalization and tier pricing:
- `normalizeId(id)` — Trims whitespace and converts to uppercase. Used by `getCustomer()` and `createInvoice()` before any comparison or storage.
- `getCustomer(id)` — Looks up a customer by normalized ID.
- `TIER_DISCOUNTS` — Exported object mapping tier names to discount percentages: `{ gold: 5, silver: 2.5, standard: 0 }`.

### src/numbering.js
Invoice number generation:
- `nextInvoiceNumber(existingNumbers, issueDate)` — Returns the next invoice number for the year of issueDate. Ignores numbers from other years.

### src/render.js
Output rendering:
- `renderInvoiceText(invoice)` — Renders an invoice as plain text. Shows invoice number (or DRAFT), customer name, line details with formatted amounts. Shows VAT line if VAT > 0 (above the total). All amounts formatted via `formatEuros()`.

### src/reports.js
Business reports and analytics:
- `overdueInvoices(invoices, asOf)` — Returns overdue invoices. Filters for status 'issued' or 'partially_paid' with dueDate before asOf. Returns `{ ok: true, value: [{ number, customerId, dueDate, daysOverdue, due }] }` sorted by daysOverdue descending (most overdue first). Validates asOf date.
- `vatSummary(invoices)` — Generates VAT summary. Filters for status 'issued', 'partially_paid', or 'paid'. Groups lines by VAT rate and accumulates base amount (after discount) and VAT. Returns `[{ rate, base, vat }]` sorted by rate high to low.
- `lateFee(invoice, asOf)` — Calculates late fees. Returns 0 if not overdue. If overdue, calculates 0.04% per day: `balanceDue * 0.0004 * daysOverdue`, rounded to cents. Returns `{ ok: true, value: fee }` or `{ ok: false, error: 'DATE_INVALID' }`.

### src/export.js
Data export utilities:
- `exportCsv(invoices)` — Exports invoices as CSV string. Header: `number,customer,issueDate,dueDate,status,subtotal,discount,vat,total,due`. One line per invoice in order given. Customer field is customer name. Shows "DRAFT" for unseen invoices. Amounts are euros with 2 decimals and dot (no currency sign, no thousands separator). CSV escaping: double quotes around fields containing commas/quotes/newlines; double internal quotes.

### src/errors.js
Centralized error codes with messages:
- `AMOUNT_INVALID` — Amount must be a whole, positive number of cents.
- `CREDIT_TOO_HIGH` — Credit note amount exceeds the invoice total.
- `CUSTOMER_INVALID` — A customer needs an id, a name and a valid email.
- `CUSTOMER_NOT_FOUND` — No customer with that id.
- `DATE_INVALID` — Issue date must be a valid date in YYYY-MM-DD format.
- `DISCOUNT_INVALID` — Discount percent must be a number from 0 to 100.
- `LINE_NOT_FOUND` — No line with that SKU on the invoice.
- `NO_LINES` — An invoice must have at least one line.
- `NOT_DRAFT` — Can only edit invoices with draft status.
- `NOT_ISSUED` — Can only record payments on issued or partially paid invoices.
- `OVERPAYMENT` — Payment amount exceeds the balance due.
- `QTY_INVALID` — Line quantity must be a positive integer.
- `TERMS_INVALID` — Payment terms must be NET14, NET30, or EOM.
- `UNKNOWN_SKU` — No product with that SKU in the catalogue.
- `VOUCHER_EXISTS` — An invoice can only have one voucher.

### Test Files
- `test/invoices.test.js` — 171 tests for invoice operations (create, add, remove, issue, totals, discounts, VAT, terms, vouchers).
- `test/dates.test.js` — 22 tests for date validation and arithmetic (format, leap years, boundaries, UTC, roundtrips).
- `test/customers.test.js` — 14 tests for customer lookup and ID normalization.
- `test/numbering.test.js` — 7 tests for invoice numbering.
- `test/render.test.js` — 15 tests for text rendering (with VAT display).
- `test/payments.test.js` — 18 tests for payment recording and balance calculations.
- `test/statements.test.js` — 17 tests for customer statements.
- `test/credits.test.js` — 23 tests for credit note creation and numbering.
- `test/reports.test.js` — 20 tests for overdue invoices, VAT summaries, and late fees.
- `test/export.test.js` — 19 tests for CSV export functionality.
- `test/money.test.js` — 23 tests for money utilities including currency conversion and formatting.
- `test/catalogue.test.js` — Pre-existing tests for product catalogue.

## What's Not Built Yet

- **Invoice storage** — No database or file persistence; invoices are held in memory.
- **Invoice editing** — No support for modifying issued invoices (they are locked by design).
- **Credit note application** — Credit notes are created but not applied to reduce invoice balance or status.
- **Dunning letters** — No automated overdue payment notifications or reminders.
- **Bulk operations** — No batch invoice creation, export, or import.
- **Audit logs** — No tracking of changes or who made them.
- **API endpoints** — No REST or GraphQL API (this is a data module, not a server).
- **Email/notifications** — No email delivery or integration.

## How to Run Tests

```bash
npm test
```

All 272 tests should pass (breakdown: 171 invoice + 22 date + 14 customer + 7 numbering + 15 render + 18 payment + 17 statement + 23 credit + 20 reports + 19 export + 23 money + 4 catalogue).

## Code Organization

- **src/invoices.js** — Invoice CRUD and all calculations (line total, discount, VAT, totals, terms, vouchers).
- **src/payments.js** — Payment recording, balance calculation, status updates.
- **src/statements.js** — Customer account statements with aging.
- **src/credits.js** — Credit note (refund) management and numbering.
- **src/reports.js** — Business reports: overdue invoices, VAT summaries, late fees.
- **src/export.js** — CSV export for invoices.
- **src/dates.js** — Date validation and UTC arithmetic.
- **src/customers.js** — Customer lookup and ID normalization.
- **src/numbering.js** — Invoice number generation.
- **src/render.js** — Text output rendering (with VAT display).
- **src/money.js** — Money utilities: rounding, euro formatting, currency conversion (EUR/USD/GBP).
- **src/catalogue.js** — Product lookup. Pre-existing.
- **src/result.js** — ok/fail result types. Pre-existing.
- **src/errors.js** — Centralized error codes.
- **data/customers.json** — Customer data (id, name, email, country, tier). Pre-existing.
- **data/catalogue.json** — Product catalogue (sku, name, unitPrice, vatRate). Pre-existing.

## Next Steps for Future Requests

When continuing this work:
1. Read this handoff to understand the rules, decisions, and structure.
2. Check `src/dates.js` for date arithmetic; always use UTC via `isValidDate()`, `addDays()`, `daysBetween()`.
3. Check `src/customers.js` for `normalizeId()`; always normalize customer IDs before lookup or storage.
4. Remember the hierarchy: line discounts > tier discounts (tier is only applied if line discount is undefined).
5. VAT is computed per line on the discounted amount, not on line total or invoice subtotal.
6. Invoice totals are: `subtotal - discount + vat - voucher` (all clamped to 0).
7. Payment recording updates invoice status: `issued` → `partially_paid` or `paid` based on balance due.
8. Payment terms are set at invoice creation; supported values are NET14, NET30 (default), and EOM.
9. Vouchers are fixed-amount discounts, applied to drafts only, one per invoice.
10. Credit notes have independent numbering (CN-YYYY-NNNN) separate from invoices; cannot exceed invoice total.
11. Customer statements filter for issued/partially_paid/paid invoices on or before asOf, sorted by issueDate.
12. Overdue invoices (from `src/reports.js`) filter for 'issued' or 'partially_paid' with dueDate before asOf, sorted by daysOverdue descending.
13. Late fees are 0.04% per day overdue: `balanceDue * 0.0004 * daysOverdue`, always rounded to cents.
14. VAT summaries group all lines by VAT rate across all issued/partially_paid/paid invoices, returning base (after discount) and VAT per rate.
15. CSV export formats amounts in plain euros (1234.50, no currency sign, no thousands separator); escapes CSV fields properly (double quotes).
16. Currency conversion uses `RATES` (EUR: 1, USD: 1.085, GBP: 0.8425); always convert EUR cents via `convert(cents, currency)`.
17. `formatMoney(cents, currency)` converts EUR cents and formats with proper symbol ($, £, €) and thousands separators.
18. Every amount is integer cents; use `roundCents()` for fractional calculations.
19. Never throw for bad input; use `fail(CODE)` and add the code to `ERRORS`.
20. Never mutate arguments; always return new objects/arrays.
21. Clamp all computed amounts to 0 minimum (no negatives).
22. Always run `npm test` before marking work done.
23. Add any new error codes to `ERRORS` in `src/errors.js` before using them.
