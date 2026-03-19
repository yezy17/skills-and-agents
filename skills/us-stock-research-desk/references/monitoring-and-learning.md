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
