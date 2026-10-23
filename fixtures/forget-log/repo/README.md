# shopstats

Small scripts for looking at the shop's order data.

- `data/orders.json`: orders as `{ id, customer, amount, date }`; `amount` is in cents (negative = refund), `date` is `YYYY-MM-DD`.
- `src/data.js`: `loadOrders()` reads the orders.
- `src/log.js`: the project's `log()` helper.
- `scripts/`: one script per report, run with `node scripts/<name>.js`.
