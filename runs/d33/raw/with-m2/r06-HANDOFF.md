# Invoicekit: Handoff

## Project Goal

Build a complete invoicing system for a service business. The system manages creating, editing, issuing, and rendering invoices with proper numbering and formatting.

## House Rules (Apply to All Requests)

1. **Money is always an integer number of cents.** Never store or return fractional amounts. When a calculation produces fractional cents, round using `roundCents()` from `src/money.js`.

2. **Never throw for bad input.** Return `fail(CODE)` from `src/result.js` instead. Add every new error code to `ERRORS` in `src/errors.js` with a one-line message.

3. **Never mutate an argument.** Return new objects and arrays instead.

4. **Run `npm test` before you say a request is done.**

5. **All amounts shown to customers use `formatEuros()`** from `src/money.js`. This applies to anything rendered for customer display going forward.

## Key Decisions Made

- **Invoice numbering format:** `INV-<year>-<counter>` where counter is 4 digits, zero-padded, starting at 0001 and restarting every year.
- **Invoice statuses:** `draft` (editable), `issued` (numbered and locked). Only draft invoices can be modified.
- **Error handling:** Uses result-style `{ ok: boolean, value?, error?, details? }` pattern. Never throws exceptions for validation errors.
- **Customer-facing output:** All monetary amounts must go through `formatEuros()` for consistency.

## What Has Been Built

### Core Files

| File | Purpose |
|------|---------|
| `src/money.js` | Money formatting and parsing (pre-existing: `roundCents`, `formatEuros`, `parseEuros`) |
| `src/result.js` | Result pattern for error handling (pre-existing: `ok()`, `fail()`) |
| `src/errors.js` | All error codes and messages |
| `src/catalogue.js` | Product catalogue (pre-existing: `getProduct()`, `listProducts()`) |
| `src/customers.js` | Customer database (pre-existing: `getCustomer()`, `listCustomers()`, `validateCustomer()`) |
| `src/invoices.js` | **NEW** Core invoicing functions |
| `src/numbering.js` | **NEW** Invoice number generation |
| `src/render.js` | **NEW** Invoice text rendering |

### Implemented Functions

#### `src/invoices.js`
- `createInvoice({ customerId, issueDate, lines })` — Create a draft invoice
  - Lines input: `{ sku, qty }` arrays
  - Output lines expanded with catalogue data: `{ sku, name, qty, unitPrice, vatRate }`
  - Errors: `CUSTOMER_NOT_FOUND`, `DATE_INVALID`, `NO_LINES`, `QTY_INVALID`, `UNKNOWN_SKU`

- `lineTotal(line)` — Calculate total for a single line (qty × unitPrice, rounded)

- `invoiceTotals(invoice)` — Calculate invoice totals
  - Returns `{ subtotal, total }` (total currently equals subtotal)

- `addLine(invoice, { sku, qty })` — Add or increase a line
  - Adds new line or increases qty if SKU exists
  - Status must be `draft`, or returns `NOT_DRAFT`
  - Same validation as create (QTY_INVALID, UNKNOWN_SKU)

- `removeLine(invoice, sku)` — Remove a line
  - Returns `LINE_NOT_FOUND` if SKU not on invoice
  - Returns `NO_LINES` if would remove last line
  - Status must be `draft`, or returns `NOT_DRAFT`

- `issueInvoice(invoice, existingNumbers)` — Change status from draft to issued
  - Assigns next invoice number
  - Returns `NOT_DRAFT` if already issued
  - Takes array of existing numbers for numbering logic

#### `src/numbering.js`
- `nextInvoiceNumber(existingNumbers, issueDate)` — Calculate next invoice number
  - Format: `INV-<year>-<counter>` (4-digit counter, zero-padded)
  - Restarts counter each year
  - Ignores malformed numbers gracefully

#### `src/render.js`
- `renderInvoiceText(invoice)` — Plain-text invoice for display
  - Line 1: Invoice number or "DRAFT"
  - Line 2: Customer name
  - Lines 3+: Item lines with `qty × name @ unitPrice = lineTotal`
  - Final line: `Total: ` with formatted total
  - All amounts use `formatEuros()`

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

### Test Coverage

| File | Tests | Coverage |
|------|-------|----------|
| `test/invoices.test.js` | 54 | createInvoice, lineTotal, invoiceTotals, addLine, removeLine, issueInvoice |
| `test/numbering.test.js` | 10 | nextInvoiceNumber (edge cases, year boundaries, malformed data) |
| `test/render.test.js` | 12 | renderInvoiceText (formats, amounts, customer lookup) |
| **Total** | **77** | All new functionality |

**Total test suite:** 77 passing tests (includes pre-existing tests for money, catalogue, customers)

## Unfinished Work

The following features have not been implemented but are likely needed:

- **VAT calculation** — `vatRate` is stored on lines but not used in totals yet
- **Discount support** — invoiceTotals currently has `subtotal === total`
- **Line item discounts** — May need per-line or invoice-level discounts
- **Payment tracking** — No payment or due date fields
- **Invoice retrieval** — No way to fetch invoices by number or date
- **Persistence** — No database or file storage (all in-memory)
- **Invoice state transitions** — Only draft → issued; no cancelled, refunded, etc.
- **PDF rendering** — Only plain text rendering exists
- **Internationalization** — Hard-coded euro formatting

## Invoice Object Structure

A complete invoice looks like:

```javascript
{
  customerId: "C-001",
  issueDate: "2025-10-07",
  status: "draft" | "issued",
  number: "INV-2025-0001", // only if issued
  lines: [
    {
      sku: "DEV-HOUR",
      name: "Development (hour)",
      qty: 5,
      unitPrice: 9500, // cents, without VAT
      vatRate: 21 // percent
    }
    // ...
  ]
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

1. Check this HANDOFF.md for context (you're reading it)
2. Run `npm test` to verify the current state
3. Read the relevant source files for the feature you're building
4. Review existing tests to understand the pattern
5. Add tests first, then implement
6. Follow the house rules (especially money-as-cents and no-throws)
7. Update this document when you add new rules or decisions

## Data Files

The system loads from JSON files in `/data/`:

- `customers.json` — Customer list (id, name, email, country, tier)
- `catalogue.json` — Product catalogue (sku, name, unitPrice in cents, vatRate in percent)

These are pre-existing and read-only within the codebase.
