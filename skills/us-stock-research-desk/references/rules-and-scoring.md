# Rules and Scoring

## Default mode

The default mode is now `offensive`.

That means:

- favor high-beta momentum and catalyst names
- tolerate more volatility than a conservative swing system
- still keep hard risk budgets, defined stops, and smaller event sizing

Use `balanced` only when the user explicitly asks for a calmer profile.

## Objective

Rank U.S. equities for short-horizon swing trading and catalyst trading without pretending certainty.
The score is a prioritization tool, not a prophecy.

## Profile summary

### Offensive profile

Use when the user wants a more aggressive style.

- default screens lean toward gainers, active names, and growth technology
- minimum normal price: about `3 USD`
- minimum normal 20-day dollar volume: about `15 million USD`
- stronger weight on breakouts, momentum, and fresh catalysts
- single-position risk should still usually stay under `2%` of account equity

### Balanced profile

Use when the user asks for cleaner and calmer setups.

- minimum normal price: about `5 USD`
- minimum normal 20-day dollar volume: about `20 million USD`
- heavier penalty for event risk and weak liquidity

## Tradability filters

### Offensive default

Exclude a stock from normal offensive swing ideas unless the user explicitly wants ultra-high risk when any of these are true:

- price under `3 USD`
- average 20-day dollar volume under `15 million USD`
- earnings within `2 calendar days`
- drawdown from the 52-week high greater than `55%`

These names can still appear in `Catalyst / Event Watch` or `Avoid / No-Trade` if they are educationally relevant.

### Balanced fallback

Use the stricter balanced limits:

- price under `5 USD`
- average 20-day dollar volume under `20 million USD`
- earnings within `5 calendar days`
- drawdown from the 52-week high greater than `45%`

## Offensive score weights

### Trend: up to 35 points

Award points for:

- price above 20-day moving average
- price above 50-day moving average
- price above 200-day moving average
- 20-day above 50-day
- 50-day above 200-day
- positive 3-month relative strength vs `SPY`
- positive 6-month relative strength vs `SPY`
- rising 200-day moving average

Interpretation:

- offensive trading still wants trend alignment
- if the trend is broken, do not let a flashy story override the chart

### Price and volume: up to 30 points

This category matters more in offensive mode.

Key bullish patterns:

- `Breakout`: close above the prior 20-day or 55-day high with volume at least about `1.3x` the 20-day average
- `Power breakout`: breakout plus volume closer to `1.8x` or better
- `Constructive pullback`: price remains above support and volume dries up below roughly `0.90x` the 20-day average
- `Momentum continuation`: positive short-horizon relative strength and expanding demand

Interpretation:

- offensive mode is willing to pay up for strength
- breakout quality matters more than buying a cheap story

### Fundamentals: up to 18 points

Fundamentals still matter, but they no longer dominate the score.

Use:

- revenue growth
- profit margin
- debt to equity
- current ratio
- forward valuation percentile
- return on equity

Interpretation:

- reward real business strength
- do not require perfect value metrics from fast-moving leaders

### Catalyst and event context: up to 15 points

This matters more in offensive mode.

Reward:

- recent 8-K or 10-Q that materially supports the narrative
- positive analyst-rating drift in the last 30 days
- earnings close enough to matter, but not so close that it becomes a coin flip
- sector or product catalysts confirmed by filings or reputable reporting

Interpretation:

- catalysts can accelerate winning trades
- catalysts can also increase gap risk, so score boost does not remove the need for smaller size

### Risk penalties: down to roughly -30 points

Subtract for:

- earnings within `2 days` very heavily
- ATR above roughly `10% to 12%`
- weak liquidity
- deep drawdown from the 52-week high
- very low-priced names
- excessive balance-sheet leverage

Interpretation:

- offensive mode is not the same as reckless mode
- if the stock is too chaotic for the account size, the system should say so

## Bucket mapping

Use score plus setup quality, not score alone.

### Offensive default

- `76-100`: `Aggressive Buy Candidate`
- `62-75`: `Pullback Watch`
- `48-61`: `Catalyst / Event Watch`
- `0-47`: `Avoid / No-Trade`

### Balanced fallback

- `80-100`: `Aggressive Buy Candidate`
- `65-79`: `Pullback Watch`
- `50-64`: `Catalyst / Event Watch`
- `0-49`: `Avoid / No-Trade`

If the user already owns the name, you may override the bucket to `Manage Existing Position`.

## Entry and exit playbook

### Breakout setup

Use when a stock clears a recent high with strong volume.

- `entry trigger`: above the breakout pivot or on an orderly retest
- `buy zone`: pivot to pivot plus roughly `0.5 to 0.75 ATR`
- `initial stop`: around `1.2 to 1.35 ATR` below the trigger or below the 20-day line, whichever is stricter
- `first trim`: near `1R`
- `second trim`: near `2R`
- `management`: if it trends well, trail behind the 10-day line or a volatility stop

### Pullback setup

Use when the primary trend is intact but price has cooled off.

- `buy zone`: around the 20-day or 50-day line when volume has dried up
- `initial stop`: below the support line or below the reset range
- `first trim`: near `1.5R`
- `management`: if support fails on heavy volume, do not average down blindly

### Catalyst setup

Use when an event is the main driver.

- size smaller than a normal swing position
- require a clearly defined invalidation level
- if earnings are imminent, say that the setup is binary and confidence is lower

## Position sizing for a 10,000 USD account

Use risk-first sizing, not story-first sizing.

### Offensive default

Suggested default risk budgets:

- `Aggressive Buy Candidate`: risk up to about `1.8%` of account equity
- `Pullback Watch`: risk up to about `1.25%`
- `Catalyst / Event Watch`: risk up to about `0.75%`

Suggested max gross allocation:

- `Aggressive Buy Candidate`: up to `40%`
- `Pullback Watch`: up to `30%`
- `Catalyst / Event Watch`: up to `20%`

Guardrail:

- avoid pushing beyond `2%` account risk on a single idea

### Balanced fallback

Suggested default risk budgets:

- `Aggressive Buy Candidate`: up to `1.5%`
- `Pullback Watch`: up to `1.0%`
- `Catalyst / Event Watch`: up to `0.5%`

Suggested max gross allocation:

- `Aggressive Buy Candidate`: up to `35%`
- `Pullback Watch`: up to `25%`
- `Catalyst / Event Watch`: up to `15%`

## Position-size formula

- `risk_per_share = entry - stop`
- `shares_by_risk = floor(account_risk_budget / risk_per_share)`
- `shares_by_cap = floor(max_position_value / entry)`
- `planned_shares = min(shares_by_risk, shares_by_cap)`

If `planned_shares` is zero, say the setup is too volatile for the account size.
