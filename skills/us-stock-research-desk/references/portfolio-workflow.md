# Portfolio Workflow

## Use case

Use this workflow when the user gives fills, current holdings, or asks OpenClaw to remember their positions.

## Ledger format

The helper script writes a transaction ledger CSV with these columns:

- `date`
- `ticker`
- `side`
- `shares`
- `price`
- `fees`
- `note`

A blank template lives at `assets/portfolio-ledger-template.csv`.

For stop monitoring, keep a separate file based on `assets/stop-watch-template.csv`.

## Minimal workflow

### Initialize a ledger

```powershell
python scripts/portfolio_journal.py init --file portfolio-ledger.csv
```

### Add a buy or sell

```powershell
python scripts/portfolio_journal.py trade --file portfolio-ledger.csv --ticker NVDA --side buy --shares 12 --price 180.40 --date 2026-03-18 --note "breakout starter"
```

### Summarize positions

```powershell
python scripts/portfolio_journal.py summary --file portfolio-ledger.csv
```

### Add or update a stop

```powershell
python scripts/stop_guard.py upsert --file stop-watch.csv --ticker NVDA --shares 12 --entry-price 180.40 --stop-price 171.00 --thesis "post-breakout swing"
```

### Check stops

```powershell
python scripts/stop_guard.py check --file stop-watch.csv
```

## How to reason over the ledger

When active positions exist, answer these in order:

1. What is the current average cost?
2. What is the unrealized gain or loss?
3. Is the position above or below the intended trend support?
4. Is there a major event close enough that the sizing should be reduced?
5. Is the user already too concentrated in one theme or ticker?
6. Is the position near the warning line or through the stop line?

## Memory rule

The ledger is the durable memory, not the chat transcript.
When the user supplies a new fill, update the ledger first, then discuss the position.
When the user supplies or changes a stop, update the stop-watch file in the same turn.

## Backtest commands

### Initialize a recommendation journal

```powershell
python scripts/backtest_journal.py init --file recommendations.csv
```

### Log a recommendation

```powershell
python scripts/backtest_journal.py log --file recommendations.csv --ticker NVDA --score 82 --bucket "Aggressive Buy Candidate" --setup breakout --entry-reference 180.40 --stop 171.00 --trim-1 189.80 --market-regime bull --note "post-breakout swing"
```

### Evaluate past recommendations

```powershell
python scripts/backtest_journal.py evaluate --file recommendations.csv --horizon 10
```

### Generate accuracy report

```powershell
python scripts/backtest_journal.py report --file recommendations.csv
```

## Reporting rule

When showing portfolio state, separate:

- realized P/L
- unrealized P/L
- current market value
- next management action

Do not merge everything into one emotional summary.

