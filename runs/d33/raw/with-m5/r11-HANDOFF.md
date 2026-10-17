# Invoicing System Handoff

## Project Goal

Building an invoicing system for a business that issues invoices to customers for products and services from a catalogue. The system manages invoice creation, editing, numbering, rendering, and handles line-level discounts, VAT, and customer tier pricing.

## House Rules (All Requests)

These rules apply to every request in this project:

1. **Money is always integer cents.** Never store or return fractional amounts. When a calculation produces a fraction of a cent, round it using `roundCents()` from `src/money.js`.

2. **Never throw for bad input.** Return `fail(CODE)` from `src/result.js` instead, and add every new error code to `ERRORS` in `src/errors.js` with a one-line message.

3. **Never mutate an argument.** Return new objects and arrays instead. This is critical for immutability.

4. **No amount we compute may ever go below zero.** Clamp all calculated amounts to 0 (subtotal, discount, VAT, total, line discounts, line VATs, etc.).

5. **Dates are YYYY-MM-DD strings in UTC.** All date arithmetic and comparisons happen in UTC using the utilities in `src/dates.js`, never in local timezone.

6. **Customer IDs are normalized.** All customer IDs are trimmed of whitespace and converted to uppercase using `normalizeId()` from `src/customers.js` before comparison or storage.

7. **Run `npm test` before you say a request is done.** All changes must pass the full test suite (currently 136 tests).

## Key Decisions

- **Invoice numbers** are formatted as `INV-<year>-<counter>`, where year is the issue date's year and counter is 4 digits, zero-padded, starting at 0001 and resetting every year. Example: `INV-2026-0042`.
- **Customer amounts shown to end users** (in rendered output) always go through `formatEuros()` from `src/money.js`. This ensures consistent euro formatting with thousands separators and two decimals.
- **Invoice statuses**: `draft` (editable), `issued` (with number, locked).
- **Line discounts** are per-line: a line can carry `discountPercent` (0–100, decimals allowed). If not specified, the customer's tier discount is applied (gold 5%, silver 2.5%, standard 0%). Explicit discounts (even 0) always override tier discounts.
- **VAT is computed per line** on the line's amount **after its discount**, and is rounded per line using `roundCents()`. The invoice's total VAT is the sum of all line VATs, never a percentage of invoice total.
- **Invoice totals** return `{ subtotal, discount, vat, total }`, where `total = subtotal - discount + vat`.
- **VAT is shown in rendered output** on its own line (only if VAT > 0) just above the total.
- **Customer tiers and their discounts** are kept in one place: `TIER_DISCOUNTS` in `src/customers.js` (gold: 5, silver: 2.5, standard: 0).

## What Has Been Built

### src/invoices.js
Core invoice operations and calculations:
- `createInvoice({ customerId, issueDate, lines })` — Creates a draft invoice. Normalizes customer ID, validates using `isValidDate()`, and enriches lines with product details. Applies tier discounts when `discountPercent` is undefined on a line. Stores normalized customer ID.
- `lineTotal(line)` — Returns qty × unitPrice in cents.
- `lineDiscount(line)` — Returns discount in cents (line total × discountPercent ÷ 100, rounded and clamped to 0).
- `lineVat(line)` — Returns VAT in cents (amount after discount × vatRate ÷ 100, rounded and clamped to 0).
- `invoiceTotals(invoice)` — Returns `{ subtotal, discount, vat, total }` where total = subtotal - discount + vat (all clamped to 0).
- `addLine(invoice, { sku, qty, discountPercent })` — Adds a line to a draft invoice (with optional discount). Validates `discountPercent` (0–100, must be a number).
- `removeLine(invoice, sku)` — Removes a line from a draft invoice. Prevents removal of the last line.
- `issueInvoice(invoice, existingNumbers)` — Assigns an invoice number and changes status to 'issued'.

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

### src/errors.js
Centralized error codes with messages:
- `AMOUNT_INVALID` — Amount must be a whole, positive number of cents.
- `CUSTOMER_INVALID` — A customer needs an id, a name and a valid email.
- `CUSTOMER_NOT_FOUND` — No customer with that id.
- `DATE_INVALID` — Issue date must be a valid date in YYYY-MM-DD format.
- `DISCOUNT_INVALID` — Discount percent must be a number from 0 to 100.
- `LINE_NOT_FOUND` — No line with that SKU on the invoice.
- `NO_LINES` — An invoice must have at least one line.
- `NOT_DRAFT` — Can only edit invoices with draft status.
- `QTY_INVALID` — Line quantity must be a positive integer.
- `UNKNOWN_SKU` — No product with that SKU in the catalogue.

### Test Files
- `test/invoices.test.js` — 109 tests for invoice operations (create, add, remove, issue, totals, discounts, VAT, ID normalization).
- `test/dates.test.js` — 22 tests for date validation and arithmetic (format, leap years, boundaries, UTC, roundtrips).
- `test/customers.test.js` — 14 tests for customer lookup and ID normalization.
- `test/numbering.test.js` — 7 tests for invoice numbering.
- `test/render.test.js` — 15 tests for text rendering (with VAT display).
- `test/money.test.js` — Pre-existing tests for money utilities.
- `test/catalogue.test.js` — Pre-existing tests for product catalogue.

## What's Not Built Yet

- **Invoice storage** — No database or file persistence; invoices are held in memory.
- **Invoice editing** — No support for modifying issued invoices (they are locked by design).
- **Payment tracking** — No payment status, payment dates, or payment reconciliation.
- **Bulk operations** — No batch invoice creation, export, or import.
- **Audit logs** — No tracking of changes or who made them.
- **API endpoints** — No REST or GraphQL API (this is a data module, not a server).

## How to Run Tests

```bash
npm test
```

All 136 tests should pass (breakdown: 109 invoice + 22 date + 14 customer + 7 numbering + 15 render + 4 money + 4 catalogue).

## Code Organization

- **src/invoices.js** — Invoice CRUD and all calculations (line total, discount, VAT, totals).
- **src/dates.js** — Date validation and UTC arithmetic (new).
- **src/customers.js** — Customer lookup and ID normalization (updated).
- **src/numbering.js** — Invoice number generation.
- **src/render.js** — Text output rendering (updated to show VAT).
- **src/money.js** — Money utilities (roundCents, formatEuros, parseEuros). Pre-existing.
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
6. Every amount is integer cents; use `roundCents()` for fractional calculations.
7. Never throw for bad input; use `fail(CODE)` and add the code to `ERRORS`.
8. Never mutate arguments; always return new objects/arrays.
9. Clamp all computed amounts to 0 minimum (no negatives).
10. Always run `npm test` before marking work done.
11. Add any new error codes to `ERRORS` in `src/errors.js` before using them.
