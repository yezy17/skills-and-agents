# Output Template

Use this structure for any meaningful stock recommendation response.
Do not collapse everything into one paragraph.

## Market Frame

- `As of`: exact date for price data
- `Mode`: daily scan, watchlist review, portfolio review, or single-name dive
- `Profile`: offensive or balanced
- `Market regime`: bull / neutral / bear / crisis
- `SPY trend`: above or below 50-day and 200-day MA
- `VIX`: current level and classification (low / normal / elevated / high)
- `Dip buy active`: yes or no (only yes in bear/crisis)
- `Risk tone`: normal, aggressive, or event-driven
- `What I checked`: short line naming the main data sources

## Ranked List

For each name, use the following fields in this order:

### `TICKER - Company Name`

- `Bucket`: Aggressive Buy Candidate / Pullback Watch / Catalyst / Event Watch / Dip Buy Candidate / Manage Existing Position / Avoid / No-Trade
- `Score`: numeric score and short interpretation
- `Last price`: exact price and as-of date
- `Why it is here`: 2-4 short bullets based on trend, volume, fundamentals, and events
- `Setup`: breakout / pullback / catalyst / broken trend
- `Preferred action now`: buy trigger, watch, hold, trim, or exit
- `Buy zone or trigger`: exact numbers when possible
- `Invalidation / stop`: exact number and what would make the thesis wrong
- `Stop-watch status`: ok / near stop / stop breached when the user already holds the name
- `Profit plan`: first trim and next management rule
- `Sizing note`: how large the position should be relative to the account and why
- `Catalyst window`: earnings date, filing date, analyst change window, or sector news timing
- `Main risks`: short bullets, not buried prose
- `Sources`: concise list of checked sources

## Portfolio Actions

If the user has active holdings, summarize them separately after the ranked list:

- `Add`: only if the setup is still valid and not overextended
- `Hold`: trend intact, no action needed
- `Trim`: extended or event risk rising
- `Exit`: thesis broken or stop violated

If any stop is near or breached, add a short `Alerts` section above the normal portfolio actions.

## Watchlist Changes

If useful, end with three tiny sections:

- `Promote to active watch`
- `Keep on bench`
- `Remove from watch`

## Style rules

- Use exact dates, not vague phrases like `soon`
- Do not hide low confidence
- Do not say `strong buy` unless the rules actually support it
- Always give the user at least one reason not to take the trade

