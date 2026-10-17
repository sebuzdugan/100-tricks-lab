# Invoicing System Handoff

## Project Goal

Building an invoicing system for a business that issues invoices to customers for products and services from a catalogue. The system manages invoice creation, editing, numbering, and rendering.

## House Rules (All Requests)

These rules apply to every request in this project:

1. **Money is always integer cents.** Never store or return fractional amounts. When a calculation produces a fraction of a cent, round it using `roundCents()` from `src/money.js`.

2. **Never throw for bad input.** Return `fail(CODE)` from `src/result.js` instead, and add every new error code to `ERRORS` in `src/errors.js` with a one-line message.

3. **Never mutate an argument.** Return new objects and arrays instead. This is critical for immutability.

4. **Run `npm test` before you say a request is done.** All changes must pass the full test suite.

## Key Decisions

- **Invoice numbers** are formatted as `INV-<year>-<counter>`, where year is the issue date's year and counter is 4 digits, zero-padded, starting at 0001 and resetting every year. Example: `INV-2026-0042`.
- **Customer amounts shown to end users** (in rendered output) always go through `formatEuros()` from `src/money.js`. This ensures consistent euro formatting with thousands separators and two decimals.
- **Invoice statuses**: `draft` (editable), `issued` (with number, locked).

## What Has Been Built

### src/invoices.js
Core invoice operations:
- `createInvoice({ customerId, issueDate, lines })` — Creates a draft invoice. Validates customer, date format, line quantities, and SKUs. Enriches lines with product details (name, unitPrice, vatRate) from the catalogue.
- `lineTotal(line)` — Returns qty × unitPrice in cents.
- `invoiceTotals(invoice)` — Returns `{ subtotal, total }`. For now, total = subtotal (VAT and discounts come later).
- `addLine(invoice, { sku, qty })` — Adds a new line to a draft invoice, or increases qty if that SKU already exists. Validates qty and SKU.
- `removeLine(invoice, sku)` — Removes a line from a draft invoice. Prevents removal of the last line (NO_LINES).
- `issueInvoice(invoice, existingNumbers)` — Assigns a number and changes status from 'draft' to 'issued'. Looks up the next number using `nextInvoiceNumber()`.

### src/numbering.js
Invoice number generation:
- `nextInvoiceNumber(existingNumbers, issueDate)` — Returns the next invoice number for a given year. Ignores numbers from other years. Example: if existingNumbers contains `INV-2026-0001` and `INV-2026-0002`, returns `INV-2026-0003`.

### src/render.js
Output rendering:
- `renderInvoiceText(invoice)` — Renders an invoice as plain text. Shows invoice number (or DRAFT), customer name, line details with formatted amounts, and total. All amounts use `formatEuros()`.

### src/errors.js
Updated error codes (in addition to existing ones):
- `DATE_INVALID` — Issue date must be a valid date in YYYY-MM-DD format.
- `LINE_NOT_FOUND` — No line with that SKU on the invoice.
- `NO_LINES` — An invoice must have at least one line.
- `NOT_DRAFT` — Can only edit invoices with draft status.
- `QTY_INVALID` — Line quantity must be a positive integer.

### Test Files
- `test/invoices.test.js` — 39 tests for invoice operations (create, add, remove, issue, totals).
- `test/numbering.test.js` — 7 tests for invoice numbering.
- `test/render.test.js` — 9 tests for text rendering.

## What's Not Built Yet

- **Discounts** — invoiceTotals currently returns total = subtotal; no discount field.
- **VAT calculation** — Lines have vatRate, but it's not used in totals yet.
- **Invoice storage** — No database or file persistence; numbers are passed as arrays.
- **Customer lookup on render** — renderInvoiceText looks up customer by customerId using getCustomer(); if not found, it shows the customerId instead of failing.

## How to Run Tests

```bash
npm test
```

All 60 tests should pass (51 existing + 9 new for render).

## Code Organization

- **src/invoices.js** — All invoice CRUD and calculations.
- **src/numbering.js** — Invoice number generation (separated for clarity).
- **src/render.js** — Output rendering (kept separate to avoid bloating invoices.js).
- **src/money.js** — Money utilities (roundCents, formatEuros, parseEuros). Pre-existing.
- **src/customers.js** — Customer lookup. Pre-existing.
- **src/catalogue.js** — Product lookup. Pre-existing.
- **src/result.js** — ok/fail result types. Pre-existing.
- **src/errors.js** — Centralized error codes.

## Next Steps for Future Requests

When continuing this work:
1. Check this file to understand the rules and decisions.
2. Read the existing test files to see what's already tested.
3. Add any new error codes to ERRORS before using fail().
4. Always run `npm test` when done.
5. Remember: never throw, never mutate arguments, always use integer cents.
