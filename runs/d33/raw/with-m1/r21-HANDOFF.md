# Invoicekit: Handoff Documentation

## Project Goal

Build an invoicing system that allows creating, modifying, issuing, and rendering invoices with proper money handling, validation, customer management, discount/VAT support, payment tracking, and credit note management.

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

2. **Credit note numbering format**: `CN-<year>-<counter>`
   - Year extracted from credit note issue date
   - Counter is 4 digits, zero-padded (0001, 0002, ..., 9999)
   - Counter restarts at 0001 each year
   - Separate counter from invoices
   - Example: `CN-2026-0015`

3. **Customer-facing amounts**: All amounts displayed to customers must be formatted via `formatEuros()` or `formatMoney()` from `src/money.js`. Output: "€1,234.56", "$1,085.00", or "£842.50"

4. **Invoice lifecycle states**: "draft" (in preparation), "issued" (sent to customer), "partially_paid" (payment received but not full amount), "paid" (full payment received). Cannot edit issued invoices.

5. **Line discounts**: 
   - Optional `discountPercent` (0-100, can have decimals like 12.5)
   - Invalid values return `DISCOUNT_INVALID`
   - Discount = line total × discountPercent / 100
   - Line discount is rounded per line using `roundCents()`

6. **Customer tier discounts**:
   - Gold tier: 5% default discount
   - Silver tier: 2.5% default discount
   - Standard tier: 0% default discount
   - Tier discounts stored in `TIER_DISCOUNTS` from `src/customers.js`
   - Explicit `discountPercent` on a line (even 0) always overrides tier discount
   - Only `createInvoice()` applies tier discounts, not `addLine()`

7. **VAT calculation**:
   - Every line has a `vatRate` (21, 9, or 0 percent)
   - VAT is computed per line on the line's amount after discount
   - Each line's VAT is rounded individually using `roundCents()`
   - Invoice VAT is the sum of rounded line VATs (never a percentage of invoice total)
   - `invoiceTotals` returns `{ subtotal, discount, vat, voucher, total }` with total = subtotal - discount + vat - voucher

8. **Payment terms**:
   - Three standard terms: NET14 (14 days), NET30 (30 days, default), EOM (end of month)
   - Due date is calculated based on issue date and terms
   - Applied when creating an invoice via optional `terms` parameter

9. **Vouchers**:
   - Fixed-amount discount applied to invoice (not percentage-based)
   - Deducted after VAT calculation
   - One voucher per invoice maximum, draft-only
   - Format: `{ code: string, amount: number }`

10. **Text rendering**:
    - `renderInvoiceText()` shows VAT line only when VAT > 0, placed just above Total

11. **Foreign currency rates**:
    - EUR: 1 (base currency)
    - USD: 1.085 (units of USD per euro)
    - GBP: 0.8425 (units of GBP per euro)
    - Conversion uses `roundCents()` to ensure whole cents
    - Formatting via `formatMoney()` with appropriate symbol: $, £, or €

## What's Been Built

### Core Data Structures

An **Invoice** object has:
```javascript
{
  customerId: string,         // normalized (e.g., "C-001")
  issueDate: string,          // YYYY-MM-DD format
  number?: string,            // e.g., "INV-2026-0001" (absent on draft)
  status: string,             // "draft", "issued", "partially_paid", or "paid"
  terms: string,              // "NET14", "NET30" (default), or "EOM"
  dueDate: string,            // YYYY-MM-DD, calculated from issueDate + terms
  lines: Array<{
    sku: string,
    name: string,             // from catalogue
    qty: number,              // positive integer
    unitPrice: number,        // cents, from catalogue
    vatRate: number,          // percent: 0, 9, or 21
    discountPercent?: number, // 0-100, can be decimal (applied from tier or explicit)
  }>,
  voucher?: {                 // optional
    code: string,
    amount: number,           // cents
  },
  payments?: Array<{          // optional, populated by recordPayment
    amount: number,           // cents
    date: string,             // YYYY-MM-DD
  }>
}
```

A **Credit Note** object has:
```javascript
{
  number: string,             // e.g., "CN-2026-0001"
  invoiceNumber: string,      // reference to original invoice
  customerId: string,         // normalized
  amount: number,             // cents
  reason: string,             // why credit was issued
  date: string,               // YYYY-MM-DD, used for numbering
}
```

### Module: `src/invoices.js`

**`createInvoice({ customerId, issueDate, lines, terms })`**
- Creates a draft invoice
- `terms` defaults to 'NET30', can be 'NET14', 'NET30', or 'EOM'
- Calculates `dueDate` based on terms
- Normalizes customerId before storage
- Applies tier discounts to lines without explicit discountPercent
- Validates: customer exists, date valid YYYY-MM-DD, lines non-empty, qty positive integers, SKUs exist, discountPercent valid, terms valid
- Error codes: CUSTOMER_NOT_FOUND, DATE_INVALID, NO_LINES, QTY_INVALID, UNKNOWN_SKU, DISCOUNT_INVALID, TERMS_INVALID

**`lineTotal(line)`**
- Returns qty × unitPrice in cents

**`lineDiscount(line)`**
- Returns discount amount for a line in cents
- Discount = lineTotal × (discountPercent ?? 0) / 100, rounded and clamped at 0

**`lineVAT(line)`**
- Returns VAT amount for a line in cents
- VAT = (lineTotal - lineDiscount) × vatRate / 100, rounded and clamped at 0

**`invoiceTotals(invoice)`**
- Returns `{ subtotal, discount, vat, voucher, total }` (all in cents)
- subtotal = sum of all line totals
- discount = sum of all line discounts
- vat = sum of all line VATs
- voucher = invoice.voucher?.amount ?? 0
- total = subtotal - discount + vat - voucher, clamped at 0

**`addLine(invoice, { sku, qty, discountPercent })`**
- Adds a new line or increases qty if SKU already present
- Works on draft invoices only
- Does NOT apply tier discount (use explicit discountPercent if needed)
- Preserves terms, dueDate, and voucher
- Validates: qty positive integer, SKU exists, discountPercent valid
- Error codes: QTY_INVALID, UNKNOWN_SKU, NOT_DRAFT, DISCOUNT_INVALID

**`removeLine(invoice, sku)`**
- Removes a line by SKU
- Works on draft invoices only
- Prevents removing the last line
- Preserves terms, dueDate, and voucher
- Error codes: LINE_NOT_FOUND, NO_LINES, NOT_DRAFT

**`issueInvoice(invoice, existingNumbers)`**
- Transitions a draft invoice to issued
- Assigns the next invoice number
- Preserves terms, dueDate, and voucher
- Error codes: NOT_DRAFT

**`applyVoucher(invoice, { code, amount })`**
- Applies a fixed-amount voucher to a draft invoice
- One voucher per invoice (subsequent applications return error)
- Voucher is deducted from total after VAT
- Preserves all other invoice data
- Validates: status is draft, amount is positive integer
- Error codes: NOT_DRAFT, AMOUNT_INVALID, VOUCHER_EXISTS

### Module: `src/payments.js`

**`balanceDue(invoice)`**
- Returns the amount still owed on an invoice
- Calculation: invoiceTotals(invoice).total - sum of payments
- Returns 0 if fully paid

**`recordPayment(invoice, { amount, date })`**
- Records a payment on an issued, partially_paid, or paid invoice
- Creates `payments` array if it doesn't exist
- Updates invoice status:
  - If balance after payment = 0: status = 'paid'
  - If balance after payment > 0: status = 'partially_paid'
- Preserves all invoice fields including vouchers, terms, dueDate
- Validates: status is issued/partially_paid, amount is positive integer, amount doesn't exceed balance due
- Error codes: NOT_ISSUED, AMOUNT_INVALID, OVERPAYMENT
- Returns `ok(newInvoice)` with payment recorded

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

**`lastDayOfMonth(date)`**
- Returns the last day of the month for a given date
- Handles leap years correctly
- Returns YYYY-MM-DD format

**`calculateDueDate(issueDate, terms)`**
- Calculates due date based on payment terms
- NET14: adds 14 days
- NET30: adds 30 days
- EOM: returns last day of the month

### Module: `src/statements.js`

**`statement(customerId, invoices, asOf)`**
- Generates a customer statement showing outstanding invoices
- Filters invoices by: customer ID (normalized), status 'issued' or 'partially_paid', issueDate on or before asOf
- Returns `ok({ customerId, invoices, totalDue })`
- Each invoice in statement includes: `{ number, issueDate, dueDate, total, due }`
- Invoices sorted by issueDate ascending
- totalDue = sum of all `due` amounts
- Validates: customer exists
- Error codes: CUSTOMER_NOT_FOUND

### Module: `src/credits.js`

**`nextCreditNoteNumber(existingNumbers, issueDate)`**
- Generates the next credit note number for a given year
- Format: `CN-<year>-<counter>` with 4-digit zero-padded counter
- Counter restarts at 0001 each year
- Maintains separate counter from invoices
- Handles mixed list of invoice and credit note numbers

**`createCreditNote(invoice, { amount, reason, date }, existingNumbers)`**
- Creates a credit note for an issued, partially_paid, or paid invoice
- Returns `ok(creditNote)` with: `{ number, invoiceNumber, customerId, amount, reason, date }`
- Validates: status not draft, amount is positive integer, amount ≤ invoice total
- Error codes: NOT_ISSUED, AMOUNT_INVALID, CREDIT_TOO_HIGH

### Module: `src/numbering.js`

**`nextInvoiceNumber(existingNumbers, issueDate)`**
- Generates the next invoice number for a given year
- Input: array of existing numbers (in any order), issue date in YYYY-MM-DD format
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

### Module: `src/money.js`

**`roundCents(x)`**
- Half to even (banker's rounding)
- Example: 124.5 → 124, 125.5 → 126

**`formatEuros(cents)`**
- Formats cents as "€1,234.56"

**`parseEuros(text)`**
- Parses "12", "12.5", "1,234.56" into cents

**`RATES`** (constant)
- `{ EUR: 1, USD: 1.085, GBP: 0.8425 }`
- Units of that currency per euro

**`convert(cents, currency)`**
- Converts euro cents to another currency's cents
- Returns `ok(convertedCents)` or `fail('UNKNOWN_CURRENCY')`
- Example: `convert(10000, 'USD')` → `ok(10850)`

**`formatMoney(cents, currency)`**
- Formats amounts in any currency for display
- Uses $ for USD, £ for GBP, € for EUR
- Falls back to currency code for unknown currencies
- Example: `formatMoney(108500, 'USD')` → `$1,085.00`

### Module: `src/reports.js`

**`overdueInvoices(invoices, asOf)`**
- Returns invoices with status 'issued' or 'partially_paid' whose dueDate is before asOf
- Returns `[{ number, customerId, dueDate, daysOverdue, due }]`
- Sorted by most overdue first (oldest dueDate)

**`vatSummary(invoices)`**
- Aggregates VAT by rate over invoices with status 'issued', 'partially_paid', or 'paid'
- Returns `[{ rate, base, vat }]` sorted by rate high-to-low
- base = line amounts after discount, vat = VAT at that rate

**`lateFee(invoice, asOf)`**
- Calculates 0.04% of amount still due for every day overdue
- Returns 0 if invoice is not overdue (dueDate ≥ asOf)
- Uses `balanceDue()` to get remaining amount (respects partial payments)

### Module: `src/export.js`

**`exportCsv(invoices)`**
- Exports invoices to CSV format
- Header: `number,customer,issueDate,dueDate,status,subtotal,discount,vat,total,due`
- Customer name is looked up from customer database
- Amounts formatted as plain euros: `1234.50` (2 decimals, dot, no currency sign, no thousands separator)
- CSV field escaping: fields with comma or quote wrapped in quotes, internal quotes doubled
- Lines end with `\n`
- Draft invoices show empty string for number

### Module: `src/result.js`

**`ok(value)`** and **`fail(error)`**
- Result objects: `{ ok: true, value }` or `{ ok: false, error }`

### Module: `src/errors.js`

Error codes and messages:
- AMOUNT_INVALID: "Amount must be a whole, positive number of cents."
- CREDIT_TOO_HIGH: "Credit note amount cannot exceed the invoice total."
- CUSTOMER_INVALID, CUSTOMER_NOT_FOUND
- DATE_INVALID
- DISCOUNT_INVALID
- LINE_NOT_FOUND, NO_LINES, NOT_DRAFT
- NOT_ISSUED: "Cannot perform this operation on a draft invoice."
- OVERPAYMENT: "Payment amount exceeds the balance due."
- QTY_INVALID
- TERMS_INVALID: "Payment terms must be "NET14", "NET30", or "EOM"."
- UNKNOWN_SKU
- VOUCHER_EXISTS: "An invoice can only have one voucher."

### Test Suites

- **`test/invoices.test.js`** (187 tests): Invoice CRUD, line operations, discounts, VAT, ID normalization, payment terms, vouchers
- **`test/customers.test.js`** (11 tests): Customer lookup, ID normalization
- **`test/numbering.test.js`** (9 tests): Invoice number generation
- **`test/render.test.js`** (9 tests): Text rendering with VAT line
- **`test/money.test.js`** (25 tests): Rounding, formatting, currency conversion and formatting
- **`test/catalogue.test.js`** (4 tests): Product lookup
- **`test/dates.test.js`** (21 tests): Date validation and arithmetic, due date calculation
- **`test/payments.test.js`** (21 tests): Payment recording, balance due, status transitions
- **`test/statements.test.js`** (16 tests): Customer statement generation, filtering, sorting
- **`test/credits.test.js`** (20 tests): Credit note creation, numbering, validation
- **`test/reports.test.js`** (33 tests): Overdue report, VAT summary, late fees
- **`test/export.test.js`** (28 tests): CSV export with proper formatting and escaping

**Total: 321 tests, all passing**

## Known Limitations / Future Work

1. **Invoice modification after issue**: Cannot edit issued invoices (by design). Credit notes allow partial refunds.

2. **Persistence**: No storage layer. Invoices, payments, and credit notes exist only in memory.

3. **PDF/HTML rendering**: Only plain-text and CSV rendering exist. No PDF or HTML output.

4. **Compliance**: No audit trails, versioning, or signature support.

5. **Multi-invoice operations**: No batch processing or bulk payment recording.

6. **Partial credits**: Credit notes are independent refund records but don't automatically affect invoice status or remaining balance (calling code must track).

7. **Currency limitation**: Only 3 currencies supported (EUR, USD, GBP). Adding more requires updating RATES constant and tests.

## Running Tests

```bash
npm test
```

This runs all tests in `test/*.test.js` using Node's built-in test runner. Output shows pass/fail count and duration.

## Key Files Overview

```
src/
  invoices.js       - Invoice CRUD, calculations, vouchers, payment terms
  payments.js       - Payment recording, balance tracking
  statements.js     - Customer statement generation
  credits.js        - Credit note creation and numbering
  numbering.js      - Invoice and credit note number generation
  render.js         - Plain-text rendering
  customers.js      - Customer lookup, ID normalization, tier discounts
  dates.js          - Date validation, arithmetic, due date calculation (UTC)
  errors.js         - Error codes and messages
  result.js         - ok() and fail() helpers
  money.js          - roundCents(), formatEuros(), parseEuros(), currency conversion and formatting
  catalogue.js      - Product lookup
  reports.js        - Overdue invoices, VAT summary, late fees
  export.js         - CSV export

test/
  invoices.test.js      - 187 tests (CRUD, calculations, discounts, VAT, ID normalization, terms, vouchers)
  payments.test.js      - 21 tests (payment recording, balance calculations, status transitions)
  statements.test.js    - 16 tests (statement generation, filtering, sorting)
  credits.test.js       - 20 tests (credit note creation, numbering, validation)
  customers.test.js     - 11 tests (lookup, normalization)
  numbering.test.js     - 9 tests (number generation)
  render.test.js        - 9 tests (text rendering with VAT)
  money.test.js         - 25 tests (rounding, formatting, currency conversion)
  catalogue.test.js     - 4 tests (product lookup)
  dates.test.js         - 21 tests (date validation and arithmetic)
  reports.test.js       - 33 tests (overdue invoices, VAT summary, late fees)
  export.test.js        - 28 tests (CSV export with formatting and escaping)

data/
  customers.json    - Customer records (id, name, email, country, tier)
  catalogue.json    - Product catalogue (sku, name, unitPrice, vatRate)

HANDOFF.md          - This file
package.json        - npm configuration
```

## Next Steps Guidance

When continuing this work:

1. **Before any changes**: Run `npm test` to establish baseline (expect 321 passing tests)
2. **When adding features**: Follow existing patterns (result objects, error codes, immutability, UTC dates, cents for money)
3. **When touching money**: Always use cents (integers) and `roundCents()` for calculations
4. **When handling dates**: Use utilities from `src/dates.js`, work in UTC
5. **When handling customer IDs**: Always normalize with `normalizeId()`
6. **When rendering money**: Use `formatEuros()` for EUR or `formatMoney(cents, currency)` for multi-currency display
7. **When converting currency**: Use `convert(cents, currency)` which returns a result object
8. **When done**: Add tests and ensure `npm test` passes

## Completed Features

This session added:
- **Overdue report**: `overdueInvoices(invoices, asOf)` - identify and list overdue invoices with days overdue and amount due
- **VAT summary**: `vatSummary(invoices)` - aggregate VAT by rate across all invoices
- **Late fees**: `lateFee(invoice, asOf)` - calculate 0.04% per-day late fees on overdue amounts
- **CSV export**: `exportCsv(invoices)` - export invoices in standard CSV format with proper escaping
- **Foreign currency support**: `RATES`, `convert()`, `formatMoney()` - support USD and GBP with conversion and formatting

## Likely Future Tasks

- Persisting invoices and transactions (loading/saving to database or file)
- Recurring invoices or subscription billing
- Invoice amendments (partial modification after issue)
- PDF or HTML rendering
- Email delivery of invoices and statements
- Additional tax calculations beyond VAT
- Enhanced reporting and analytics
- Automated payment reminders
- Invoice templates
- Webhooks or event notifications
