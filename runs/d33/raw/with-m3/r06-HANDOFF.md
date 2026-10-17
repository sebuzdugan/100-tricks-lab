# Invoicekit Handoff

## Project Goal
Build a complete invoicing system into this Node.js project, starting with draft creation, line item management, invoice numbering, and text rendering. Later phases will add VAT calculation, discounts, payment tracking, and other features.

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

4. **Run `npm test` before completing each request**

## Architectural Decisions

### Invoice Numbers
Format: `INV-<year>-<counter>`
- Year is extracted from the invoice's issue date
- Counter is 4 digits, zero-padded (0001–9999)
- Counter restarts at 0001 every calendar year
- Gaps and out-of-order numbers are allowed

### Invoice Data Model
Invoices are self-contained records:
- `customerId`: Customer ID from catalogue
- `customerName`: Customer name (looked up at creation, stored for historical accuracy)
- `issueDate`: Date in YYYY-MM-DD format
- `number`: Invoice number (undefined for draft, set on issue)
- `status`: 'draft' or 'issued' (VAT calc and payments will add more states)
- `lines`: Array of line items, each with:
  - `sku`: Product SKU
  - `name`: Product name (from catalogue)
  - `qty`: Positive integer quantity
  - `unitPrice`: Cents (from catalogue, without VAT)
  - `vatRate`: Percent (from catalogue)

### Line Item Management
- `addLine` adds a new line or increments qty if SKU exists
- `removeLine` prevents removing the last line (invoices must have ≥1 line)
- Both refuse to modify non-draft invoices (error: NOT_DRAFT)
- Both preserve immutability

## What Has Been Built

### Core Modules

**src/invoices.js**
- `createInvoice({ customerId, issueDate, lines })` — Creates a draft invoice with enriched line items from the catalogue
- `addLine(invoice, { sku, qty })` — Adds or increments a line
- `removeLine(invoice, sku)` — Removes a line by SKU
- `lineTotal(line)` — Calculates qty × unitPrice
- `invoiceTotals(invoice)` — Returns { subtotal, total } (total=subtotal for now; VAT/discounts come later)
- `issueInvoice(invoice, existingNumbers)` — Assigns invoice number and changes status to 'issued'

**src/numbering.js**
- `nextInvoiceNumber(existingNumbers, issueDate)` — Generates the next free invoice number for a given year

**src/render.js**
- `renderInvoiceText(invoice)` — Renders invoice as plain text for customer display (all amounts via formatEuros)

**src/errors.js**
- Added error codes: DATE_INVALID, NO_LINES, QTY_INVALID, NOT_DRAFT, LINE_NOT_FOUND

### Tests
- `test/invoices.test.js` — 40+ tests for all invoice functions (creation, line management, totals, issuing)
- `test/numbering.test.js` — 7 tests for invoice number generation (year boundaries, counter padding, edge cases)
- `test/render.test.js` — 10 tests for text rendering (formatting, line breaks, large quantities, zero prices)

**All 62 tests pass.**

## What's Not Done (Future Work)

- VAT calculation (invoiceTotals will need to split subtotal into pre-tax and tax amounts)
- Discounts (line-level and invoice-level)
- Payment tracking (status transitions, payment history)
- Editing issued invoices (credit notes, amendments)
- Persistence (database storage, retrieval, updates)
- PDF rendering (beyond plain text)

## How to Run Tests

```bash
npm test
```

All tests are in `test/` using Node's built-in `node:test` module. No external test framework.

## Key Files to Know

- `src/money.js` — `roundCents()`, `formatEuros()`, `parseEuros()`
- `src/customers.js` — `getCustomer(id)`, `listCustomers()`
- `src/catalogue.js` — `getProduct(sku)`, `listProducts()`
- `src/result.js` — `ok(value)`, `fail(error, details)`
- `data/customers.json` — Customer records (id, name, email, country, tier)
- `data/catalogue.json` — Product records (sku, name, unitPrice, vatRate)

## Integration Points for Next Agent

When adding new features (e.g., VAT calculation):
1. Update the invoice data model if needed (add fields in `createInvoice`, `addLine`, `removeLine`, `issueInvoice`)
2. Add error codes to `src/errors.js` as needed
3. Preserve immutability and avoid mutations
4. Update `renderInvoiceText` if rendering format changes
5. Always run `npm test` before finishing
6. Don't forget to add tests for any new functions or error cases
