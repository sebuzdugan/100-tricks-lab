# Invoicekit: Handoff Documentation

## Project Goal

Build an invoicing system that allows creating, modifying, issuing, and rendering invoices with proper money handling, validation, customer management, and discount/VAT support.

## House Rules (Non-Negotiable)

1. **Money handling**: All monetary amounts are integers representing cents. Never store or return fractional cents. Use `roundCents()` from `src/money.js` when calculations produce fractions.

2. **Error handling**: Never throw errors for bad input. Always return `fail(CODE)` from `src/result.js`. Add every new error code to the `ERRORS` object in `src/errors.js` with a one-line message.

3. **Immutability**: Never mutate function arguments. Always return new objects and arrays.

4. **Verification**: Run `npm test` before declaring any work complete.

5. **Dates**: All dates are 'YYYY-MM-DD' strings everywhere. All date arithmetic is done in UTC, never in the machine's local time zone. Use utilities from `src/dates.js`.

6. **Customer IDs**: Always normalize customer IDs using `normalizeId()` from `src/customers.js` before comparison or storage. IDs reach us in mixed case with stray spaces; normalization handles this consistently.

7. **No amounts below zero**: Every amount computed (on a line, an invoice, or anything else) is clamped at 0. No negative totals, discounts, or VAT.

## Project Decisions

1. **Invoice numbering format**: `INV-<year>-<counter>`
   - Year extracted from invoice issue date
   - Counter is 4 digits, zero-padded (0001, 0002, ..., 9999)
   - Counter restarts at 0001 each year
   - Example: `INV-2026-0042`

2. **Customer-facing amounts**: All amounts displayed to customers must be formatted via `formatEuros()` from `src/money.js`. Output: "€1,234.56"

3. **Invoice lifecycle states**: At least "draft" and "issued". More states may be added later.

4. **Line discounts**: 
   - Optional `discountPercent` (0-100, can have decimals like 12.5)
   - Invalid values return `DISCOUNT_INVALID`
   - Discount = line total × discountPercent / 100
   - Line discount is rounded per line using `roundCents()`

5. **Customer tier discounts**:
   - Gold tier: 5% default discount
   - Silver tier: 2.5% default discount
   - Standard tier: 0% default discount
   - Tier discounts stored in `TIER_DISCOUNTS` from `src/customers.js`
   - Explicit `discountPercent` on a line (even 0) always overrides tier discount
   - Only `createInvoice()` applies tier discounts, not `addLine()`

6. **VAT calculation**:
   - Every line has a `vatRate` (21, 9, or 0 percent)
   - VAT is computed per line on the line's amount after discount
   - Each line's VAT is rounded individually using `roundCents()`
   - Invoice VAT is the sum of rounded line VATs (never a percentage of invoice total)
   - `invoiceTotals` returns `{ subtotal, discount, vat, total }` with total = subtotal - discount + vat

7. **Text rendering**:
   - `renderInvoiceText()` shows VAT line only when VAT > 0, placed just above Total

## What's Been Built

### Core Data Structures

An **Invoice** object has:
```javascript
{
  customerId: string,         // normalized (e.g., "C-001")
  issueDate: string,          // YYYY-MM-DD format
  number?: string,            // e.g., "INV-2026-0001" (absent on draft)
  status: string,             // "draft" or "issued"
  lines: Array<{
    sku: string,
    name: string,             // from catalogue
    qty: number,              // positive integer
    unitPrice: number,        // cents, from catalogue
    vatRate: number,          // percent: 0, 9, or 21
    discountPercent?: number, // 0-100, can be decimal (applied from tier or explicit)
  }>
}
```

### Module: `src/invoices.js`

**`createInvoice({ customerId, issueDate, lines })`**
- Creates a draft invoice
- Normalizes customerId before storage
- Applies tier discounts to lines without explicit discountPercent
- Validates: customer exists, date is valid YYYY-MM-DD, lines non-empty, qty positive integers, SKUs exist, discountPercent valid
- Error codes: CUSTOMER_NOT_FOUND, DATE_INVALID, NO_LINES, QTY_INVALID, UNKNOWN_SKU, DISCOUNT_INVALID

**`lineTotal(line)`**
- Returns qty × unitPrice in cents

**`lineDiscount(line)`**
- Returns discount amount for a line in cents
- Discount = lineTotal × (discountPercent ?? 0) / 100, rounded and clamped at 0

**`lineVAT(line)`**
- Returns VAT amount for a line in cents
- VAT = (lineTotal - lineDiscount) × vatRate / 100, rounded and clamped at 0

**`invoiceTotals(invoice)`**
- Returns `{ subtotal, discount, vat, total }` (all in cents)
- subtotal = sum of all line totals
- discount = sum of all line discounts
- vat = sum of all line VATs
- total = subtotal - discount + vat, clamped at 0

**`addLine(invoice, { sku, qty, discountPercent })`**
- Adds a new line or increases qty if SKU already present
- Works on draft invoices only
- Does NOT apply tier discount (use explicit discountPercent if needed)
- Validates: qty positive integer, SKU exists, discountPercent valid
- Error codes: QTY_INVALID, UNKNOWN_SKU, NOT_DRAFT, DISCOUNT_INVALID

**`removeLine(invoice, sku)`**
- Removes a line by SKU
- Works on draft invoices only
- Prevents removing the last line
- Error codes: LINE_NOT_FOUND, NO_LINES, NOT_DRAFT

**`issueInvoice(invoice, existingNumbers)`**
- Transitions a draft invoice to issued
- Assigns the next invoice number
- Error codes: NOT_DRAFT

### Module: `src/numbering.js`

**`nextInvoiceNumber(existingNumbers, issueDate)`**
- Generates the next invoice number for a given year
- Input: array of existing invoice numbers (in any order), issue date in YYYY-MM-DD format
- Output: next number, e.g., "INV-2026-0003"

### Module: `src/render.js`

**`renderInvoiceText(invoice)`**
- Renders an invoice as plain text (human-readable)
- Returns `ok(text)` where text is newline-separated lines:
  1. Invoice number or "DRAFT"
  2. Customer name
  3. One line per invoice line: `qty x name @ €unitPrice = €lineTotal`
  4. VAT line (if VAT > 0): `VAT: €amount`
  5. Final line: `Total: €amount`
- All amounts formatted via `formatEuros()`
- Error codes: CUSTOMER_NOT_FOUND

### Module: `src/customers.js`

**`getCustomer(id)`**
- Normalizes id, then finds customer by normalized id
- Returns `ok(customer)` or `fail('CUSTOMER_NOT_FOUND')`

**`listCustomers()`**
- Returns all customers (each with: id, name, email, country, tier)

**`validateCustomer(c)`**
- Validates a customer record before storage
- Error codes: CUSTOMER_INVALID

**`normalizeId(id)`**
- Trims whitespace and uppercases customer ID
- E.g., ' c-007 ' → 'C-007'

**`TIER_DISCOUNTS`** (constant)
- `{ gold: 5, silver: 2.5, standard: 0 }`

### Module: `src/dates.js`

**`isValidDate(text)`**
- Validates YYYY-MM-DD format with round-trip checking
- Rejects invalid dates like Feb 30
- Handles leap years correctly

**`addDays(date, n)`**
- Adds n days to a YYYY-MM-DD date (UTC)
- Returns YYYY-MM-DD format

**`daysBetween(a, b)`**
- Calculates b minus a in whole days (UTC)
- Returns integer

### Module: `src/money.js`

**`roundCents(x)`**
- Half to even (banker's rounding)
- Example: 124.5 → 124, 125.5 → 126

**`formatEuros(cents)`**
- Formats cents as "€1,234.56"

**`parseEuros(text)`**
- Parses "12", "12.5", "1,234.56" into cents

### Module: `src/result.js`

**`ok(value)`** and **`fail(error)`**
- Result objects: `{ ok: true, value }` or `{ ok: false, error }`

### Module: `src/errors.js`

Error codes and messages:
- AMOUNT_INVALID, CUSTOMER_INVALID, CUSTOMER_NOT_FOUND
- DATE_INVALID, DISCOUNT_INVALID
- LINE_NOT_FOUND, NO_LINES, NOT_DRAFT
- QTY_INVALID, UNKNOWN_SKU

### Test Suites

- **`test/invoices.test.js`** (79 tests): Invoice CRUD, line operations, discounts, VAT, ID normalization
- **`test/customers.test.js`** (11 tests): Customer lookup, ID normalization
- **`test/numbering.test.js`** (9 tests): Invoice number generation
- **`test/render.test.js`** (9 tests): Text rendering with VAT line
- **`test/money.test.js`** (4 tests): Rounding and formatting
- **`test/catalogue.test.js`** (4 tests): Product lookup
- **`test/dates.test.js`** (21 tests): Date validation and arithmetic

**Total: 145 tests, all passing**

## Known Limitations / Future Work

1. **VAT**: Fully implemented. Line VAT is calculated after discount, rounded per line.

2. **Invoice modification after issue**: Cannot edit issued invoices (by design, NOT_DRAFT error). Credit notes / amendments not yet designed.

3. **Persistence**: No storage layer. Invoices exist only in memory.

4. **PDF/HTML rendering**: Only plain-text rendering exists.

5. **Invoice status lifecycle**: Only "draft" → "issued". No transitions for paid, archived, cancelled, etc.

6. **Compliance**: No audit trails, versioning, or signature support.

## Running Tests

```bash
npm test
```

This runs all tests in `test/*.test.js` using Node's built-in test runner. Output shows pass/fail count and duration.

## Key Files Overview

```
src/
  invoices.js       - Invoice CRUD, calculations (line total, discount, VAT, totals)
  numbering.js      - Invoice number generation
  render.js         - Plain-text rendering
  customers.js      - Customer lookup, ID normalization, tier discounts
  dates.js          - Date validation and arithmetic (UTC)
  errors.js         - Error codes and messages
  result.js         - ok() and fail() helpers
  money.js          - roundCents(), formatEuros(), parseEuros()
  catalogue.js      - Product lookup

test/
  invoices.test.js  - 79 tests (CRUD, calculations, discounts, VAT, ID normalization)
  customers.test.js - 11 tests (lookup, normalization)
  numbering.test.js - 9 tests (number generation)
  render.test.js    - 9 tests (text rendering with VAT)
  money.test.js     - 4 tests (rounding, formatting)
  catalogue.test.js - 4 tests (product lookup)
  dates.test.js     - 21 tests (date validation and arithmetic)

data/
  customers.json    - Customer records (id, name, email, country, tier)
  catalogue.json    - Product catalogue (sku, name, unitPrice, vatRate)

HANDOFF.md          - This file
package.json        - npm configuration
```

## Next Steps Guidance

When continuing this work:

1. **Before any changes**: Run `npm test` to establish baseline
2. **When adding features**: Follow existing patterns (result objects, error codes, immutability, UTC dates, cents for money)
3. **When touching money**: Always use cents (integers) and `roundCents()` for calculations
4. **When handling dates**: Use utilities from `src/dates.js`, work in UTC
5. **When handling customer IDs**: Always normalize with `normalizeId()`
6. **When rendering**: Always use `formatEuros()` for customer-facing amounts
7. **When done**: Add tests and ensure `npm test` passes

Likely future tasks:
- Persisting invoices (loading/saving)
- Credit notes or amendments
- Recurring invoices
- Payment tracking and status
- PDF rendering
- Email delivery
- Multi-currency support
