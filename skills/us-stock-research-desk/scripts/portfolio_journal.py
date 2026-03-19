#!/usr/bin/env python3
"""Maintain a simple trade ledger and summarize active positions."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

COLUMNS = ["date", "ticker", "side", "shares", "price", "fees", "note"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a new ledger CSV")
    init_parser.add_argument("--file", required=True)

    trade_parser = subparsers.add_parser("trade", help="Append a buy or sell to the ledger")
    trade_parser.add_argument("--file", required=True)
    trade_parser.add_argument("--ticker", required=True)
    trade_parser.add_argument("--side", required=True, choices=["buy", "sell"])
    trade_parser.add_argument("--shares", required=True, type=float)
    trade_parser.add_argument("--price", required=True, type=float)
    trade_parser.add_argument("--fees", type=float, default=0.0)
    trade_parser.add_argument("--date", dest="trade_date", default=date.today().isoformat())
    trade_parser.add_argument("--note", default="")

    summary_parser = subparsers.add_parser("summary", help="Summarize realized and unrealized P/L")
    summary_parser.add_argument("--file", required=True)
    summary_parser.add_argument("--out")

    return parser.parse_args()


def init_ledger(path: Path) -> dict[str, Any]:
    if path.exists():
        raise SystemExit(f"Ledger already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=COLUMNS).to_csv(path, index=False)
    return {"status": "created", "file": str(path)}


def load_ledger(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Ledger not found: {path}")
    frame = pd.read_csv(path)
    if frame.empty:
        return pd.DataFrame(columns=COLUMNS)
    for column in COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["ticker"] = frame["ticker"].astype(str).str.upper()
    frame["side"] = frame["side"].astype(str).str.lower()
    frame["shares"] = pd.to_numeric(frame["shares"], errors="coerce").fillna(0.0)
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce").fillna(0.0)
    frame["fees"] = pd.to_numeric(frame["fees"], errors="coerce").fillna(0.0)
    frame["note"] = frame["note"].fillna("")
    return frame[COLUMNS].sort_values(["date", "ticker"], kind="stable")


def append_trade(path: Path, args: argparse.Namespace) -> dict[str, Any]:
    frame = load_ledger(path) if path.exists() else pd.DataFrame(columns=COLUMNS)
    record = {
        "date": pd.to_datetime(args.trade_date, errors="raise").date().isoformat(),
        "ticker": args.ticker.upper(),
        "side": args.side,
        "shares": float(args.shares),
        "price": float(args.price),
        "fees": float(args.fees),
        "note": args.note,
    }
    updated = pd.concat([frame, pd.DataFrame([record])], ignore_index=True)
    updated.to_csv(path, index=False)
    return {"status": "appended", "trade": record, "file": str(path)}


def extract_frame(history: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame()
    if isinstance(history.columns, pd.MultiIndex):
        top = list(history.columns.get_level_values(0).unique())
        if symbol in top:
            frame = history[symbol].copy()
        else:
            frame = pd.DataFrame()
    else:
        frame = history.copy()
    return frame.dropna(how="all")


def current_prices(tickers: list[str]) -> dict[str, float | None]:
    if not tickers:
        return {}
    data = yf.download(
        tickers,
        period="5d",
        interval="1d",
        auto_adjust=False,
        group_by="ticker",
        progress=False,
    )
    prices: dict[str, float | None] = {}
    for ticker in tickers:
        frame = extract_frame(data, ticker)
        if frame.empty:
            prices[ticker] = None
            continue
        series = frame.get("Close")
        if series is None or series.dropna().empty:
            series = frame.get("Adj Close")
        prices[ticker] = float(series.dropna().iloc[-1]) if series is not None and not series.dropna().empty else None
    return prices


def summarize_positions(frame: pd.DataFrame) -> dict[str, Any]:
    positions: dict[str, dict[str, Any]] = {}
    realized_total = 0.0

    for trade in frame.sort_values(["date", "ticker"], kind="stable").itertuples(index=False):
        ticker = trade.ticker
        side = trade.side
        shares = float(trade.shares)
        price = float(trade.price)
        fees = float(trade.fees)

        book = positions.setdefault(
            ticker,
            {
                "ticker": ticker,
                "shares": 0.0,
                "cost_basis_total": 0.0,
                "realized_pnl": 0.0,
                "last_trade_date": None,
                "last_note": "",
            },
        )

        if side == "buy":
            book["cost_basis_total"] += shares * price + fees
            book["shares"] += shares
        elif side == "sell":
            avg_cost = (book["cost_basis_total"] / book["shares"]) if book["shares"] > 0 else 0.0
            realized = shares * (price - avg_cost) - fees
            book["realized_pnl"] += realized
            realized_total += realized
            book["cost_basis_total"] -= avg_cost * shares
            book["shares"] -= shares
            if book["shares"] < 0:
                book["shares"] = 0.0
                book["cost_basis_total"] = 0.0
        book["last_trade_date"] = trade.date.date().isoformat() if pd.notna(trade.date) else None
        book["last_note"] = trade.note

    active_tickers = [ticker for ticker, book in positions.items() if book["shares"] > 0]
    marks = current_prices(active_tickers)

    results = []
    for ticker, book in sorted(positions.items()):
        shares = float(book["shares"])
        avg_cost = (book["cost_basis_total"] / shares) if shares > 0 else 0.0
        current_price = marks.get(ticker)
        market_value = shares * current_price if shares > 0 and current_price is not None else None
        unrealized = market_value - book["cost_basis_total"] if market_value is not None else None
        results.append(
            {
                "ticker": ticker,
                "shares": round(shares, 4),
                "avg_cost": round(avg_cost, 4) if shares > 0 else None,
                "current_price": round(current_price, 4) if current_price is not None else None,
                "market_value": round(market_value, 2) if market_value is not None else None,
                "unrealized_pnl": round(unrealized, 2) if unrealized is not None else None,
                "realized_pnl": round(book["realized_pnl"], 2),
                "last_trade_date": book["last_trade_date"],
                "last_note": book["last_note"],
                "status": "open" if shares > 0 else "closed",
            }
        )

    total_market_value = sum(item["market_value"] for item in results if item["market_value"] is not None)
    total_unrealized = sum(item["unrealized_pnl"] for item in results if item["unrealized_pnl"] is not None)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "positions": results,
        "totals": {
            "active_positions": sum(1 for item in results if item["status"] == "open"),
            "realized_pnl": round(realized_total, 2),
            "unrealized_pnl": round(total_unrealized, 2),
            "market_value": round(total_market_value, 2),
        },
    }


def emit(payload: dict[str, Any], out_path: str | None) -> None:
    text = json.dumps(payload, indent=2, default=str)
    if out_path:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    print(text)


def main() -> None:
    args = parse_args()
    path = Path(getattr(args, "file")).resolve()

    if args.command == "init":
        emit(init_ledger(path), None)
        return
    if args.command == "trade":
        emit(append_trade(path, args), None)
        return
    if args.command == "summary":
        frame = load_ledger(path)
        emit(summarize_positions(frame), args.out)
        return


if __name__ == "__main__":
    main()

