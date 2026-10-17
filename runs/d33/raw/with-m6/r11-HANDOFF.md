# Invoicekit - Handoff

## Project Goal
Build a complete invoicing system for the invoicekit project. The system manages invoice creation, modification, issuance, and rendering with support for customer tiers, line discounts, VAT calculations, and proper date/ID handling.

## House Rules (Apply to All Future Work)

1. **Money as Integer Cents**: All monetary amounts are integers representing cents. Never store or return fractional cents. When calculations produce fractions, round using `roundCents()` from `src/money.js`.

2. **Error Handling**: Never throw errors for invalid input. Instead, return `fail(CODE)` from `src/result.js`. Add every new error code to the `ERRORS` object in `src/errors.js` with a one-line message.

3. **Immutability**: Never mutate function arguments. Always return new objects and arrays.

4. **Testing**: Run `npm test` before marking any task complete. Currently 141 tests pass.

5. **No Negative Amounts**: No amount we compute, on a line, an invoice, or anything we add later, may ever go below zero. Clamp at 0.

6. **Dates in UTC**: All dates are 'YYYY-MM-DD' strings everywhere. All date arithmetic is done in UTC, never in machine's local time zone. Use functions from `src/dates.js`.

7. **Customer IDs Normalized**: Always normalize customer IDs with `normalizeId()` from `src/customers.js` before comparing or storing them. Trim whitespace and uppercase.

## Key Decisions

1. **Invoice Numbering Format**: `INV-<year>-<counter>`
   - Year is extracted from the invoice's `issueDate`
   - Counter has 4 digits, zero-padded (0001, 0002, ..., 9999, 10000, ...)
   - Counter resets to 0001 at the start of each year
   - Example: `INV-2026-0001`

2. **Customer-Facing Amounts**: All monetary amounts displayed to customers must be formatted using `formatEuros()` from `src/money.js`. This ensures consistent euro formatting with symbol and two decimal places (e.g., `€1,234.56`).

3. **Line Discounts**: Lines can carry `discountPercent` (0-100, can have decimals like 12.5). Validation returns `DISCOUNT_INVALID` if invalid. Line discount = line total × discountPercent / 100, rounded per line.

4. **Customer Tier Discounts**: Every customer has a tier (gold, silver, standard). When a line has no explicit `discountPercent`, it gets the customer's tier discount:
   - Gold: 5%
   - Silver: 2.5%
   - Standard: 0%
   - Explicit discountPercent (even 0) always overrides tier discount.

5. **VAT Calculation**: VAT is computed per line on the line's amount after its discount, then rounded per line. Invoice VAT is the sum of rounded line VATs, never a percentage of invoice total. Formula: `(line_total - line_discount) * vatRate / 100`.

6. **Invoice Totals Structure**: Returns `{ subtotal, discount, vat, total }` where:
   - `subtotal` = sum of all line totals
   - `discount` = sum of all line discounts
   - `vat` = sum of all line VATs
   - `total` = subtotal - discount + vat (clamped at 0)

## What Has Been Built

### Core Modules

**src/invoices.js** - Main invoice operations
- `createInvoice({ customerId, issueDate, lines })` → Creates a draft invoice with validated and normalized customer, date, and line items. Normalizes customer ID and applies tier discounts to lines without explicit discountPercent.
- `lineTotal(line)` → Calculates `qty × unitPrice` in cents
- `lineDiscount(line)` → Calculates line discount as `(lineTotal × discountPercent) / 100`, clamped at 0
- `lineVAT(line)` → Calculates VAT on line after discount as `((lineTotal - lineDiscount) × vatRate) / 100`, clamped at 0
- `invoiceTotals(invoice)` → Returns `{ subtotal, discount, vat, total }` where total = subtotal - discount + vat (clamped at 0)
- `addLine(invoice, { sku, qty, discountPercent })` → Adds new line or increases qty of existing line. Applies tier discount if no explicit discountPercent. Can update discountPercent on existing lines.
- `removeLine(invoice, sku)` → Removes line; rejects if it's the last line
- `issueInvoice(invoice, existingNumbers)` → Assigns invoice number and changes status to 'issued'

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

**src/money.js** - Money utilities (existing)
- `roundCents(amount)` → Rounds monetary amounts using banker's rounding
- `formatEuros(cents)` → Formats cents as €X,XXX.XX

**src/catalogue.js** - Product lookup (existing)
- `getProduct(sku)` → Finds product by SKU, returns with name, unitPrice, vatRate

**src/result.js** - Result wrapper types (existing)
- `ok(value)` → Success result
- `fail(code)` → Failure result

### Error Codes (in src/errors.js)

- `AMOUNT_INVALID` - Amount must be a whole, positive number of cents
- `CUSTOMER_INVALID` - Customer needs an id, a name and a valid email
- `CUSTOMER_NOT_FOUND` - No customer with that id
- `DATE_INVALID` - Date must be in YYYY-MM-DD format and a valid calendar date
- `DISCOUNT_INVALID` - Discount percent must be a number between 0 and 100
- `LINE_NOT_FOUND` - No line with that SKU on the invoice
- `NOT_DRAFT` - Can only modify invoices with status "draft"
- `NO_LINES` - An invoice must have at least one line item
- `QTY_INVALID` - Quantity must be a positive integer
- `UNKNOWN_SKU` - No product with that SKU in the catalogue

### Invoice Data Structure

```javascript
{
  customerId: string,           // e.g., 'C-001' (normalized: uppercase, no leading/trailing spaces)
  issueDate: string,            // YYYY-MM-DD format (UTC, valid calendar date)
  status: 'draft' | 'issued',   // 'draft' when created, 'issued' after issueInvoice()
  number?: string,              // e.g., 'INV-2026-0001' (absent for draft)
  lines: [
    {
      sku: string,              // Product SKU
      name: string,             // Product name (from catalogue)
      qty: number,              // Positive integer
      unitPrice: number,        // Cents (from catalogue)
      vatRate: number,          // Percent (from catalogue): 0, 9, or 21
      discountPercent: number   // 0-100 (can have decimals like 12.5). If not explicit, set to customer tier discount
    }
  ]
}
```

### Test Coverage

- **test/invoices.test.js** - 120 tests for invoice creation, manipulation, issuance, discounts, VAT, and ID normalization
- **test/numbering.test.js** - 8 tests for invoice number generation
- **test/render.test.js** - 13 tests for invoice text rendering with VAT and discounts
- **test/dates.test.js** - 21 tests for date utilities and UTC operations
- **Total**: 141 passing tests

Run tests: `npm test`

## What's Unfinished

1. **Additional Rendering Formats**: Only plain-text rendering exists. HTML and PDF rendering can be added to `src/render.js`.

2. **Invoice Persistence**: No database or file storage for invoices—they exist only in memory during a request. Need to add database layer.

3. **Invoice Retrieval**: No functions to fetch existing invoices by ID or search invoices.

4. **Invoice Status Transitions**: Currently only 'draft' and 'issued' statuses exist. Future statuses (e.g., 'paid', 'cancelled', 'refunded') may require additional logic.

5. **Payment Processing**: No payment integration or payment tracking.

6. **Notifications**: No email or notification system for invoice creation/payment.

7. **Audit Logging**: No audit trail of invoice modifications.

## How to Continue

### Running Tests
```bash
npm test
```
All tests should pass. There are currently 141 tests covering invoices, numbering, rendering, and dates.

### File Organization
- **src/** - Source code
  - `invoices.js` - Main invoice operations (create, add lines, remove lines, issue, totals)
  - `customers.js` - Customer lookup and normalization
  - `catalogue.js` - Product lookup (existing)
  - `numbering.js` - Invoice numbering logic
  - `dates.js` - Date utilities (validation, arithmetic, all UTC)
  - `render.js` - Invoice rendering (plain-text; HTML/PDF can be added here)
  - `money.js` - Money formatting and parsing
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

### Example: Adding a New Feature

If asked to add invoice comments/notes:
1. Add `comment?: string` field to invoice data structure
2. Update `createInvoice()` to accept and validate comment
3. Update `addLine()` signature if needed (or create separate function)
4. Update `renderInvoiceText()` to display comment if present
5. Add comprehensive tests for comment validation, storage, and rendering
6. Run `npm test` to verify all 141+ tests still pass

### Testing Requirements
- Every new public function needs tests
- Test both happy path and error cases
- Test edge cases (empty inputs, boundary values, year/month transitions for dates)
- Test immutability (verify inputs aren't mutated)
- Test with different customer tiers and VAT rates
- Test amounts are clamped at 0
- Update test expectations when behavior changes
