# Rules and Scoring

## Objective

Rank U.S. equities for short-horizon swing trading and catalyst trading without pretending certainty.
The score is only a prioritization tool. The final answer must still explain what could go wrong.

## Tradability filters

Exclude a stock from normal swing ideas unless the user explicitly wants ultra-high risk when any of these are true:

- price under `5 USD`
- average 20-day dollar volume under `20 million USD`
- major earnings event within `5 calendar days`
- extreme drawdown from 52-week high greater than `45%`

These names can still appear in `Catalyst / Event Watch` or `Avoid / No-Trade` if they are educationally relevant.

## Score components

### Trend: up to 35 points

Award points for:

- price above 20-day moving average
- price above 50-day moving average
- price above 200-day moving average
- 20-day above 50-day
- 50-day above 200-day
- positive 3-month relative strength vs `SPY`
- positive 6-month relative strength vs `SPY`

Interpretation:

- clean MA stack plus positive RS means institutions are likely still participating
- broken MA stack means the name may need more time, even if the story sounds good

### Price and volume: up to 20 points

Key bullish patterns:

- `Breakout`: close above the prior 20-day or 55-day high with volume at least `1.5x` the 20-day average
- `Constructive pullback`: price stays above 50-day moving average, comes back toward 20-day or 50-day moving average, and volume contracts below `0.85x` the 20-day average
- `Tight range`: ATR percent is controlled and the name is not just wildly thrashing

Key warnings:

- high ATR percent makes the position harder to size
- breakout without volume confirmation is lower quality

### Fundamentals: up to 25 points

Use the following fields when available:

- revenue growth
- profit margin
- debt to equity
- current ratio
- forward PE
- trailing PE
- price to book
- return on equity

General logic:

- reward positive and accelerating business quality
- reward balance-sheet resilience
- prefer less stretched valuation versus the current candidate set, not an absolute magic number
- missing values should reduce confidence, not trigger made-up opinions

### Catalyst and event context: up to 10 points

Reward only modestly. Catalysts matter, but they should not overpower trend and liquidity.

Examples:

- fresh 10-Q or 10-K that supports the trend
- recent 8-K that changes the story in a meaningful way
- net positive analyst-rating changes in the last 30 days
- upcoming but not immediate earnings window

### Risk penalties: down to -30 points

Subtract for:

- earnings within 5 days
- ATR percent above roughly `8%`
- low liquidity
- large drawdown from the 52-week high
- weak balance-sheet flags
- broken trend after a large recent run

## Bucket mapping

Use score plus setup quality, not score alone.

- `80-100`: `Aggressive Buy Candidate`
- `65-79`: `Pullback Watch`
- `50-64`: `Catalyst / Event Watch`
- `0-49`: `Avoid / No-Trade`

If the user already owns the name, you may override the bucket to `Manage Existing Position`.

## Entry and exit playbook

### Breakout setup

Use when a stock clears a recent high with strong volume.

- `entry trigger`: above the breakout pivot or on an orderly retest
- `buy zone`: pivot to pivot plus `0.5 ATR`
- `initial stop`: around `1.2 ATR` below the trigger or below the 20-day line, whichever is stricter
- `first trim`: near `1R`
- `second trim`: near `2R`
- `management`: if it keeps trending, trail behind the 10-day line or a volatility-based stop

### Pullback setup

Use when the primary trend is intact but price has cooled off.

- `buy zone`: around the 20-day or 50-day line when volume has dried up
- `initial stop`: below the support line or `1.2 ATR`, whichever invalidates the setup more clearly
- `first trim`: near `1.5R`
- `management`: if support fails on heavy volume, do not average down blindly

### Catalyst setup

Use when an event is the main driver.

- size smaller than a normal swing position
- require a clearly defined invalidation level
- if earnings are imminent, say that the setup is binary and confidence is lower

## Position sizing for a 10,000 USD account

Use risk-first sizing, not story-first sizing.

Suggested default risk budgets:

- `Aggressive Buy Candidate`: risk up to `1.5%` of account equity per idea
- `Pullback Watch`: risk up to `1.0%`
- `Catalyst / Event Watch`: risk up to `0.5%`

Suggested max gross allocation:

- `Aggressive Buy Candidate`: up to `35%` of account
- `Pullback Watch`: up to `25%`
- `Catalyst / Event Watch`: up to `15%`

Position-size formula:

- `risk_per_share = entry - stop`
- `shares_by_risk = floor(account_risk_budget / risk_per_share)`
- `shares_by_cap = floor(max_position_value / entry)`
- `planned_shares = min(shares_by_risk, shares_by_cap)`

If `planned_shares` is zero, say the setup is too volatile for the account size.

