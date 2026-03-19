#!/usr/bin/env python3
"""Record scoring recommendations and evaluate outcomes to validate the model."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("curl_cffi").setLevel(logging.CRITICAL)

COLUMNS = [
    "rec_date",
    "ticker",
    "score",
    "bucket",
    "setup",
    "profile",
    "entry_reference",
    "stop",
    "trim_1",
    "market_regime",
    "note",
]

EVAL_COLUMNS = [
    "rec_date",
    "ticker",
    "score",
    "bucket",
    "setup",
    "profile",
    "entry_reference",
    "stop",
    "trim_1",
    "horizon_days",
    "price_at_horizon",
    "return_at_horizon_pct",
    "mfe_pct",
    "mae_pct",
    "hit_trim",
    "hit_stop",
    "direction_correct",
    "eval_date",
]

SCORE_BANDS = [
    ("76-100", 76, 100),
    ("62-75", 62, 75),
    ("48-61", 48, 61),
    ("0-47", 0, 47),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a recommendation journal CSV")
    init_parser.add_argument("--file", required=True)

    log_parser = subparsers.add_parser("log", help="Append a recommendation record")
    log_parser.add_argument("--file", required=True)
    log_parser.add_argument("--ticker", required=True)
    log_parser.add_argument("--score", required=True, type=float)
    log_parser.add_argument("--bucket", required=True)
    log_parser.add_argument("--setup", required=True)
    log_parser.add_argument("--entry-reference", required=True, type=float)
    log_parser.add_argument("--stop", required=True, type=float)
    log_parser.add_argument("--trim-1", required=True, type=float)
    log_parser.add_argument("--profile", default="offensive")
    log_parser.add_argument("--market-regime", default="")
    log_parser.add_argument("--note", default="")

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate outcomes for mature recommendations")
    eval_parser.add_argument("--file", required=True)
    eval_parser.add_argument("--horizon", type=int, default=10)
    eval_parser.add_argument("--out")

    report_parser = subparsers.add_parser("report", help="Aggregate evaluation results")
    report_parser.add_argument("--file", required=True)
    report_parser.add_argument("--out")

    return parser.parse_args()


def init_journal(path: Path) -> dict[str, Any]:
    if path.exists():
        raise SystemExit(f"Journal already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=COLUMNS).to_csv(path, index=False)
    return {"status": "created", "file": str(path)}


def load_journal(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Journal not found: {path}")
    frame = pd.read_csv(path)
    if frame.empty:
        return pd.DataFrame(columns=COLUMNS)
    for column in COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    frame["rec_date"] = pd.to_datetime(frame["rec_date"], errors="coerce")
    frame["ticker"] = frame["ticker"].astype(str).str.upper()
    frame["score"] = pd.to_numeric(frame["score"], errors="coerce").fillna(0.0)
    for field in ["entry_reference", "stop", "trim_1"]:
        frame[field] = pd.to_numeric(frame[field], errors="coerce")
    frame["bucket"] = frame["bucket"].fillna("")
    frame["setup"] = frame["setup"].fillna("")
    frame["profile"] = frame["profile"].fillna("offensive")
    frame["market_regime"] = frame["market_regime"].fillna("")
    frame["note"] = frame["note"].fillna("")
    return frame[COLUMNS].sort_values(["rec_date", "ticker"], kind="stable")


def append_recommendation(path: Path, args: argparse.Namespace) -> dict[str, Any]:
    frame = load_journal(path) if path.exists() else pd.DataFrame(columns=COLUMNS)
    record = {
        "rec_date": date.today().isoformat(),
        "ticker": args.ticker.upper(),
        "score": float(args.score),
        "bucket": args.bucket,
        "setup": args.setup,
        "profile": args.profile,
        "entry_reference": float(args.entry_reference),
        "stop": float(args.stop),
        "trim_1": float(args.trim_1),
        "market_regime": args.market_regime,
        "note": args.note,
    }
    updated = pd.concat([frame, pd.DataFrame([record])], ignore_index=True)
    updated.to_csv(path, index=False)
    return {"status": "appended", "recommendation": record, "file": str(path)}


def eval_path_for(journal_path: Path) -> Path:
    return journal_path.with_name(f"{journal_path.stem}_eval.csv")


def load_eval(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=EVAL_COLUMNS)
    frame = pd.read_csv(path)
    if frame.empty:
        return pd.DataFrame(columns=EVAL_COLUMNS)
    return frame


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


def evaluate_recommendations(
    journal_path: Path, horizon: int,
) -> dict[str, Any]:
    journal = load_journal(journal_path)
    if journal.empty:
        return {"status": "empty", "evaluated": 0, "skipped": 0}

    ep = eval_path_for(journal_path)
    existing_eval = load_eval(ep)

    # Build set of already-evaluated (ticker, rec_date) combos
    evaluated_keys: set[tuple[str, str]] = set()
    if not existing_eval.empty:
        for row in existing_eval.itertuples(index=False):
            evaluated_keys.add((str(row.ticker), str(row.rec_date)))

    # Filter to recommendations old enough and not yet evaluated
    today = pd.Timestamp(date.today())
    candidates = []
    for row in journal.itertuples(index=False):
        rec_dt = pd.Timestamp(row.rec_date)
        if pd.isna(rec_dt):
            continue
        # Need at least horizon calendar days to have passed (rough filter)
        if (today - rec_dt).days < horizon:
            continue
        key = (str(row.ticker), str(rec_dt.date()))
        if key in evaluated_keys:
            continue
        candidates.append(row)

    if not candidates:
        return {"status": "nothing_to_evaluate", "evaluated": 0, "skipped": 0}

    # Group tickers and determine date ranges for batch download
    ticker_dates: dict[str, list[Any]] = {}
    for row in candidates:
        ticker = str(row.ticker)
        ticker_dates.setdefault(ticker, []).append(row)

    # Batch download: find earliest rec_date and latest needed end date
    all_tickers = list(ticker_dates.keys())
    earliest = min(pd.Timestamp(r.rec_date) for r in candidates)
    buffer_days = horizon + 25  # generous buffer for weekends/holidays
    start_date = (earliest - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    data = yf.download(
        all_tickers,
        start=start_date,
        end=end_date,
        interval="1d",
        auto_adjust=False,
        group_by="ticker",
        progress=False,
    )

    results = []
    skipped = 0

    for row in candidates:
        ticker = str(row.ticker)
        rec_dt = pd.Timestamp(row.rec_date)
        entry_ref = float(row.entry_reference)
        stop_price = float(row.stop)
        trim_price = float(row.trim_1)

        frame = extract_frame(data, ticker)
        if frame.empty:
            skipped += 1
            continue

        # Get trading days after rec_date
        mask = frame.index > rec_dt
        future = frame.loc[mask]

        if len(future) < horizon:
            skipped += 1
            continue

        window = future.iloc[:horizon]
        horizon_row = future.iloc[horizon - 1]

        price_at_horizon = float(horizon_row["Close"])
        return_at_horizon_pct = round((price_at_horizon - entry_ref) / entry_ref * 100, 4)

        highs = window["High"]
        lows = window["Low"]
        max_high = float(highs.max())
        min_low = float(lows.min())

        mfe_pct = round((max_high - entry_ref) / entry_ref * 100, 4)
        mae_pct = round((entry_ref - min_low) / entry_ref * 100, 4)
        hit_trim = bool(max_high >= trim_price)
        hit_stop = bool(min_low <= stop_price)
        direction_correct = bool(price_at_horizon > entry_ref)

        results.append({
            "rec_date": str(rec_dt.date()),
            "ticker": ticker,
            "score": float(row.score),
            "bucket": str(row.bucket),
            "setup": str(row.setup),
            "profile": str(row.profile),
            "entry_reference": entry_ref,
            "stop": stop_price,
            "trim_1": trim_price,
            "horizon_days": horizon,
            "price_at_horizon": round(price_at_horizon, 4),
            "return_at_horizon_pct": return_at_horizon_pct,
            "mfe_pct": mfe_pct,
            "mae_pct": mae_pct,
            "hit_trim": hit_trim,
            "hit_stop": hit_stop,
            "direction_correct": direction_correct,
            "eval_date": date.today().isoformat(),
        })

    # Append new results to eval CSV
    if results:
        new_eval = pd.DataFrame(results)
        combined = pd.concat([existing_eval, new_eval], ignore_index=True)
        ep.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(ep, index=False)

    return {
        "status": "evaluated",
        "evaluated": len(results),
        "skipped": skipped,
        "eval_file": str(ep),
    }


def score_band(score: float) -> str:
    for label, lo, hi in SCORE_BANDS:
        if lo <= score <= hi:
            return label
    return "unknown"


def group_stats(group: pd.DataFrame) -> dict[str, Any]:
    count = len(group)
    if count == 0:
        return {
            "count": 0,
            "avg_return_pct": 0,
            "direction_accuracy": 0,
            "trim_hit_rate": 0,
            "stop_hit_rate": 0,
            "avg_mfe_pct": 0,
            "avg_mae_pct": 0,
        }
    return {
        "count": count,
        "avg_return_pct": round(float(group["return_at_horizon_pct"].mean()), 2),
        "direction_accuracy": round(float(group["direction_correct"].mean()) * 100, 2),
        "trim_hit_rate": round(float(group["hit_trim"].mean()) * 100, 2),
        "stop_hit_rate": round(float(group["hit_stop"].mean()) * 100, 2),
        "avg_mfe_pct": round(float(group["mfe_pct"].mean()), 2),
        "avg_mae_pct": round(float(group["mae_pct"].mean()), 2),
    }


def generate_report(journal_path: Path) -> dict[str, Any]:
    ep = eval_path_for(journal_path)
    evals = load_eval(ep)
    if evals.empty:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_evaluated": 0,
            "by_bucket": {},
            "by_setup": {},
            "by_score_band": {},
            "by_regime": {},
            "suggestions": [],
        }

    # Ensure numeric types
    for field in ["return_at_horizon_pct", "mfe_pct", "mae_pct", "score"]:
        evals[field] = pd.to_numeric(evals[field], errors="coerce").fillna(0.0)
    evals["direction_correct"] = evals["direction_correct"].astype(bool)
    evals["hit_trim"] = evals["hit_trim"].astype(bool)
    evals["hit_stop"] = evals["hit_stop"].astype(bool)
    evals["score_band"] = evals["score"].apply(score_band)

    by_bucket: dict[str, Any] = {}
    for bucket, group in evals.groupby("bucket"):
        by_bucket[str(bucket)] = group_stats(group)

    by_setup: dict[str, Any] = {}
    for setup, group in evals.groupby("setup"):
        by_setup[str(setup)] = group_stats(group)

    by_score_band: dict[str, Any] = {}
    for band, group in evals.groupby("score_band"):
        by_score_band[str(band)] = group_stats(group)

    by_regime: dict[str, Any] = {}
    # Load journal to get market_regime for each rec
    journal = load_journal(journal_path)
    if not journal.empty:
        regime_map = {}
        for row in journal.itertuples(index=False):
            key = (str(row.ticker), str(pd.Timestamp(row.rec_date).date()))
            regime_map[key] = str(row.market_regime)
        regimes = []
        for row in evals.itertuples(index=False):
            key = (str(row.ticker), str(row.rec_date))
            regimes.append(regime_map.get(key, ""))
        evals["market_regime"] = regimes
    else:
        evals["market_regime"] = ""

    for regime, group in evals.groupby("market_regime"):
        if str(regime):
            by_regime[str(regime)] = group_stats(group)

    # Generate suggestions
    suggestions: list[str] = []

    for bucket, stats in by_bucket.items():
        if stats["count"] > 0 and stats["direction_accuracy"] < 50:
            suggestions.append(
                f"Bucket '{bucket}' direction accuracy is {stats['direction_accuracy']}%"
                " — consider tightening threshold"
            )

    for setup, stats in by_setup.items():
        if stats["count"] > 0 and stats["trim_hit_rate"] < 25:
            suggestions.append(
                f"Setup '{setup}' trim hit rate is {stats['trim_hit_rate']}%"
                " — trim target may be too aggressive"
            )
        if stats["count"] > 0 and stats["stop_hit_rate"] > 60:
            suggestions.append(
                f"Setup '{setup}' stop hit rate is {stats['stop_hit_rate']}%"
                " — stops may be too tight"
            )

    # Regime+bucket combos
    if not evals.empty and "market_regime" in evals.columns:
        for (regime, bucket), group in evals.groupby(["market_regime", "bucket"]):
            if not str(regime):
                continue
            stats = group_stats(group)
            if stats["count"] > 0 and stats["direction_accuracy"] > 60:
                suggestions.append(
                    f"Bucket '{bucket}' in regime '{regime}' has"
                    f" {stats['direction_accuracy']}% direction accuracy"
                    " — this pattern works"
                )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_evaluated": len(evals),
        "by_bucket": by_bucket,
        "by_setup": by_setup,
        "by_score_band": by_score_band,
        "by_regime": by_regime,
        "suggestions": suggestions,
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
        emit(init_journal(path), None)
        return
    if args.command == "log":
        emit(append_recommendation(path, args), None)
        return
    if args.command == "evaluate":
        emit(evaluate_recommendations(path, args.horizon), args.out)
        return
    if args.command == "report":
        emit(generate_report(path), args.out)
        return


if __name__ == "__main__":
    main()
