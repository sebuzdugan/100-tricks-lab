# Invoicekit: Handoff

## Project Goal

Build a complete invoicing system for a service business. The system manages creating, editing, issuing, and rendering invoices with proper numbering and formatting. Includes payments, statements, credit notes, reporting, CSV export, and multi-currency support.

## House Rules (Apply to All Requests)

1. **Money is always an integer number of cents.** Never store or return fractional amounts. When a calculation produces fractional cents, round using `roundCents()` from `src/money.js`.

2. **Never throw for bad input.** Return `fail(CODE)` from `src/result.js` instead. Add every new error code to `ERRORS` in `src/errors.js` with a one-line message.

3. **Never mutate an argument.** Return new objects and arrays instead.

4. **Run `npm test` before you say a request is done.**

5. **All amounts shown to customers use `formatEuros()` or `formatMoney()`** from `src/money.js`. This applies to anything rendered for customer display.

6. **No amount may ever go below zero; clamp at 0.** This applies to line discounts, invoice discounts, totals, VAT, and any other computed amount.

7. **Dates are always YYYY-MM-DD strings and all date arithmetic uses UTC, never local time.** Use `isValidDate()`, `addDays()`, and `daysBetween()` from `src/dates.js`.

8. **Customer IDs are always normalized (trimmed and uppercased) before comparison or storage.** Use `normalizeId()` from `src/customers.js`.

## Key Decisions Made

- **Invoice numbering format:** `INV-<year>-<counter>` where counter is 4 digits, zero-padded, starting at 0001 and restarting every year.
- **Invoice statuses:** `draft` (editable), `issued` (numbered and locked), `partially_paid` (has payments but balance remains), `paid` (all balance paid). Only draft invoices can be modified (no edits after issuing).
- **Error handling:** Uses result-style `{ ok: boolean, value?, error?, details? }` pattern. Never throws exceptions for validation errors.
- **Customer-facing output:** All monetary amounts must go through `formatEuros()` or `formatMoney()` for consistency.
- **Line discounts:** Per-line `discountPercent` (0–100, can have decimals). Line discount = `lineTotal × discountPercent / 100`, rounded per line.
- **Tier-based discounts:** Gold 5%, Silver 2.5%, Standard 0%. Applied automatically when a line has no explicit `discountPercent`.
- **VAT calculation:** VAT is computed per line on the line amount **after discount is applied** (i.e., `(lineTotal - lineDiscount) × vatRate / 100`). Each line's VAT is rounded independently. Invoice VAT is the sum of rounded line VATs.
- **Invoice totals formula:** `total = subtotal - discount + vat - voucher` (where all components are clamped at 0). Vouchers apply after VAT and are optional.
- **Rendering:** VAT is shown on its own line (when > 0) just above the total in plain-text output.
- **Currency support:** Three currencies supported: EUR (€, base), USD ($, 1.085 per EUR), GBP (£, 0.8425 per EUR). All amounts stored in EUR cents internally; conversion uses banker's rounding.
- **Late fees:** 0.04% of outstanding balance per day overdue. Applied to issued and partially_paid invoices based on daysOverdue from dueDate to asOf.

## What Has Been Built

### Core Files

| File | Purpose |
|------|---------|
| `src/money.js` | Money formatting, parsing, and currency conversion (`roundCents`, `formatEuros`, `parseEuros`, `RATES`, `convert`, `formatMoney`) |
| `src/result.js` | Result pattern for error handling (`ok()`, `fail()`) |
| `src/errors.js` | All error codes and messages |
| `src/catalogue.js` | Product catalogue (`getProduct()`, `listProducts()`) |
| `src/customers.js` | Customer database with ID normalization and tier discounts |
| `src/invoices.js` | Core invoicing: create, edit, issue, calculate totals with discount and VAT |
| `src/numbering.js` | Invoice number generation with year-based counter |
| `src/render.js` | Plain-text invoice rendering with VAT display |
| `src/dates.js` | UTC-based date utilities (`isValidDate`, `addDays`, `daysBetween`) |
| `src/payments.js` | Payment tracking and balance calculation (`recordPayment`, `balanceDue`) |
| `src/statements.js` | Customer account statements showing outstanding invoices |
| `src/credits.js` | Credit notes for refunds on issued invoices |
| `src/reports.js` | **NEW** Reporting functions (`overdueInvoices`, `vatSummary`, `lateFee`) |
| `src/export.js` | **NEW** CSV export (`exportCsv`) |

### Implemented Functions

#### `src/money.js`
- `RATES` — Exchange rates constant: `{ EUR: 1, USD: 1.085, GBP: 0.8425 }`

- `roundCents(x)` — Round fractional cents using banker's rounding (half-to-even)

- `formatEuros(cents)` — Format as euros with thousands separator: `€1,234.56`

- `parseEuros(text)` — Parse euro amounts from user input: `"12.5"` → `1250` cents

- `convert(cents, currency)` — Convert from EUR cents to another currency
  - Returns `ok(convertedCents)` or `fail('UNKNOWN_CURRENCY')`
  - Uses RATES and banker's rounding
  - Example: `convert(10000, 'USD')` → `ok(10850)` (€100 = $108.50)

- `formatMoney(cents, currency)` — Format amount in target currency with symbol
  - Returns `ok(formattedString)` or `fail('UNKNOWN_CURRENCY')`
  - Formats with 2 decimals: `$100.50`, `€100.00`, `£84.25`
  - Uses `convert()` internally

#### `src/invoices.js`
- `createInvoice({ customerId, issueDate, lines, terms? })` — Create a draft invoice
- `lineTotal(line)` — Calculate base total for a line (qty × unitPrice, rounded)
- `lineDiscount(line)` — Calculate discount amount for a line
- `lineVAT(line)` — Calculate VAT for a line (applied to discounted amount)
- `invoiceTotals(invoice)` — Returns `{ subtotal, discount, vat, voucher, total }`
- `addLine(invoice, { sku, qty, discountPercent? })` — Add or increase a line
- `removeLine(invoice, sku)` — Remove a line
- `issueInvoice(invoice, existingNumbers)` — Change status to issued
- `applyVoucher(invoice, { code, amount })` — Apply fixed-amount voucher

#### `src/dates.js`
- `isValidDate(text)` — Validate YYYY-MM-DD format and real dates in UTC
- `addDays(dateStr, n)` — Add n days to a date, handling month/year boundaries
- `daysBetween(a, b)` — Calculate whole days between two dates (b - a)

#### `src/payments.js`
- `recordPayment(invoice, { amount, date })` — Record payment and update status
  - Status → `partially_paid` (partial) or `paid` (full)
  - Returns new invoice with payment in `payments` array
  
- `balanceDue(invoice)` — Calculate amount still owed
  - Formula: `invoiceTotals(invoice).total - sum(payments)`

#### `src/statements.js`
- `statement(customerId, invoices, asOf)` — Generate customer account statement
  - Filters for matching customer (normalized), issued/partially_paid status, and issueDate ≤ asOf
  - Returns `{ customerId, invoices: [...], totalDue }`
  - Each invoice: `{ number, issueDate, dueDate, total, due }`

#### `src/credits.js`
- `createCreditNote(invoice, { amount, reason, date }, existingNumbers)` — Issue credit note
  - For issued, partially_paid, or paid invoices only
  - Returns `{ number, invoiceNumber, customerId, amount, reason, date }`
  - Number format: `CN-<year>-<counter>`

#### `src/reports.js` (NEW)
- `overdueInvoices(invoices, asOf)` — Find overdue invoices as of a date
  - Filters for status `issued` or `partially_paid` with dueDate < asOf
  - Returns `ok([{ number, customerId, dueDate, daysOverdue, due }])`
  - Sorted by daysOverdue descending (most overdue first)

- `vatSummary(invoices)` — Summarize VAT by rate across invoices
  - Filters for status `issued`, `partially_paid`, or `paid`
  - Groups by VAT rate, accumulating base and vat amounts
  - Returns `ok([{ rate, base, vat }])`
  - Sorted by rate descending (high to low: 21%, 9%, 0%)

- `lateFee(invoice, asOf)` — Calculate late fee for an invoice
  - Formula: `due × 0.0004 × daysOverdue` (0.04% per day)
  - Returns `ok(feeInCents)` or `fail('DATE_INVALID')`
  - Returns 0 if not overdue or fully paid

#### `src/export.js` (NEW)
- `exportCsv(invoices)` — Export invoices as CSV
  - Header: `number,customer,issueDate,dueDate,status,subtotal,discount,vat,total,due`
  - Amounts: Plain euros with 2 decimals and dot (1234.50)
  - Proper CSV escaping (quotes, commas within fields)
  - Customer field shows customer name (via getCustomer lookup)
  - Draft invoices show "DRAFT" as number
  - Returns `ok(csvString)` with lines ending in `\n`

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
| `UNKNOWN_CURRENCY` | Currency code not recognized. Use EUR, USD, or GBP. |

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
| `test/reports.test.js` | 26 | overdueInvoices (14 tests), vatSummary (12 tests) |
| `test/export.test.js` | 21 | exportCsv (headers, fields, escaping, formatting, order) |
| `test/money-currency.test.js` | 30 | convert (validation, rates, rounding), formatMoney (symbols, formatting, edge cases) |
| **Total** | **311** | All functionality including reports, export, and multi-currency |

**Total test suite:** 311 passing tests

## Unfinished Work

The following features have not been implemented but are likely needed:

- **Persistence** — No database or file storage (all in-memory); all data must be passed as parameters
- **Invoice state transitions** — Only draft → issued → (partially_paid / paid); no cancelled, refunded, or voided states
- **PDF rendering** — Only plain text rendering exists; no PDF generation
- **Remittance advice** — No support for payment instructions or bank details
- **Credit note application** — Credit notes are created but not automatically applied to reduce invoice balance
- **Late fee application** — Late fees are calculated but not automatically applied or charged
- **Email delivery** — No email integration for sending invoices, credit notes, or statements
- **Line amendments** — No ability to change qty or discount on existing issued lines
- **Invoice search/filtering** — No built-in search or filtering API beyond statement by customer
- **Batch operations** — No bulk payment recording or mass updates

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
2. **Verify setup:** Run `npm test` to confirm all 311 tests pass
3. **Understand patterns:** Read key files (`src/invoices.js`, `src/payments.js`, `src/reports.js`) to see how the system works
4. **Review tests:** Look at test files to understand testing patterns and edge cases
5. **Plan new work:** Identify what feature to build next, write tests first, then implement
6. **Follow house rules:** 
   - All money as cents (integers only)
   - All errors via `fail()`, never throw
   - Never mutate arguments (return new objects)
   - Dates always YYYY-MM-DD in UTC
   - No amounts below zero (clamp at 0)
   - Customer IDs normalized everywhere
   - Use `convert()` and `formatMoney()` for multi-currency amounts
7. **Add new error codes:** Update `src/errors.js` with any new error codes
8. **Run tests:** Always run `npm test` before considering work complete
9. **Update HANDOFF.md:** Document any new rules, decisions, or architectural changes

## Key Implementation Notes

- **Discount calculation happens per-line:** Each line's discount is computed from its own total, not the invoice subtotal. This allows different discount percentages on different lines.

- **Tier discounts are automatic:** When `createInvoice()` or `addLine()` is called without an explicit `discountPercent`, the customer's tier discount is applied. Standard tier (0%) does not set `discountPercent` on the line (cleaner JSON).

- **VAT uses the discounted amount:** This is critical for correct tax calculation. VAT = `(lineTotal - lineDiscount) × vatRate / 100`. This affects all math involving VAT.

- **Customer IDs are normalized everywhere:** Both `getCustomer()` and `createInvoice()` normalize the ID. The invoice stores the normalized ID. This prevents issues like `'c-001'`, `'C-001'`, and `' c-001 '` being treated as different customers.

- **All date math is in UTC:** The `dates.js` module never uses local time. This is critical for cross-timezone consistency.

- **Rendering includes VAT line:** When `renderInvoiceText()` is called, it shows "VAT: €XXX.XX" just above the total (only if VAT > 0). This is required for EU invoices.

- **Payment terms determine due dates:** Terms default to NET30 (30 days from issue). NET14 is 14 days from issue. EOM is the last day of the issue month, regardless of when in the month the invoice is issued.

- **Vouchers are applied after VAT:** A voucher is a fixed-amount deduction (in cents) applied to the invoice total AFTER VAT calculation. Only one voucher per invoice, and only drafts can have vouchers applied.

- **Credit notes track refunds:** Credit notes are issued against invoices that have been issued, partially paid, or paid (no credit notes on drafts). Each credit note has its own number sequence (CN-YYYY-NNNN) separate from invoice numbers.

- **Currency conversion uses banker's rounding:** When converting between currencies, fractional cents are rounded using banker's rounding (round half to even). Example: 108.5 cents → 108 cents (even), 109.5 cents → 110 cents (even).

- **Late fees scale linearly with days overdue:** Formula is `due × 0.0004 × daysOverdue`, applied daily. Returns 0 if invoice is not overdue or fully paid.

- **Overdue invoices exclude future and paid:** `overdueInvoices()` only includes invoices with `dueDate < asOf` and status `issued` or `partially_paid`. Draft and paid invoices are filtered out.

- **VAT summary groups all invoices:** `vatSummary()` operates across all invoices (issued/partially_paid/paid), summing base amounts and VAT by rate. Useful for tax reporting and reconciliation.

- **CSV export handles special characters:** `exportCsv()` properly escapes commas and quotes in customer names. Fields containing commas or quotes are wrapped in double quotes, and internal quotes are doubled. Lines end with `\n`.

## Data Files

The system loads from JSON files in `/data/`:

- `customers.json` — Customer list (id, name, email, country, tier: "gold" | "silver" | "standard")
- `catalogue.json` — Product catalogue (sku, name, unitPrice in cents, vatRate in percent: 0, 9, or 21)

These are pre-existing, read-only within the codebase, and always accessed via the catalogue/customers modules (not directly).
