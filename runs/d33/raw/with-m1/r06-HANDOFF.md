# Invoicekit: Handoff Documentation

## Project Goal

Build an invoicing system that allows creating, modifying, issuing, and rendering invoices with proper money handling, validation, and customer management.

## House Rules (Non-Negotiable)

1. **Money handling**: All monetary amounts are integers representing cents. Never store or return fractional cents. Use `roundCents()` from `src/money.js` when calculations produce fractions.

2. **Error handling**: Never throw errors for bad input. Always return `fail(CODE)` from `src/result.js`. Add every new error code to the `ERRORS` object in `src/errors.js` with a one-line message.

3. **Immutability**: Never mutate function arguments. Always return new objects and arrays.

4. **Verification**: Run `npm test` before declaring any work complete.

## Project Decisions

1. **Invoice numbering format**: `INV-<year>-<counter>`
   - Year extracted from invoice issue date
   - Counter is 4 digits, zero-padded (0001, 0002, ..., 9999)
   - Counter restarts at 0001 each year
   - Example: `INV-2026-0042`

2. **Customer-facing amounts**: All amounts displayed to customers must be formatted via `formatEuros()` from `src/money.js`. This produces output like "€1,234.56".

3. **Invoice lifecycle states**: At least "draft" and "issued". More states may be added later (e.g., paid, archived).

## What's Been Built

### Core Data Structures

An **Invoice** object has:
```javascript
{
  customerId: string,      // e.g., "C-001"
  issueDate: string,       // YYYY-MM-DD format
  number?: string,         // e.g., "INV-2026-0001" (absent on draft)
  status: string,          // "draft" or "issued"
  lines: Array<{
    sku: string,
    name: string,          // from catalogue
    qty: number,           // positive integer
    unitPrice: number,     // cents, from catalogue
    vatRate: number,       // percent, from catalogue (0, 9, or 21)
  }>
}
```

### Module: `src/invoices.js`

**`createInvoice({ customerId, issueDate, lines })`**
- Creates a draft invoice
- Returns `ok(invoice)` or error
- Validates: customer exists, date is valid YYYY-MM-DD, lines non-empty, qty positive integers, SKUs exist
- Error codes: CUSTOMER_NOT_FOUND, DATE_INVALID, NO_LINES, QTY_INVALID, UNKNOWN_SKU

**`lineTotal(line)`**
- Simple calculation: `qty × unitPrice` in cents
- Returns a number

**`invoiceTotals(invoice)`**
- Returns `{ subtotal, total }` (both in cents)
- Currently subtotal = total (VAT not yet calculated)

**`addLine(invoice, { sku, qty })`**
- Adds a new line or increases qty if SKU already present
- Works on draft invoices only
- Returns `ok(newInvoice)` or error
- Validates: qty positive integer, SKU exists
- Error codes: QTY_INVALID, UNKNOWN_SKU, NOT_DRAFT

**`removeLine(invoice, sku)`**
- Removes a line by SKU
- Works on draft invoices only
- Prevents removing the last line
- Returns `ok(newInvoice)` or error
- Error codes: LINE_NOT_FOUND, NO_LINES, NOT_DRAFT

**`issueInvoice(invoice, existingNumbers)`**
- Transitions a draft invoice to issued
- Assigns the next invoice number
- Takes array of existing numbers to determine next counter
- Returns `ok(newInvoice)` with `number` set and `status: "issued"`
- Error codes: NOT_DRAFT

### Module: `src/numbering.js`

**`nextInvoiceNumber(existingNumbers, issueDate)`**
- Generates the next invoice number for a given year
- Input: array of existing invoice numbers (in any order), issue date in YYYY-MM-DD format
- Output: next number, e.g., "INV-2026-0003"
- Handles: multiple years, invalid formats in input, year transitions

### Module: `src/render.js`

**`renderInvoiceText(invoice)`**
- Renders an invoice as plain text (human-readable)
- Returns `ok(text)` where text is newline-separated lines:
  1. Invoice number or "DRAFT"
  2. Customer name
  3. One line per invoice line: `qty x name @ €unitPrice = €lineTotal`
  4. Final line: `Total: €amount`
- All amounts formatted via `formatEuros()`
- Error codes: CUSTOMER_NOT_FOUND

### Error Codes Added

In `src/errors.js`:
- `DATE_INVALID`: Issue date must be a valid date in YYYY-MM-DD format.
- `LINE_NOT_FOUND`: That SKU is not on the invoice.
- `NO_LINES`: An invoice must have at least one line.
- `NOT_DRAFT`: Can only modify invoices with status "draft".
- `QTY_INVALID`: Quantity must be a positive integer.

(Existing codes: AMOUNT_INVALID, CUSTOMER_INVALID, CUSTOMER_NOT_FOUND, UNKNOWN_SKU)

### Test Suites

- **`test/invoices.test.js`** (44 tests): All invoice CRUD and calculation functions
- **`test/numbering.test.js`** (9 tests): Invoice number generation across years
- **`test/render.test.js`** (9 tests): Text rendering with various invoice states

**Total: 68 tests, all passing**

## Known Limitations / Future Work

1. **VAT**: Currently `total = subtotal`. VAT rates are loaded from the catalogue but not yet calculated. When implemented:
   - Line total (VAT-exclusive): `qty × unitPrice`
   - Line VAT: `roundCents(lineTotal × vatRate / 100)`
   - Subtotal: sum of all line totals
   - Total VAT: sum of all line VATs
   - Total: `subtotal + totalVAT`

2. **Discounts**: Not yet implemented. Design decision pending.

3. **Invoice status lifecycle**: Only draft → issued so far. No transitions for paid, archived, cancelled, etc.

4. **Persistence**: No storage layer. Invoices exist only in memory.

5. **PDF/HTML rendering**: Only plain-text rendering exists.

6. **Invoice modification after issue**: Cannot edit issued invoices (by design with NOT_DRAFT error). Credit notes / amendments not yet designed.

## Running Tests

```bash
npm test
```

This runs all tests in `test/*.test.js` using Node's built-in test runner. Output shows pass/fail count and duration.

## Key Files Overview

```
src/
  invoices.js       - Main invoice CRUD and calculations
  numbering.js      - Invoice number generation
  render.js         - Plain-text rendering
  errors.js         - Updated with new error codes
  result.js         - ok() and fail() helpers (unchanged)
  money.js          - roundCents(), formatEuros(), parseEuros() (unchanged)
  customers.js      - Customer lookup (unchanged)
  catalogue.js      - Product lookup (unchanged)

test/
  invoices.test.js  - 44 tests
  numbering.test.js - 9 tests
  render.test.js    - 9 tests
  (Other test files for customers, catalogue, money unchanged)

data/
  customers.json    - Customer data (unchanged)
  catalogue.json    - Product/SKU data (unchanged)

HANDOFF.md          - This file
package.json        - npm config (unchanged)
```

## Next Steps Guidance

When continuing this work:

1. **Before any changes**: Run `npm test` to establish baseline
2. **When adding features**: Follow the existing patterns (result objects, error codes, immutability)
3. **When touching money**: Always use cents (integers) and `roundCents()` if needed
4. **When rendering**: Always use `formatEuros()` for customer-facing amounts
5. **When done**: Add tests and ensure `npm test` passes

The next likely tasks are VAT calculation and persisting invoices (loading/saving).
