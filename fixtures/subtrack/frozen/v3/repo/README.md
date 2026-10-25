# subtrack

Keep track of your subscriptions from the terminal: what they cost you each month, and what renews next.
Plain Node.js (ES modules), no dependencies.

```sh
subtrack add Netflix 12.99                        # monthly by default, first charge today
subtrack add "Domain name" 14 --every year --since 2026-03-02
subtrack list                                     # every plan with its monthly cost
subtrack total                                    # what all of it costs you a month
subtrack renewals --within 14                     # charges coming up in the next 14 days, soonest first
subtrack export > subs.csv                        # CSV for a spreadsheet
subtrack remove Netflix
```

During development, run it with `node bin/subtrack.js <command>`.

## Options

| Option | Commands | Meaning |
|---|---|---|
| `--every month\|year` | add | How often the plan charges you (default `month`). |
| `--since YYYY-MM-DD` | add | Date of the first charge (default today). Later charges fall on the same day of the month, or the last day of a shorter month. |
| `--within <days>` | renewals | How far ahead to look (default 30). A charge today counts. |
| `--today YYYY-MM-DD` | list, renewals, export | Pretend today is another date. |
| `--file <path>` | all | Where your subscriptions are kept. Default: `$SUBTRACK_FILE`, else `./subscriptions.json`. |

## Money

Prices are typed in euros (`12.99`, `1,299.00`) and kept in whole cents. The monthly cost of a yearly plan is its
price divided by 12.

## Code

- `bin/subtrack.js`: the command line
- `src/cycles.js`: billing cycles: monthly cost and next charge of a plan
- `src/renewals.js`: upcoming charges
- `src/export.js`: CSV export
- `src/store.js`: reading and writing the subscriptions file
- `src/dates.js`, `src/money.js`: date and money helpers

Run the tests with `npm test`.
