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

## How to reason over the ledger

When active positions exist, answer these in order:

1. What is the current average cost?
2. What is the unrealized gain or loss?
3. Is the position above or below the intended trend support?
4. Is there a major event close enough that the sizing should be reduced?
5. Is the user already too concentrated in one theme or ticker?

## Memory rule

The ledger is the durable memory, not the chat transcript.
When the user supplies a new fill, update the ledger first, then discuss the position.

## Reporting rule

When showing portfolio state, separate:

- realized P/L
- unrealized P/L
- current market value
- next management action

Do not merge everything into one emotional summary.

