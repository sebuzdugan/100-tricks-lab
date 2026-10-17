# Invoicekit - Handoff

## Project Goal
Build a complete invoicing system for the invoicekit project. The system manages invoice creation, modification, issuance, and rendering.

## House Rules (Apply to All Future Work)

1. **Money as Integer Cents**: All monetary amounts are integers representing cents. Never store or return fractional cents. When calculations produce fractions, round using `roundCents()` from `src/money.js`.

2. **Error Handling**: Never throw errors for invalid input. Instead, return `fail(CODE)` from `src/result.js`. Add every new error code to the `ERRORS` object in `src/errors.js` with a one-line message.

3. **Immutability**: Never mutate function arguments. Always return new objects and arrays.

4. **Testing**: Run `npm test` before marking any task complete.

## Key Decisions

1. **Invoice Numbering Format**: `INV-<year>-<counter>`
   - Year is extracted from the invoice's `issueDate`
   - Counter has 4 digits, zero-padded (0001, 0002, ..., 9999, 10000, ...)
   - Counter resets to 0001 at the start of each year
   - Example: `INV-2026-0001`

2. **Customer-Facing Amounts**: All monetary amounts displayed to customers must be formatted using `formatEuros()` from `src/money.js`. This ensures consistent euro formatting with symbol and two decimal places (e.g., `€1,234.56`).

## What Has Been Built

### Core Modules

**src/invoices.js** - Main invoice operations
- `createInvoice({ customerId, issueDate, lines })` → Creates a draft invoice with validated customer, date, and line items
- `lineTotal(line)` → Calculates `qty × unitPrice` in cents
- `invoiceTotals(invoice)` → Returns `{ subtotal, total }` (currently `total = subtotal` pending VAT)
- `addLine(invoice, { sku, qty })` → Adds new line or increases qty of existing line
- `removeLine(invoice, sku)` → Removes line; rejects if it's the last line
- `issueInvoice(invoice, existingNumbers)` → Assigns invoice number and changes status to 'issued'

**src/numbering.js** - Invoice numbering
- `nextInvoiceNumber(existingNumbers, issueDate)` → Generates next available invoice number for the given year

**src/render.js** - Invoice rendering
- `renderInvoiceText(invoice)` → Returns plain-text invoice with: number/DRAFT, customer name, line items with formatted prices, and total

### Error Codes (in src/errors.js)

- `DATE_INVALID` - Date must be in YYYY-MM-DD format and a valid calendar date
- `LINE_NOT_FOUND` - SKU not found on the invoice
- `NOT_DRAFT` - Cannot modify invoices that aren't in draft status
- `NO_LINES` - Invoice must have at least one line item
- `QTY_INVALID` - Quantity must be a positive integer

### Invoice Data Structure

```javascript
{
  customerId: string,           // e.g., 'C-001'
  issueDate: string,            // YYYY-MM-DD format
  status: 'draft' | 'issued',   // 'draft' when created, 'issued' after issueInvoice()
  number?: string,              // e.g., 'INV-2026-0001' (absent for draft)
  lines: [
    {
      sku: string,              // Product SKU
      name: string,             // Product name (from catalogue)
      qty: number,              // Positive integer
      unitPrice: number,        // Cents (from catalogue)
      vatRate: number           // Percent (from catalogue)
    }
  ]
}
```

### Test Coverage

- **test/invoices.test.js** - 42 tests for invoice creation, manipulation, and issuance
- **test/numbering.test.js** - 8 tests for invoice number generation
- **test/render.test.js** - 11 tests for invoice text rendering
- **Total**: 66 passing tests

Run tests: `npm test`

## What's Unfinished

1. **VAT Calculations**: The `invoiceTotals()` function currently returns `total = subtotal`. VAT will be calculated separately by customer tier or product rate and added to the total.

2. **Discounts**: No discount system implemented yet.

3. **Additional Rendering Formats**: Only plain-text rendering exists. HTML and PDF rendering can be added to `src/render.js`.

4. **Invoice Persistence**: No database or file storage for invoices—they exist only in memory during a request.

5. **Invoice Retrieval**: No functions to fetch existing invoices by ID or search invoices.

6. **Invoice Status Transitions**: Currently only 'draft' and 'issued' statuses exist. Future statuses (e.g., 'paid', 'cancelled') may require additional logic.

## How to Continue

### Running Tests
```bash
npm test
```

### File Organization
- **src/** - Source code
  - `invoices.js` - Main invoice operations
  - `numbering.js` - Invoice numbering logic
  - `render.js` - Invoice rendering (start here for new formats)
  - `errors.js` - Error codes (update here for new errors)
  - `money.js` - Money formatting and parsing (existing)
  - `customers.js` - Customer lookup (existing)
  - `catalogue.js` - Product lookup (existing)
  - `result.js` - Result wrapper types (existing)
- **test/** - Test files (mirror src/ structure)
- **data/** - Data files (customers.json, catalogue.json)

### Next Steps Example
If asked to add VAT calculations:
1. Update `invoiceTotals(invoice)` to calculate VAT based on `vatRate` of each line
2. Return `{ subtotal, vatAmount, total }` instead of current structure
3. Update `renderInvoiceText()` to display VAT line item
4. Add tests for VAT calculations
5. Run `npm test` to verify

### Common Patterns
- Always use `ok(value)` and `fail(code)` from `src/result.js`
- Always validate customer exists with `getCustomer(customerId)`
- Always validate products exist with `getProduct(sku)`
- Always copy objects when returning modified invoices (never mutate input)
- Always format monetary amounts with `formatEuros()` when displaying to users
- Always zero-pad counters in invoice numbers
