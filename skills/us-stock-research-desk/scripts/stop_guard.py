#!/usr/bin/env python3
"""Maintain active stop levels and check for stop breaches."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

COLUMNS = [
    "ticker",
    "shares",
    "entry_price",
    "stop_price",
    "warning_price",
    "status",
    "thesis",
    "note",
    "updated_at",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a stop-watch CSV")
    init_parser.add_argument("--file", required=True)

    upsert_parser = subparsers.add_parser("upsert", help="Add or update a stop entry")
    upsert_parser.add_argument("--file", required=True)
    upsert_parser.add_argument("--ticker", required=True)
    upsert_parser.add_argument("--shares", required=True, type=float)
    upsert_parser.add_argument("--entry-price", required=True, type=float)
    upsert_parser.add_argument("--stop-price", required=True, type=float)
    upsert_parser.add_argument("--warning-price", type=float)
    upsert_parser.add_argument("--status", default="active", choices=["active", "paused", "closed"])
    upsert_parser.add_argument("--thesis", default="")
    upsert_parser.add_argument("--note", default="")

    check_parser = subparsers.add_parser("check", help="Check active positions against stop levels")
    check_parser.add_argument("--file", required=True)
    check_parser.add_argument("--warn-buffer-pct", type=float, default=1.0)
    check_parser.add_argument("--out")

    return parser.parse_args()


def init_book(path: Path) -> dict[str, Any]:
    if path.exists():
        raise SystemExit(f"Stop file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=COLUMNS).to_csv(path, index=False)
    return {"status": "created", "file": str(path)}


def load_book(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Stop file not found: {path}")
    frame = pd.read_csv(path)
    if frame.empty:
        return pd.DataFrame(columns=COLUMNS)
    for column in COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    frame["ticker"] = frame["ticker"].astype(str).str.upper()
    for field in ["shares", "entry_price", "stop_price", "warning_price"]:
        frame[field] = pd.to_numeric(frame[field], errors="coerce")
    frame["status"] = frame["status"].fillna("active").astype(str).str.lower()
    frame["thesis"] = frame["thesis"].fillna("")
    frame["note"] = frame["note"].fillna("")
    frame["updated_at"] = frame["updated_at"].fillna("")
    return frame[COLUMNS]


def upsert_entry(path: Path, args: argparse.Namespace) -> dict[str, Any]:
    frame = load_book(path) if path.exists() else pd.DataFrame(columns=COLUMNS)
    ticker = args.ticker.upper()
    warning_price = args.warning_price or (args.stop_price * 1.01)
    record = {
        "ticker": ticker,
        "shares": float(args.shares),
        "entry_price": float(args.entry_price),
        "stop_price": float(args.stop_price),
        "warning_price": float(warning_price),
        "status": args.status,
        "thesis": args.thesis,
        "note": args.note,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if ticker in frame["ticker"].values:
        frame.loc[frame["ticker"] == ticker, COLUMNS] = [record[column] for column in COLUMNS]
    else:
        frame = pd.concat([frame, pd.DataFrame([record])], ignore_index=True)

    frame.to_csv(path, index=False)
    return {"status": "upserted", "entry": record, "file": str(path)}


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


def check_stops(frame: pd.DataFrame, warn_buffer_pct: float) -> dict[str, Any]:
    active = frame.loc[frame["status"] == "active"].copy()
    tickers = active["ticker"].dropna().astype(str).str.upper().tolist()
    prices = current_prices(tickers)

    alerts = []
    for row in active.itertuples(index=False):
        current_price = prices.get(row.ticker)
        if current_price is None:
            status = "missing_price"
            distance_pct = None
        else:
            warning_price = row.warning_price if pd.notna(row.warning_price) else row.stop_price * (1 + warn_buffer_pct / 100)
            distance_pct = ((current_price - row.stop_price) / row.stop_price) * 100 if row.stop_price else None
            if current_price <= row.stop_price:
                status = "stop_breached"
            elif current_price <= warning_price:
                status = "near_stop"
            else:
                status = "ok"

        risk_per_share = max((row.entry_price - row.stop_price), 0) if pd.notna(row.entry_price) and pd.notna(row.stop_price) else None
        planned_risk = (risk_per_share * row.shares) if risk_per_share is not None else None
        alerts.append(
            {
                "ticker": row.ticker,
                "status": status,
                "shares": float(row.shares) if pd.notna(row.shares) else None,
                "entry_price": float(row.entry_price) if pd.notna(row.entry_price) else None,
                "current_price": current_price,
                "stop_price": float(row.stop_price) if pd.notna(row.stop_price) else None,
                "warning_price": float(row.warning_price) if pd.notna(row.warning_price) else None,
                "distance_to_stop_pct": round(distance_pct, 2) if distance_pct is not None else None,
                "planned_risk_usd": round(planned_risk, 2) if planned_risk is not None else None,
                "thesis": row.thesis,
                "note": row.note,
                "updated_at": row.updated_at,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "alerts": alerts,
        "summary": {
            "active_positions": len(alerts),
            "stop_breaches": sum(1 for item in alerts if item["status"] == "stop_breached"),
            "near_stop": sum(1 for item in alerts if item["status"] == "near_stop"),
            "ok": sum(1 for item in alerts if item["status"] == "ok"),
            "missing_price": sum(1 for item in alerts if item["status"] == "missing_price"),
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
        emit(init_book(path), None)
        return
    if args.command == "upsert":
        emit(upsert_entry(path, args), None)
        return
    if args.command == "check":
        emit(check_stops(load_book(path), args.warn_buffer_pct), args.out)
        return


if __name__ == "__main__":
    main()
