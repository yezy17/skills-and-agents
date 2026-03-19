---
name: us-stock-research-desk
description: Research and manage U.S. equity swing-trade ideas, daily watchlists, catalyst calendars, and existing holdings using public market data plus SEC filings. Use whenever the user asks for 美股 or U.S. stock ideas, offensive scans, watchlist ranking, breakout or pullback entries, earnings or 8-K catalyst review, analyst-rating changes, risk flags, or wants OpenClaw to remember positions and turn them into entry, trim, hold, or exit plans.
---

# US Stock Research Desk

## Overview

Use this skill to turn public U.S. equity data into a daily action plan instead of vague market commentary.
The default operating style is now `offensive`: favor high-beta momentum, breakouts, and catalyst names, but keep explicit risk caps, defined stops, and smaller event sizing.
In bear or crisis markets, the system switches to a contrarian dip-buy mode instead of retreating.

## Workflow

### 1. Choose the mode

Classify the user request into one of these modes:

- `daily-scan`: build a ranked idea list from public screens or a watchlist
- `watchlist-review`: score a user-provided ticker list and update the action plan
- `portfolio-review`: update holdings, assess position health, and suggest hold or trim or exit logic
- `single-name-dive`: dig into one stock with more filing and event context
- `risk-monitor`: update stop levels, check stop alerts, and prepare warning messages
- `daily-review`: append a structured journal entry after the trading day
- `backtest-review`: evaluate past recommendations and generate a scoring accuracy report

### 2. Load only the references you need

- Read `references/data-sources.md` before deciding which data source to trust.
- Read `references/rules-and-scoring.md` when you need the scoring rubric, offensive profile rules, setup definitions, or position-sizing rules.
- Read `references/output-template.md` before drafting the final answer.
- Read `references/portfolio-workflow.md` only when the user gives holdings, fills, or asks you to remember positions.
- Read `references/monitoring-and-learning.md` when the user asks about stop rules, hourly monitoring, backtesting, or how the agent should improve over time.

### 3. Use the helper scripts when possible

- Run `scripts/build_stock_snapshot.py` for latest price, trend, volume, fundamentals, catalyst, SEC filing, risk snapshot data, and market regime classification.
- Run `scripts/portfolio_journal.py` to initialize, update, or summarize a transaction ledger.
- Run `scripts/stop_guard.py` to initialize, update, or check the stop-watch file.
- Run `scripts/backtest_journal.py` to log recommendations, evaluate past picks after N trading days, and generate scoring accuracy reports.
- If a script fails because dependencies are missing, say so briefly and fall back to a manual workflow instead of hallucinating values.

### 4. Cross-check freshness before recommending anything

Always state the as-of date for price data and the date of the latest catalyst you cite.
If the market data is stale, missing, or contradictory, say so and downgrade confidence.

## Hard Rules

- Always report the current market regime (bull/neutral/bear/crisis) at the top of any scan output.
- Use official or primary sources for filings and corporate events whenever available.
- Treat free market-data wrappers as convenient but imperfect; mention caveats when the source is unofficial or personal-use only.
- Never promise that a stock will double or return 50 percent in one or two weeks.
- If the user asks for very aggressive growth, still respond with defined-risk setups, invalidation levels, and smaller event sizes.
- Never output a naked `buy this now` line. Always include setup type, entry logic, stop or invalidation, first trim level, and key risk flags.
- Do not assume a stop price guarantees the exit price. Fast markets and gaps can slip through the intended level.
- A skill alone is passive. If the user wants hourly stop checks or push-style reminders, pair the skill with an automation or scheduler.
- Do not hide uncertainty. Missing fields should remain missing.
- Avoid illiquid names by default. The user must opt in if they want lottery-ticket or micro-cap ideas.

## Daily Scan Process

When the user asks for a daily or weekly scan:

1. Use `scripts/build_stock_snapshot.py` with the default `offensive` profile unless the user explicitly asks for a calmer one.
2. Check the `market_environment` section in the output to determine the current regime.
3. Filter out names that fail basic tradability rules unless the user explicitly wants ultra-high risk.
4. Rank candidates with the scoring model from `references/rules-and-scoring.md`.
5. Sort the final output into buckets rather than only `recommended buys`.

Use these buckets:

- `Aggressive Buy Candidate`
- `Pullback Watch`
- `Catalyst / Event Watch`
- `Dip Buy Candidate` (active only in bear/crisis regimes)
- `Manage Existing Position`
- `Avoid / No-Trade`

In bear or crisis regimes, the system automatically activates dip-buy scanning to find quality names sold off with the market. Do not reduce position sizes or retreat in these conditions — the user prefers contrarian entries.

If the user asks for only a few names, prefer quality over count.

## Position Management Process

When the user gives current holdings or fills:

1. Update the ledger with `scripts/portfolio_journal.py`.
2. If the user gives a stop, also update the stop-watch file with `scripts/stop_guard.py`.
3. Recalculate cost basis, realized P/L, unrealized P/L, and active position size.
4. For each active holding, answer four questions:
   - Is the trend still intact?
   - Did the thesis improve, stall, or break?
   - Is the stock near earnings or another major catalyst?
   - What action makes sense now: hold, add, trim, or exit?
5. If the position is extended above the buy zone, do not tell the user to chase it. Switch to hold or trim language.
6. If price breaks the invalidation level on heavy volume, prefer trim or exit over hoping.

## Risk Monitoring Process

When the user says `I bought XXX`, `my stop is YYY`, `watch this position`, or asks for stop reminders:

1. Update the ledger with the fill.
2. Update the stop-watch file with ticker, shares, entry, stop, and thesis.
3. Use `scripts/stop_guard.py check` to classify each active position as:
   - `ok`
   - `near_stop`
   - `stop_breached`
4. If the user wants recurring checks, explain that the skill should be paired with an hourly automation.
5. If a stop is breached, lead with the alert first and keep the message short and actionable.

## Recommendation Tracking Process

When the system outputs actionable ideas:

1. Log each recommendation using `scripts/backtest_journal.py log` with the ticker, score, bucket, setup, entry reference, stop, trim target, and current market regime.
2. Periodically run `scripts/backtest_journal.py evaluate` (e.g., weekly) to check what happened to past recommendations after N trading days.
3. Run `scripts/backtest_journal.py report` to see accuracy by bucket, setup type, score band, and market regime.
4. Use the report to discuss scoring weight adjustments with the user. Do not auto-change weights — treat report findings as evidence for a conversation.

## Daily Review Process

When the user wants the agent to learn and improve:

1. Keep a daily review file based on `assets/daily-trading-review-template.md`.
2. Update it after the trading day, not every intraday wiggle.
3. Capture process quality, risk control, and rule adherence before P/L vanity metrics.
4. Treat new lessons as observations first. Do not turn a single day's emotion into a permanent rule.

## Output Discipline

Always use the structure in `references/output-template.md`.

At minimum, every actionable idea must include:

- ticker and company name
- last price and as-of date
- score and bucket
- why it ranked here
- setup type
- preferred entry trigger or buy zone
- stop or invalidation
- first trim level and next management rule
- catalyst window
- main reasons to skip the trade
- source list

## If the user asks for extreme returns

Do not encode magical targets into the answer.
Instead:

- say the goal is highly speculative and could lead to large losses
- keep the scan focused on high-beta momentum and catalyst names
- reduce size around binary events even in offensive mode
- present the trade as a scenario, not a forecast

## Notes For Future Iteration

This skill is intentionally rules-based and data-first.
If you later notice repeated manual work, extend the scripts before expanding the prompt.
