Some people pay for things every week (a meal kit, a cleaner, a weekly class), and subtrack can't track those yet.

Please add weekly subscriptions:

- `subtrack add "Meal kit" 59.90 --every week` should work, next to the existing `--every month` and `--every year`.
- A weekly plan costs its price × 52 ÷ 12 a month (€12 a week is €52.00 a month), and that is the monthly cost subtrack should show for it everywhere.
- Weekly plans charge every 7 days from their first charge (`--since`), and `subtrack renewals` should list them like any other plan.

One more change while you're in there: monthly costs are currently cut off at the cent, so a €119.99 yearly plan shows as €9.99 a month. Round them to the nearest cent instead (that plan should show €10.00).
