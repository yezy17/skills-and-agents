# Data Sources

## Default stack

Use this source hierarchy unless the user explicitly wants a different provider.

### 1. SEC EDGAR and data.sec.gov

Use for:

- 8-K, 10-Q, 10-K, DEF 14A, Form 4, and other filing events
- recent filing dates and official filing URLs
- company ticker to CIK mapping
- cross-checking whether a catalyst is real or just media noise

Why it is first choice:

- official U.S. regulator source
- real-time filing updates
- free public access
- structured JSON endpoints for submissions and company-facts style data

Rules:

- set a descriptive `User-Agent`
- keep request rate under SEC fair-access limits
- prefer the latest filings that materially affect the thesis

Useful endpoints:

- `https://www.sec.gov/files/company_tickers_exchange.json`
- `https://data.sec.gov/submissions/CIK##########.json`
- `https://www.sec.gov/Archives/edgar/data/...`

### 2. yfinance

Use for:

- daily price and volume history
- moving averages, ATR, 3/6 month relative strength, and drawdown math
- public screen presets such as `most_actives`, `day_gainers`, and growth-oriented screens
- quick valuation and quality fields exposed through Yahoo Finance data
- earnings calendar hints and analyst upgrade/downgrade history when available

Why it is good enough for this skill:

- no paid API key required
- broad symbol coverage
- easy multi-ticker download flow
- enough metadata to seed a fast daily scan

Caveats:

- this is not an official exchange or regulator feed
- Yahoo data accessed through yfinance is intended for research and educational use and personal use only
- some fields may be delayed, missing, or inconsistent across tickers

Operational rule:

- use yfinance for screening and daily math
- use SEC or company IR to confirm important events before you lean on them

### 3. Company investor-relations pages or official press releases

Use for:

- confirming earnings-call timing
- press-release context after an 8-K or major announcement
- investor-presentation links when a filing is too dense for a quick first pass

Use only when the filing signal needs more context.

## Not the default

### Alpha Vantage, Finnhub, Financial Modeling Prep, Polygon, IEX

These can be useful later, but do not make them the default for this private skill unless the user decides to bring an API key or paid plan.

Reasons they are not the default here:

- extra setup friction
- tighter free-tier limits or account requirements
- this skill should work out of the box with public data first

## Source priority by task

- price, volume, moving averages, ATR, relative strength: `yfinance`
- filing dates, 8-K/10-Q/10-K checks, official event confirmation: `SEC`
- earnings proximity: `yfinance` first, then company IR if needed
- analyst-rating changes: `yfinance` if present, otherwise mark as unavailable
- sector context: compare to `SPY` plus sector or industry context from `yfinance`

## Missing-data behavior

If a field is missing:

- keep the field missing instead of substituting a guess
- lower confidence rather than inventing a clean story
- say which source was checked and what was unavailable

