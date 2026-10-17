# Invoicekit Handoff

## Project Goal
Build a complete invoicing system into this Node.js project with:
- Draft creation, line item management, invoice numbering, and text rendering ✓
- Payment tracking with status transitions and payment history ✓
- Credit notes for refunds ✓
- Customer statements showing outstanding amounts ✓
- Vouchers and payment terms ✓
- Future: Persistence (database), PDF rendering, amendments/editing workflow

## House Rules (Apply to All Future Work)

1. **Money is always integer cents**
   - Never store or return fractional amounts
   - When calculations produce fractions, round with `roundCents()` from `src/money.js`
   - Every amount shown to customers goes through `formatEuros()` from `src/money.js`

2. **Never throw for bad input**
   - Return `fail(CODE)` from `src/result.js`
   - Add every new error code to `ERRORS` in `src/errors.js` with a one-line message
   - Codes are UPPER_SNAKE_CASE

3. **Never mutate arguments**
   - Return new objects and arrays instead
   - Preserve all existing fields when transforming invoices

4. **Always normalize customer IDs**
   - Use `normalizeId(id)` from `src/customers.js` before comparing or storing
   - This trims whitespace and converts to uppercase
   - Decision: accepts messy input like `'c-007 '` or `' C-003 '`, stores canonical `'C-NNN'`

5. **Dates are YYYY-MM-DD strings everywhere**
   - All date arithmetic done in UTC, never in the machine's local time zone
   - Use date functions from `src/dates.js`: `isValidDate()`, `addDays()`, `daysBetween()`
   - Create Date objects with explicit UTC: `new Date(dateStr + 'T00:00:00Z')`

6. **No amount may go below zero**
   - Clamp all computed amounts at 0 (never negative)
   - Applies to line totals, discounts, VAT, invoice totals

7. **Run `npm test` before completing each request**

## Architectural Decisions

### Invoice Numbers
Format: `INV-<year>-<counter>`
- Year is extracted from the invoice's issue date
- Counter is 4 digits, zero-padded (0001–9999)
- Counter restarts at 0001 every calendar year
- Gaps and out-of-order numbers are allowed
- Implemented in `src/numbering.js`

### Invoice Data Model
Invoices are self-contained records:
- `customerId`: Customer ID (always normalized to uppercase)
- `customerName`: Customer name (looked up at creation, stored for historical accuracy)
- `issueDate`: Date in YYYY-MM-DD format
- `number`: Invoice number (undefined for draft, set on issue)
- `status`: 'draft', 'issued', 'partially_paid', or 'paid'
- `terms`: Payment terms ('NET14', 'NET30' default, or 'EOM')
- `dueDate`: Payment due date (calculated from terms and issueDate)
- `lines`: Array of line items, each with:
  - `sku`: Product SKU
  - `name`: Product name (from catalogue)
  - `qty`: Positive integer quantity
  - `unitPrice`: Cents (from catalogue, without VAT)
  - `discountPercent`: Discount percentage (0-100, may have decimals like 12.5)
  - `vatRate`: Percent (from catalogue: 0, 9, or 21)
- `voucher`: Optional fixed discount, each with:
  - `code`: Voucher code
  - `amount`: Fixed discount in cents (applied after VAT)
- `payments`: Array of recorded payments, each with:
  - `amount`: Payment amount in cents
  - `date`: Payment date (YYYY-MM-DD)

### Line Item Management
- `addLine` adds a new line or increments qty if SKU exists
- `removeLine` prevents removing the last line (invoices must have ≥1 line)
- Both refuse to modify non-draft invoices (error: NOT_DRAFT)
- Both preserve immutability
- `addLine` does NOT apply tier discounts (only `createInvoice` does)

### Discount System
- **Line discounts**: Each line has optional `discountPercent` (0-100, decimals OK)
- **Tier discounts**: Customer tier determines default discount if line doesn't specify:
  - gold: 5%, silver: 2.5%, standard: 0%
  - Stored in `TIER_DISCOUNTS` export from `src/customers.js`
- **Decision**: Explicit line discount always wins, even if it's 0 (to override tier)
- Discount amount = lineTotal × (discountPercent / 100)

### VAT System
- **Per-line VAT**: Calculated on line amount after discount
- **Rounding**: Each line's VAT is rounded individually using `roundCents()`
- **Invoice VAT**: Sum of all line VATs (not a percentage of invoice total)
- Formula: `lineVAT = roundCents((lineTotal - lineDiscount) × vatRate / 100)`
- `invoiceTotals()` returns `{ subtotal, discount, vat, voucher, total }`
- `total = subtotal - discount + vat - voucher` (clamped to 0)
- `lineDiscount()` now rounds its result to ensure integer cents

### Payment Terms
- Three options: NET14 (14 days), NET30 (default), EOM (end of month)
- Terms set at invoice creation time with default NET30
- `dueDate` calculated and stored on invoice
- EOM calculation handles leap years correctly

### Vouchers
- Fixed discount applied after VAT (not a percentage)
- Amount must be positive integer in cents
- Maximum one voucher per invoice
- Can only be applied to draft invoices
- Vouchers are preserved through all invoice modifications and issuance

### Payment Tracking
- Invoices transition through statuses: draft → issued → partially_paid → paid
- Payments recorded with amount (cents) and date
- Multiple partial payments allowed
- Status updates automatically based on total paid vs. invoice total
- `balanceDue(invoice)` calculates remaining amount owed

### Customer ID Normalization
- All incoming customer IDs normalized before use
- `normalizeId(id)`: trim whitespace + uppercase
- `getCustomer(id)`: normalizes before lookup
- `createInvoice({ customerId, ... })`: normalizes and stores the canonical form
- Handles messy input like `'c-007 '`, `' C-003 '` → stored as `'C-007'`, `'C-003'`

### Date Handling
- All dates as 'YYYY-MM-DD' strings
- All date arithmetic in UTC (never local timezone)
- `isValidDate(text)`: strict validation, catches invalid leap years
- `addDays(date, n)`: add/subtract days in UTC
- `daysBetween(a, b)`: calculate days between dates (b - a)
- Implementation in `src/dates.js`

## What Has Been Built

### Core Modules

**src/invoices.js** — Invoice creation and management
- `createInvoice({ customerId, issueDate, lines, terms })` — Creates draft invoice with enriched lines from catalogue
  - Normalizes customer ID
  - Applies tier discount to lines without explicit discount
  - Accepts optional payment terms (default NET30)
  - Calculates and stores dueDate
  - Validates all inputs
- `addLine(invoice, { sku, qty, discountPercent })` — Adds or increments line (no tier discount)
- `removeLine(invoice, sku)` — Removes line by SKU (must have ≥1 line remaining)
- `lineTotal(line)` — Returns qty × unitPrice
- `lineDiscount(line)` — Returns roundCents(lineTotal × discountPercent / 100)
- `lineVAT(line)` — Returns roundCents((lineTotal - lineDiscount) × vatRate / 100)
- `invoiceTotals(invoice)` — Returns `{ subtotal, discount, vat, voucher, total }`
- `issueInvoice(invoice, existingNumbers)` — Assigns number, changes status to 'issued'
- `applyVoucher(invoice, { code, amount })` — Adds fixed discount to draft invoice (one per invoice)

**src/customers.js** — Customer data and normalization
- `getCustomer(id)` — Finds customer by (normalized) ID
- `listCustomers()` — Returns all customers
- `validateCustomer(c)` — Validates customer record structure
- `normalizeId(id)` — Trims and upper-cases
- `TIER_DISCOUNTS` — Export: `{ gold: 5, silver: 2.5, standard: 0 }`

**src/numbering.js** — Invoice number generation
- `nextInvoiceNumber(existingNumbers, issueDate)` — Generates next free invoice number for year

**src/render.js** — Plain text invoice rendering
- `renderInvoiceText(invoice)` — Renders invoice as text
  - Shows: DRAFT/number, customer name, line items, subtotal, discount (if any), VAT (if any), total

**src/dates.js** — Date utilities
- `isValidDate(text)` — Validates YYYY-MM-DD format and actual date validity
- `addDays(date, n)` — Adds n days in UTC
- `daysBetween(a, b)` — Returns days between (b - a) in UTC

**src/payments.js** — Payment recording and balance tracking
- `recordPayment(invoice, { amount, date })` — Records a payment on an issued or partially_paid invoice
  - Updates invoice status to 'partially_paid' or 'paid'
  - Accumulates multiple payments
  - Returns new invoice object with payment history
- `balanceDue(invoice)` — Calculates remaining amount owed
  - Returns total minus all recorded payments (clamped at 0)

**src/statements.js** — Customer statements
- `statement(customerId, invoices, asOf)` — Generates a customer statement
  - Filters invoices by customer (normalized ID) and date
  - Includes only issued, partially_paid, or paid invoices
  - Returns list with { number, issueDate, dueDate, total, due } for each
  - Sorted by issueDate
  - Returns totalDue (sum of all due amounts)

**src/credits.js** — Credit notes for refunds
- `nextCreditNoteNumber(existingNumbers, issueDate)` — Generates CN numbers (CN-YYYY-NNNN format)
  - Separate counter from invoices (ignores INV numbers)
  - Per-year counter resets at 0001
- `createCreditNote(invoice, { amount, reason, date }, existingNumbers)` — Creates a credit note
  - Works on issued, partially_paid, or paid invoices
  - Amount must be positive integer and not exceed invoice total
  - Returns { number, invoiceNumber, customerId, amount, reason, date }

**src/errors.js** — Error code registry
- Error codes: AMOUNT_INVALID, CUSTOMER_INVALID, CUSTOMER_NOT_FOUND, UNKNOWN_SKU, DATE_INVALID, NO_LINES, QTY_INVALID, NOT_DRAFT, LINE_NOT_FOUND, DISCOUNT_INVALID, NOT_ISSUED, OVERPAYMENT, TERMS_INVALID, VOUCHER_EXISTS, CREDIT_TOO_HIGH
- `message(code)` — Returns human-readable error message

### Tests
- `test/invoices.test.js` — 173 tests for invoice functions (creation, lines, terms, vouchers, payments preservation)
- `test/payments.test.js` — 14 tests for payment recording and balance calculation
- `test/statements.test.js` — 20 tests for customer statement generation
- `test/credits.test.js` — 16 tests for credit note creation and numbering
- `test/customers.test.js` — 10 tests for customer operations and ID normalization
- `test/render.test.js` — 10 tests for text rendering
- `test/numbering.test.js` — 7 tests for invoice number generation
- `test/dates.test.js` — 21 tests for date utilities
- `test/money.test.js` — 4 tests for money rounding and formatting
- `test/catalogue.test.js` — 4 tests for product data

**All 206 tests pass.**

## What's Not Done (Future Work)

- Editing issued invoices (amendments workflow beyond credit notes)
- Persistence (database storage, retrieval, updates)
- PDF rendering (beyond plain text)
- Dunning (late payment reminders)
- Partial credit note application to invoice balance
- Recurring/subscription invoices
- Multiple currencies
- Tax compliance reporting
- Audit trail/invoice modification history

## How to Run Tests

```bash
npm test
```

All tests use Node's built-in `node:test` module. No external test framework.

## Key Files to Know

- `src/invoices.js` — Core invoice operations and totals calculation
- `src/payments.js` — Payment recording and balance tracking
- `src/statements.js` — Customer statement generation
- `src/credits.js` — Credit note creation and numbering
- `src/money.js` — `roundCents()`, `formatEuros()`, `parseEuros()`
- `src/customers.js` — `getCustomer(id)`, `listCustomers()`, `normalizeId(id)`, `TIER_DISCOUNTS`
- `src/catalogue.js` — `getProduct(sku)`, `listProducts()`
- `src/result.js` — `ok(value)`, `fail(error, details)`
- `src/dates.js` — `isValidDate()`, `addDays()`, `daysBetween()`
- `src/errors.js` — All error codes and messages
- `data/customers.json` — Customer records (id, name, email, country, tier)
- `data/catalogue.json` — Product records (sku, name, unitPrice, vatRate)

## Integration Points for Next Agent

### When Adding New Features

1. **Invoice data model**: Update all functions that create/transform invoices to preserve new fields (`createInvoice`, `addLine`, `removeLine`, `issueInvoice`, `recordPayment`)
2. **Error handling**: Add new error codes to `src/errors.js` before using them
3. **Immutability**: Never mutate arguments; return new objects/arrays with spread or map
4. **Customer IDs**: Always normalize with `normalizeId()` before comparing or storing
5. **Date operations**: Use date functions from `src/dates.js`; all dates as YYYY-MM-DD strings in UTC
6. **Money calculations**: Round with `roundCents()` after any arithmetic; clamp negative amounts to 0
7. **Testing**: Add tests immediately when creating new functions; run `npm test` before finishing
8. **Rendering**: Update `renderInvoiceText` if new invoice fields should be displayed

### Key Design Patterns

- **Status transitions**: draft → issued → partially_paid → paid (one-way, automatic on payment)
- **Number generation**: Separate counters for invoices (INV-YYYY-NNNN) and credit notes (CN-YYYY-NNNN)
- **Amount calculations**: Always integer cents; totals = subtotal - discount + vat - voucher (clamped ≥ 0)
- **Field preservation**: When returning modified invoices, include all original fields plus any new ones
- **Customer data**: Normalized IDs stored; customer names frozen on invoice creation for historical accuracy

### Before Implementing Persistence

1. Ensure all invoice state (payments, vouchers, credit notes) can be round-tripped
2. Consider invoice immutability: issued invoices should not be mutable (use credit notes for refunds)
3. Payment history is append-only (never delete or modify recorded payments)
4. Credit notes reference invoice numbers, not invoice objects
5. Test backwards compatibility when adding fields to existing invoice records
