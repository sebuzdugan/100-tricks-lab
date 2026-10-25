Some people pay for things every week (a meal kit, a cleaner, a weekly class), and subtrack can't track those yet.

Please add weekly subscriptions:

- `subtrack add "Meal kit" 59.90 --every week` should work, next to the existing `--every month` and `--every year`.
- A weekly plan costs its price × 52 ÷ 12 a month (€12 a week is €52.00 a month), rounded to the nearest cent like every monthly cost from now on (today they are cut off), and that is the monthly cost subtrack should show for it everywhere.
- Weekly plans charge every 7 days from their first charge (`--since`), and `subtrack renewals` should list them like any other plan.
