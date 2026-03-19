# Monitoring and Learning

## Screenshot takeaway

The screenshot is directionally right but too absolute.

What is worth keeping:

- risk control matters more than finding a magical entry style
- stop-loss discipline is often shared across otherwise very different traders
- position sizing should be tied to account risk, not just conviction
- ATR-aware sizing is useful because volatility changes the real risk of each trade

What should be corrected:

- `1-2% account risk per trade` is a reasonable default for a swing trader, but `5%` is already very aggressive for a small account
- stop losses are not perfect protection because gaps and fast markets can skip the intended level
- a stop is not the same thing as guaranteed execution; alerts and broker-side order choices still matter

## Recommended default risk budget for this skill

- normal swing idea: `0.75% to 1.50%` account risk
- aggressive catalyst idea: `0.25% to 0.75%`
- hard ceiling: avoid going above `2%` account risk on a single position

With a `10,000 USD` account, that means:

- normal swing risk budget: roughly `75 to 150 USD`
- catalyst risk budget: roughly `25 to 75 USD`
- do not let one bad trade cost `500 USD` unless the user explicitly overrides the guardrail

## Stop monitoring workflow

Use `scripts/stop_guard.py` with a durable CSV file instead of relying on chat memory.

Suggested fields:

- ticker
- shares
- entry price
- stop price
- warning price
- status
- thesis
- note

Rules:

- if the user says `I bought XXX and my stop is YYY`, update both the portfolio ledger and the stop-watch file
- default warning price can sit about `1%` above the stop
- treat `near stop` as a review signal, not an automatic panic signal
- treat `stop breached` as an action signal unless the user explicitly uses end-of-day stops only

## Daily learning loop

Yes, keeping a daily review file is worthwhile, but do not let the agent rewrite the whole strategy from one day of data.

Daily notes should capture:

- what positions were added, trimmed, or closed
- whether the stop discipline was followed
- whether the trade fit the setup rules before entry
- what went right because of process
- what went wrong because of process
- one thing to repeat and one thing to stop doing

## Anti-overfitting rules

The agent may learn from the journal, but should only promote a change from `observation` to `rule` when:

- the same pattern repeats across multiple trades, or
- the issue persists for at least several weeks, or
- the user explicitly approves the rule change

Good journal use:

- noticing repeated mistakes
- noticing which setups are actually followed well
- tracking whether stops are too loose or too tight

Bad journal use:

- changing the whole strategy after one red day
- treating random noise as a new rule
- doubling risk after a short winning streak

## Backtest validation workflow

Use `scripts/backtest_journal.py` to verify whether the scoring system is actually predictive.

### The cycle

1. **Log**: after each scan, log actionable recommendations with `backtest_journal.py log`
2. **Evaluate**: after 10+ trading days, run `backtest_journal.py evaluate --horizon 10` to check what happened
3. **Report**: run `backtest_journal.py report` to see accuracy grouped by bucket, setup, score band, and market regime

### How to read the report

- `direction_accuracy`: what percentage of recommendations moved in the right direction within the horizon
- `trim_hit_rate`: what percentage reached the first trim target
- `stop_hit_rate`: what percentage hit the stop level
- `avg_mfe_pct / avg_mae_pct`: average best-case and worst-case excursion during the window

### What the suggestions mean

The report generates rule-based suggestions:

- direction accuracy below 50% for a bucket → that bucket threshold may be too loose
- trim hit rate below 25% → trim targets may be too aggressive
- stop hit rate above 60% → stops may be too tight
- high direction accuracy for a regime+bucket combo → that pattern is working

### Rules for acting on the report

- treat report findings as evidence for a discussion with the user, not as automatic rule changes
- do not adjust scoring weights without user approval
- wait for at least 20+ evaluated recommendations before drawing conclusions
- compare performance across different market regimes before changing anything
