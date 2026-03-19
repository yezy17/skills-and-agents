---
name: us-stock-research-desk
description: Research and manage U.S. equity swing-trade ideas, daily watchlists, catalyst calendars, and existing holdings using public market data plus SEC filings. Use whenever the user asks for 美股 or US stocks ideas, daily scans, watchlist ranking, breakout or pullback entries, earnings or 8-K catalyst review, analyst-rating changes, risk flags, or wants OpenClaw to remember positions and turn them into entry, trim, hold, or exit plans.
---

# US Stock Research Desk

## Overview

Use this skill to turn public U.S. equity data into a daily action plan instead of vague market commentary.
Prioritize fresh dates, explicit rules, scenario-based entries and exits, and risk labels that make uncertainty obvious.

## Workflow

### 1. Choose the mode

Classify the user request into one of four modes:

- `daily-scan`: build a ranked idea list from public screens or a watchlist
- `watchlist-review`: score a user-provided ticker list and update the action plan
- `portfolio-review`: update holdings, assess position health, and suggest hold/trim/exit logic
- `single-name-dive`: dig into one stock with more filing and event context

### 2. Load only the references you need

- Read `references/data-sources.md` before deciding which data source to trust.
- Read `references/rules-and-scoring.md` when you need the scoring rubric, setup definitions, or position-sizing rules.
- Read `references/output-template.md` before drafting the final answer.
- Read `references/portfolio-workflow.md` only when the user gives holdings, fills, or asks you to remember positions.

### 3. Use the helper scripts when possible

- Run `scripts/build_stock_snapshot.py` for latest price, trend, volume, fundamentals, catalyst, SEC filing, and risk snapshot data.
- Run `scripts/portfolio_journal.py` to initialize, update, or summarize a transaction ledger.
- If a script fails because dependencies are missing, say so briefly and fall back to a manual workflow instead of hallucinating values.

### 4. Cross-check freshness before recommending anything

Always state the as-of date for price data and the date of the latest catalyst you cite.
If the market data is stale, missing, or contradictory, say so and downgrade confidence.

## Hard Rules

- Use official or primary sources for filings and corporate events whenever available.
- Treat free market-data wrappers as convenient but imperfect; mention caveats when the source is unofficial or personal-use only.
- Never promise that a stock will double or return 50 percent in one or two weeks.
- If the user asks for very aggressive growth, still respond with defined-risk setups, invalidation levels, and smaller event sizes.
- Never output a naked `buy this now` line. Always include setup type, entry logic, stop or invalidation, first trim level, and key risk flags.
- Do not hide uncertainty. Missing fields should remain missing.
- Avoid illiquid names by default. The user must opt in if they want lottery-ticket or micro-cap ideas.

## Daily Scan Process

When the user asks for a daily or weekly scan:

1. Use `scripts/build_stock_snapshot.py` with either the user watchlist or the default screen presets.
2. Filter out names that fail basic tradability rules unless the user explicitly wants ultra-high risk.
3. Rank candidates with the scoring model from `references/rules-and-scoring.md`.
4. Sort the final output into buckets rather than only `recommended buys`.

Use these buckets:

- `Aggressive Buy Candidate`
- `Pullback Watch`
- `Catalyst / Event Watch`
- `Manage Existing Position`
- `Avoid / No-Trade`

If the user asks for only a few names, prefer quality over count.

## Position Management Process

When the user gives current holdings or fills:

1. Update the ledger with `scripts/portfolio_journal.py`.
2. Recalculate cost basis, realized P/L, unrealized P/L, and active position size.
3. For each active holding, answer four questions:
   - Is the trend still intact?
   - Did the thesis improve, stall, or break?
   - Is the stock near earnings or another major catalyst?
   - What action makes sense now: hold, add, trim, or exit?
4. If the position is extended above the buy zone, do not tell the user to chase it. Switch to hold or trim language.
5. If price breaks the invalidation level on heavy volume, prefer trim or exit over hoping.

## Output Discipline

Always use the structure in `references/output-template.md`.

At minimum, every actionable idea must include:

- ticker and company name
- last price and as-of date
- score and bucket
- why it ranked here
- setup type
- preferred entry trigger or buy zone
- stop / invalidation
- first trim level and next management rule
- catalyst window
- main reasons to skip the trade
- source list

## If the user asks for extreme returns

Do not encode magical targets into the answer.
Instead:

- say the goal is highly speculative and could lead to large losses
- keep the scan focused on high-beta momentum and catalyst names
- reduce size around binary events
- present the trade as a scenario, not a forecast

## Notes For Future Iteration

This skill is intentionally rules-based and data-first.
If you later notice repeated manual work, extend the scripts before expanding the prompt.

