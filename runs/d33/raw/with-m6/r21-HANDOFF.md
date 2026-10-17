# Invoicekit - Handoff

## Project Goal
Build a complete invoicing system for the invoicekit project. The system manages invoice creation, modification, issuance, rendering, payment tracking, and refunds with support for customer tiers, line discounts, VAT calculations, payment terms, vouchers, credit notes, customer statements, and proper date/ID handling.

## House Rules (Apply to All Future Work)

1. **Money as Integer Cents**: All monetary amounts are integers representing cents. Never store or return fractional cents. When calculations produce fractions, round using `roundCents()` from `src/money.js`.

2. **Error Handling**: Never throw errors for invalid input. Instead, return `fail(CODE)` from `src/result.js`. Add every new error code to the `ERRORS` object in `src/errors.js` with a one-line message.

3. **Immutability**: Never mutate function arguments. Always return new objects and arrays.

4. **Testing**: Run `npm test` before marking any task complete. Currently 226 tests pass.

5. **No Negative Amounts**: No amount we compute, on a line, an invoice, or anything we add later, may ever go below zero. Clamp at 0.

6. **Dates in UTC**: All dates are 'YYYY-MM-DD' strings everywhere. All date arithmetic is done in UTC, never in machine's local time zone. Use functions from `src/dates.js`.

7. **Customer IDs Normalized**: Always normalize customer IDs with `normalizeId()` from `src/customers.js` before comparing or storing them. Trim whitespace and uppercase.

## Key Decisions

1. **Invoice Numbering Format**: `INV-<year>-<counter>`
   - Year is extracted from the invoice's `issueDate`
   - Counter has 4 digits, zero-padded (0001, 0002, ..., 9999, 10000, ...)
   - Counter resets to 0001 at the start of each year
   - Example: `INV-2026-0001`

2. **Customer-Facing Amounts**: All monetary amounts displayed to customers must be formatted using `formatEuros()` (EUR only) or `formatMoney()` (any currency) from `src/money.js`. This ensures consistent formatting with symbol and two decimal places (e.g., `€1,234.56`, `$1,234.56`, `£1,234.56`).

3. **Line Discounts**: Lines can carry `discountPercent` (0-100, can have decimals like 12.5). Validation returns `DISCOUNT_INVALID` if invalid. Line discount = line total × discountPercent / 100, rounded per line.

4. **Customer Tier Discounts**: Every customer has a tier (gold, silver, standard). When a line has no explicit `discountPercent`, it gets the customer's tier discount:
   - Gold: 5%
   - Silver: 2.5%
   - Standard: 0%
   - Explicit discountPercent (even 0) always overrides tier discount.

5. **VAT Calculation**: VAT is computed per line on the line's amount after its discount, then rounded per line. Invoice VAT is the sum of rounded line VATs, never a percentage of invoice total. Formula: `(line_total - line_discount) * vatRate / 100`.

6. **Invoice Totals Structure**: Returns `{ subtotal, discount, vat, voucher, total }` where:
   - `subtotal` = sum of all line totals
   - `discount` = sum of all line discounts
   - `vat` = sum of all line VATs
   - `voucher` = voucher amount (0 if no voucher)
   - `total` = subtotal - discount + vat - voucher (clamped at 0)

7. **Payment Terms**: Invoices support three payment term types:
   - `NET14`: Due 14 days after issue date
   - `NET30`: Due 30 days after issue date (default)
   - `EOM`: Due on last day of the month of issue date
   - Each invoice has `terms` and `dueDate` fields set at creation

8. **Vouchers**: Invoices can have at most one voucher applied (only when draft). Vouchers:
   - Take a fixed amount in cents off the invoice
   - Applied after VAT calculation
   - Included in `invoiceTotals` calculation

9. **Credit Note Numbering Format**: `CN-<year>-<counter>` (similar to invoices but with CN prefix)
   - Year is extracted from the credit note's `date`
   - Counter has 4 digits, zero-padded (0001, 0002, ..., 9999, 10000, ...)
   - Counter resets to 0001 at the start of each year
   - Separate counter from invoices; both types can coexist in existingNumbers
   - Example: `CN-2026-0001`

10. **Payment Status**: Invoices track payments and update status:
    - `draft`: Initial status, can be modified
    - `issued`: After issuance, can receive payments
    - `partially_paid`: Has received some payments but not full amount
    - `paid`: All payments received equal invoice total

11. **Foreign Currency Support**: System supports EUR (base), USD, and GBP with fixed exchange rates:
    - EUR: 1.0 (base currency, all amounts stored in EUR cents)
    - USD: 1.085 units per euro
    - GBP: 0.8425 units per euro
    - Use `convert(cents, currency)` to convert EUR to other currencies
    - Use `formatMoney(cents, currency)` to format in any supported currency
    - All calculations use `roundCents()` for precision

12. **Late Fees**: Invoices can accrue late fees at 0.04% per day for each day overdue:
    - Only calculated on balance due (remaining unpaid amount)
    - Zero fee if invoice is not overdue
    - Use `lateFee(invoice, asOf)` to calculate fee for a given date

## What Has Been Built

### Core Modules

**src/invoices.js** - Main invoice operations
- `createInvoice({ customerId, issueDate, lines, terms })` → Creates a draft invoice with validated and normalized customer, date, and line items. Accepts optional terms ('NET14', 'NET30' default, 'EOM'). Sets invoice.terms and invoice.dueDate.
- `lineTotal(line)` → Calculates `qty × unitPrice` in cents
- `lineDiscount(line)` → Calculates line discount as `(lineTotal × discountPercent) / 100`, clamped at 0
- `lineVAT(line)` → Calculates VAT on line after discount as `((lineTotal - lineDiscount) × vatRate) / 100`, clamped at 0
- `invoiceTotals(invoice)` → Returns `{ subtotal, discount, vat, voucher, total }` where total = subtotal - discount + vat - voucher (clamped at 0)
- `addLine(invoice, { sku, qty, discountPercent })` → Adds new line or increases qty of existing line. Applies tier discount if no explicit discountPercent. Can update discountPercent on existing lines.
- `removeLine(invoice, sku)` → Removes line; rejects if it's the last line
- `issueInvoice(invoice, existingNumbers)` → Assigns invoice number and changes status to 'issued'
- `applyVoucher(invoice, { code, amount })` → Applies a voucher to a draft invoice (fixed amount in cents, after VAT). One voucher per invoice.

**src/payments.js** - Payment tracking for issued invoices
- `recordPayment(invoice, { amount, date })` → Records a payment on an issued or partially_paid invoice. Updates status to 'partially_paid' or 'paid' based on total paid. Creates invoice.payments array if missing.
- `balanceDue(invoice)` → Calculates the amount still owed on an invoice (total - sum of payments).

**src/statements.js** - Customer statements
- `statement(customerId, invoices, asOf)` → Generates a customer statement showing all due invoices (status 'issued' or 'partially_paid' with issueDate <= asOf), sorted by issueDate. Returns { customerId, invoices[], totalDue } where each invoice has { number, issueDate, dueDate, total, due }.

**src/credits.js** - Credit notes for refunds
- `nextCreditNoteNumber(existingNumbers, date)` → Generates next credit note number in format CN-YYYY-NNNN with separate counter from invoices.
- `createCreditNote(invoice, { amount, reason, date }, existingNumbers)` → Creates a credit note for an issued/partially_paid/paid invoice. Returns { number, invoiceNumber, customerId, amount, reason, date }.

**src/customers.js** - Customer management
- `listCustomers()` → Returns list of all customers
- `getCustomer(id)` → Finds customer by ID (ID is normalized before lookup)
- `validateCustomer(c)` → Validates customer record has required fields
- `normalizeId(id)` → Trims and uppercases customer ID
- `TIER_DISCOUNTS` → Object with discount percentages: `{ gold: 5, silver: 2.5, standard: 0 }`

**src/dates.js** - Date utilities (all operations in UTC)
- `isValidDate(text)` → Validates YYYY-MM-DD format and that it's a valid calendar date
- `addDays(date, n)` → Adds n days to a date (can be negative), returns YYYY-MM-DD
- `daysBetween(a, b)` → Calculates b minus a in whole days

**src/numbering.js** - Invoice numbering
- `nextInvoiceNumber(existingNumbers, issueDate)` → Generates next available invoice number for the given year (format: INV-YYYY-NNNN)

**src/render.js** - Invoice rendering
- `renderInvoiceText(invoice)` → Returns plain-text invoice with: number/DRAFT, customer name, line items with quantities and prices, subtotal, discount (if non-zero), VAT, and total

**src/reports.js** - Reporting and analysis
- `overdueInvoices(invoices, asOf)` → Filters invoices with status 'issued' or 'partially_paid' whose dueDate is before asOf. Returns array sorted by daysOverdue descending with fields: { number, customerId, dueDate, daysOverdue, due }
- `vatSummary(invoices)` → Aggregates VAT from invoices with status 'issued', 'partially_paid', or 'paid'. Returns array of { rate, base, vat } (base = line totals after discounts), sorted by rate descending.
- `lateFee(invoice, asOf)` → Calculates late fee at 0.04% per day on balance due for days overdue. Returns 0 if not overdue.

**src/export.js** - CSV export
- `exportCsv(invoices)` → Exports invoices as CSV string with header: number,customer,issueDate,dueDate,status,subtotal,discount,vat,total,due. Customer field contains customer name, amounts in euros with 2 decimals and dot (no symbol/thousands separator), proper CSV escaping. Lines end with \n.

**src/money.js** - Money utilities
- `roundCents(amount)` → Rounds monetary amounts using banker's rounding
- `formatEuros(cents)` → Formats cents as €X,XXX.XX
- `parseEuros(text)` → Parses user-entered amounts like "12", "12.5", "1,234.56" into cents
- `RATES` → Exchange rates object: { EUR: 1, USD: 1.085, GBP: 0.8425 } (units of currency per euro)
- `convert(cents, currency)` → Converts EUR cents to another currency's cents. Returns ok(amount) or fail('UNKNOWN_CURRENCY').
- `formatMoney(cents, currency)` → Formats cents in specified currency with symbol: € (EUR), $ (USD), £ (GBP). Format: symbol + amount with thousands separators and 2 decimals.

**src/catalogue.js** - Product lookup (existing)
- `getProduct(sku)` → Finds product by SKU, returns with name, unitPrice, vatRate

**src/result.js** - Result wrapper types (existing)
- `ok(value)` → Success result
- `fail(code)` → Failure result

### Error Codes (in src/errors.js)

- `AMOUNT_INVALID` - Amount must be a whole, positive number of cents
- `CREDIT_TOO_HIGH` - Credit note amount cannot exceed the invoice total
- `CUSTOMER_INVALID` - Customer needs an id, a name and a valid email
- `CUSTOMER_NOT_FOUND` - No customer with that id
- `DATE_INVALID` - Date must be in YYYY-MM-DD format and a valid calendar date
- `DISCOUNT_INVALID` - Discount percent must be a number between 0 and 100
- `LINE_NOT_FOUND` - No line with that SKU on the invoice
- `NOT_DRAFT` - Can only modify invoices with status "draft"
- `NOT_ISSUED` - Invoice must be issued or partially paid to record a payment
- `NO_LINES` - An invoice must have at least one line item
- `OVERPAYMENT` - Payment amount exceeds amount still owed
- `QTY_INVALID` - Quantity must be a positive integer
- `TERMS_INVALID` - Terms must be NET14, NET30, or EOM
- `UNKNOWN_CURRENCY` - Currency must be EUR, USD, or GBP
- `UNKNOWN_SKU` - No product with that SKU in the catalogue
- `VOUCHER_EXISTS` - An invoice can only have one voucher

### Invoice Data Structure

```javascript
{
  customerId: string,                    // e.g., 'C-001' (normalized: uppercase, no leading/trailing spaces)
  issueDate: string,                     // YYYY-MM-DD format (UTC, valid calendar date)
  status: 'draft' | 'issued' | 'partially_paid' | 'paid',  // Status based on payments
  number?: string,                       // e.g., 'INV-2026-0001' (absent for draft)
  terms: string,                         // 'NET14', 'NET30' (default), or 'EOM'
  dueDate: string,                       // YYYY-MM-DD format, calculated from terms
  lines: [
    {
      sku: string,                       // Product SKU
      name: string,                      // Product name (from catalogue)
      qty: number,                       // Positive integer
      unitPrice: number,                 // Cents (from catalogue)
      vatRate: number,                   // Percent (from catalogue): 0, 9, or 21
      discountPercent: number            // 0-100 (can have decimals like 12.5). If not explicit, set to customer tier discount
    }
  ],
  voucher?: {                            // Optional voucher (draft only)
    code: string,                        // Voucher code
    amount: number                       // Amount in cents
  },
  payments?: [                           // Optional payments array
    {
      amount: number,                    // Amount in cents
      date: string                       // YYYY-MM-DD format
    }
  ]
}
```

### Test Coverage

- **test/invoices.test.js** - 184 tests for invoice creation, manipulation, issuance, discounts, VAT, payment terms, vouchers, and ID normalization
- **test/payments.test.js** - 18 tests for payment recording, balance tracking, and status transitions
- **test/statements.test.js** - 19 tests for customer statements with filtering, sorting, and aggregation
- **test/credits.test.js** - 23 tests for credit note creation and numbering
- **test/numbering.test.js** - 8 tests for invoice number generation
- **test/render.test.js** - 13 tests for invoice text rendering with VAT and discounts
- **test/dates.test.js** - 21 tests for date utilities and UTC operations
- **test/reports.test.js** - 49 tests for overdue invoices, VAT summaries, and late fees
- **test/export.test.js** - 30 tests for CSV export with proper formatting and escaping
- **test/money.test.js** - 39 tests for currency conversion, formatting, and money utilities (includes original 4 tests)
- **Total**: 342 passing tests

Run tests: `npm test`

## What's Unfinished

1. **Additional Rendering Formats**: Only plain-text rendering exists. HTML and PDF rendering can be added to `src/render.js`.

2. **Invoice Persistence**: No database or file storage for invoices—they exist only in memory during a request. Need to add database layer.

3. **Invoice Retrieval**: No functions to fetch existing invoices by ID or search invoices.

4. **Invoice Status Transitions**: 'cancelled' and 'refunded' statuses not yet implemented. May require additional logic for reversing payments/credits.

5. **Credit Note Integration**: Credit notes are created but not yet linked back to invoices or integrated with payment calculations. May want to reduce invoice.due by credit note amounts.

6. **Notifications**: No email or notification system for invoice creation, payment, or credit note issuance.

7. **Audit Logging**: No audit trail of invoice modifications, payments, or credit notes.

8. **Tax Exemption**: No support for tax-exempt customers or line items.

9. **Partial Credit Notes**: All credit notes use exact amounts. May want to support partial refunds with pro-rata VAT calculations.

10. **Additional Currencies**: Only EUR, USD, and GBP supported with fixed rates. Could add more currencies or dynamic rate fetching.

11. **Multi-currency Invoicing**: Currently all invoices in EUR internally. Could allow customers to be invoiced in their preferred currency with automatic conversion.

12. **Advanced Reporting**: Could add invoice aging reports, revenue by customer, payment tracking over time, etc.

13. **Late Fee Configuration**: Late fee is hardcoded at 0.04% per day. Could make this configurable per invoice or customer.

## How to Continue

### Running Tests
```bash
npm test
```
All tests should pass. There are currently 342 tests covering invoices, payments, statements, credit notes, numbering, rendering, dates, reporting, CSV export, and currency operations.

### File Organization
- **src/** - Source code
  - `invoices.js` - Main invoice operations (create, add lines, remove lines, issue, apply voucher, totals)
  - `payments.js` - Payment tracking and balance calculations
  - `statements.js` - Customer statement generation
  - `credits.js` - Credit note creation and numbering
  - `customers.js` - Customer lookup and normalization
  - `catalogue.js` - Product lookup (existing)
  - `numbering.js` - Invoice numbering logic
  - `dates.js` - Date utilities (validation, arithmetic, all UTC)
  - `render.js` - Invoice rendering (plain-text; HTML/PDF can be added here)
  - `reports.js` - Reporting: overdue invoices, VAT summaries, late fees
  - `export.js` - CSV export with proper formatting and escaping
  - `money.js` - Money utilities: formatting, parsing, currency conversion, exchange rates
  - `result.js` - Result wrapper types (ok/fail)
  - `errors.js` - Error codes (update here for new errors)
- **test/** - Test files (mirror src/ structure)
- **data/** - Data files (customers.json with tiers, catalogue.json with products)

### Common Implementation Patterns

1. **Invoice Creation**:
   - Normalize customer ID with `normalizeId()`
   - Validate date with `isValidDate()`
   - Apply tier discounts to lines without explicit `discountPercent`
   - Never mutate input, return new object

2. **Monetary Calculations**:
   - Always work in cents (integers)
   - Round intermediate results with `roundCents()`
   - Clamp final amounts at 0
   - Never display fractional cents

3. **Error Handling**:
   - Use `fail(CODE)` for validation errors
   - Add new codes to `src/errors.js` with one-line messages
   - Never throw exceptions for invalid input

4. **Customer Management**:
   - Always normalize IDs before lookup or storage
   - Use `getCustomer()` to validate customer exists
   - Check customer tier for discount (if applicable)

5. **Date Operations**:
   - Always validate dates with `isValidDate()`
   - Use `addDays()` for date arithmetic
   - Use `daysBetween()` for duration calculations
   - All operations are UTC; never use local timezone

6. **Payment Processing**:
   - Only issue, partially_paid, and paid invoices can receive payments
   - Payments are stored in invoice.payments array
   - Always use `balanceDue()` to calculate amount owed
   - Status automatically updates: 'partially_paid' if partial, 'paid' if complete
   - Never mutate invoice when recording payment, return new invoice

7. **Voucher Application**:
   - Only draft invoices can have vouchers applied
   - Maximum one voucher per invoice
   - Voucher amount must be positive integer and not exceed invoice total
   - Voucher reduces invoice total (after VAT, before payment)
   - Include voucher in invoiceTotals calculations

8. **Credit Note Generation**:
   - Credit notes work with issued, partially_paid, and paid invoices
   - Credit note amount cannot exceed invoice total
   - Credit notes have separate numbering from invoices (CN vs INV prefix)
   - Use `nextCreditNoteNumber()` passing all existing numbers (both types)
   - Credit note date determines year for numbering, not invoice date

9. **Customer Statements**:
   - Filter invoices by customer (normalized ID), status (issued/partially_paid), and date (<=asOf)
   - Sort by issueDate ascending
   - Calculate due using `balanceDue()` for each invoice
   - Sum all due amounts for totalDue
   - Return only invoices with status issued or partially_paid (exclude draft and paid)

10. **Reporting Functions**:
   - Overdue invoices: filter by status (issued/partially_paid), dueDate < asOf, calculate daysOverdue using `daysBetween()`, sort descending
   - VAT summary: filter by status (issued/partially_paid/paid), aggregate base (lineTotal - lineDiscount) and VAT by rate, sort rates descending
   - Late fees: only calculate on balance due, 0.04% per day overdue, use `roundCents()` for precision

11. **CSV Export**:
   - Escape fields with comma/quote/newline by wrapping in quotes and doubling internal quotes
   - Amount fields: use euros with 2 decimals and dot, no symbol or thousands separator (e.g., "1234.50")
   - Customer field: lookup customer name from customer ID
   - Ensure trailing newline on output

12. **Currency Conversion**:
   - All amounts stored internally as EUR cents
   - Use `convert(eurocents, currency)` to convert to other currencies
   - Always use `roundCents()` on converted amounts for precision
   - Use `formatMoney(cents, currency)` to format any currency with symbol

### Example: Adding a New Feature

If asked to add invoice comments/notes:
1. Add `comment?: string` field to invoice data structure
2. Update `createInvoice()` to accept and validate comment
3. Update `addLine()` signature if needed (or create separate function)
4. Update `renderInvoiceText()` to display comment if present
5. Add comprehensive tests for comment validation, storage, and rendering
6. Run `npm test` to verify all 226+ tests still pass

### Testing Requirements
- Every new public function needs tests
- Test both happy path and error cases
- Test edge cases (empty inputs, boundary values, year/month transitions for dates)
- Test immutability (verify inputs aren't mutated)
- Test with different customer tiers and VAT rates
- Test amounts are clamped at 0
- Update test expectations when behavior changes
