# Workshop interactivity

The remaster keeps the original 13-category workshop model and a single canonical BMW/economy state.

Purchases charge the recovered prices, as the original does. A refused purchase (money below the price) shows the original "Din fattiglus!" dialog (`brokeassalert`, sprite 290). `free_purchases` is a testing switch that bypasses payment rather than replacing authentic values with zero; it defaults to `false`.

LAKKERING's `skift` is the paint purchase (button 395): 500 kr and BMW cred replaced up to 0.15, and the RGB mixer opens only when it is paid for.

Option counts, labels, prices, Street Cred rewards, ownership behavior, animation, sound and category-specific interactions must come from the preserved SWF. Unknown values stay unrecovered rather than invented.

The same canonical state must ultimately drive VERKSTED, SHOWROOM and KJØR!.
