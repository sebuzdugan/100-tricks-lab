# Invoicing System — Handoff

## Project Goal

Build a complete invoicing system for this project, starting with core invoice creation, modification, numbering, and rendering. Future work includes VAT calculations, discounts, and additional output formats.

## House Rules (Apply to All Requests)

These rules are fundamental to this project and must be followed in all future work:

1. **Money is always integer cents.** Never store or return fractional amounts. When a calculation gives a fraction of a cent, round it using `roundCents()` from `src/money.js`. This ensures consistency across all monetary values.

2. **Never throw for bad input.** Return `fail(CODE)` from `src/result.js` instead, and add every new error code to `ERRORS` in `src/errors.js` with a one-line message. This provides consistent error handling across the API.

3. **Never mutate an argument.** Always return new objects and arrays instead. This ensures functions are predictable and don't have side effects.

4. **Run `npm test` before marking a request done.** All tests must pass before considering work complete.

## Key Decisions

1. **Invoice numbering format:** `INV-<year>-<counter>`, where:
   - Year comes from the invoice's issue date (YYYY)
   - Counter is 4 digits, zero-padded (0001, 0002, ..., 9999)
   - Counter restarts at 0001 every January

2. **Customer-facing amounts:** Every amount displayed to a customer must go through `formatEuros()` from `src/money.js`. This ensures consistent formatting (€ sign, thousands separators, two decimals) everywhere.

## What Has Been Built

### Core Invoice Operations (`src/invoices.js`)

- **`createInvoice({ customerId, issueDate, lines })`** — Creates a draft invoice with enriched line items. Each line is validated (qty must be positive integer, SKU must exist) and enriched with product details from the catalogue. Returns `ok(invoice)` or `fail(CODE)`.

- **`lineTotal(line)`** — Calculates total for a single line (qty × unitPrice in cents).

- **`invoiceTotals(invoice)`** — Calculates invoice totals, returns `{ subtotal, total }`. Currently subtotal equals total (VAT comes later).

- **`addLine(invoice, { sku, qty })`** — Adds a line to a draft invoice. If the SKU already exists, increases that line's quantity instead. Validates qty and SKU. Refuses to modify non-draft invoices (NOT_DRAFT).

- **`removeLine(invoice, sku)`** — Removes a line from a draft invoice by SKU. Refuses to remove the last line (NO_LINES) or modify non-draft invoices (NOT_DRAFT).

- **`issueInvoice(invoice, existingNumbers)`** — Issues a draft invoice by assigning the next available invoice number and changing status to 'issued'. Refuses if status isn't 'draft' (NOT_DRAFT).

### Invoice Numbering (`src/numbering.js`)

- **`nextInvoiceNumber(existingNumbers, issueDate)`** — Generates the next invoice number for a given year. Takes an array of existing numbers (any order) and issue date. Returns `INV-<year>-<counter>` format with proper zero-padding.

### Rendering (`src/render.js`)

- **`renderInvoiceText(invoice)`** — Renders an invoice as plain text:
  - First line: `DRAFT` or the invoice number (e.g., `INV-2024-0001`)
  - Second line: customer name
  - One line per item: `qty × name @ €unitPrice = €lineTotal`
  - Final line: `Total: €amount`
  - All amounts formatted via `formatEuros()`.

### Error Codes (`src/errors.js`)

Added to support invoicing operations:
- `DATE_INVALID` — Date must be in YYYY-MM-DD format
- `LINE_NOT_FOUND` — No line with that SKU on the invoice
- `NO_LINES` — Invoice must have at least one line
- `NOT_DRAFT` — Only draft invoices can be modified
- `QTY_INVALID` — Quantity must be a positive integer

Existing codes still in use:
- `CUSTOMER_NOT_FOUND` — No customer with that id
- `UNKNOWN_SKU` — No product with that SKU in the catalogue

## Test Coverage

All tests pass. Run with `npm test`:

- **`test/invoices.test.js`** (40 tests) — Tests for createInvoice, lineTotal, invoiceTotals, addLine, removeLine, issueInvoice. Covers validation, error cases, immutability.

- **`test/numbering.test.js`** (7 tests) — Tests for nextInvoiceNumber. Covers year handling, counter incrementing, zero-padding, unordered input.

- **`test/render.test.js`** (9 tests) — Tests for renderInvoiceText. Covers draft/issued display, customer names, line formatting, amount formatting.

- **Existing tests** (`test/customers.test.js`, `test/catalogue.test.js`, `test/money.test.js`) — All continue to pass.

Total: 61 passing tests.

## What's Unfinished

1. **VAT calculation** — Currently, invoiceTotals returns `{ subtotal, total }` with total = subtotal. VAT calculations need to be added to the total based on line VAT rates. Decision needed on whether to show VAT per-line or aggregate.

2. **Discounts** — No discount functionality yet. Will need to decide on application (per-line or invoice-level) and how to track them in the invoice object.

3. **Additional rendering formats** — Only plain text rendering exists. PDF, HTML, or other formats would be future additions.

4. **Invoice status workflow** — Currently only 'draft' and 'issued' exist. Future statuses (paid, overdue, cancelled) and transitions may be needed.

5. **Persistence** — No database or file storage yet. Data is all in-memory.

## How to Run Tests

```bash
npm test
```

All tests must pass before any request is considered complete. The test suite includes:
- Unit tests for each function
- Validation tests for error cases
- Immutability tests to ensure no mutations
- Integration tests combining multiple functions

## Code Organization

```
src/
  invoices.js       # Core invoice operations
  numbering.js      # Invoice number generation
  render.js         # Text rendering
  errors.js         # Error codes (update when adding new errors)
  money.js          # Existing: money formatting and parsing
  customers.js      # Existing: customer lookup
  catalogue.js      # Existing: product catalogue

test/
  invoices.test.js  # Tests for invoices.js
  numbering.test.js # Tests for numbering.js
  render.test.js    # Tests for render.js
  (existing tests)  # Unchanged

data/
  customers.json    # Customer database
  catalogue.json    # Product catalogue
```

## Next Steps for Future Work

1. **VAT Implementation** — Add VAT calculation to invoiceTotals. Decide on display strategy (itemized or aggregated).

2. **Discount Support** — Add discount fields to invoice and line items. Implement discount validation and calculation.

3. **Extended Rendering** — Add PDF or HTML rendering using the existing text renderer as a base.

4. **Persistence** — Add database or file-based storage for invoice numbers and invoices.

5. **Additional Status Transitions** — Implement workflow for payment, marking as paid, cancellation, etc.

When starting work on any of these, remember the house rules above and this handoff document.
