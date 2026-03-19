#!/usr/bin/env python3
"""Build a public-data snapshot for U.S. stock research and swing-trade scoring."""

from __future__ import annotations

import argparse
import json
import logging
import math
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yfinance as yf

PROFILE_SETTINGS = {
    "balanced": {
        "screens": ["growth_technology_stocks", "most_actives", "day_gainers"],
        "min_price": 5.0,
        "min_dollar_volume": 20_000_000.0,
        "breakout_volume_ratio": 1.5,
        "pullback_volume_ratio": 0.85,
    },
    "offensive": {
        "screens": ["day_gainers", "most_actives", "growth_technology_stocks"],
        "min_price": 3.0,
        "min_dollar_volume": 15_000_000.0,
        "breakout_volume_ratio": 1.3,
        "pullback_volume_ratio": 0.90,
    },
}
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
DEFAULT_USER_AGENT = "US Stock Research Desk openclaw@example.com"

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("curl_cffi").setLevel(logging.CRITICAL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        default="offensive",
        choices=sorted(PROFILE_SETTINGS.keys()),
        help="Research profile. Defaults to the offensive profile.",
    )
    parser.add_argument("--tickers", help="Comma-separated tickers to analyze")
    parser.add_argument(
        "--screen",
        action="append",
        dest="screens",
        help="Predefined yfinance screen. Repeatable. Defaults to a built-in high-beta mix.",
    )
    parser.add_argument("--count", type=int, default=8, help="Per-screen candidate count")
    parser.add_argument("--benchmark", default="SPY", help="Relative-strength benchmark")
    parser.add_argument("--account-size", type=float, default=10_000.0)
    parser.add_argument("--min-price", type=float, default=None)
    parser.add_argument("--min-dollar-volume", type=float, default=None)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--out", help="Write JSON output to this file")
    return parser.parse_args()


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def clean_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def round_or_none(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def serialize(value: Any) -> Any:
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def parse_ticker_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    tickers = []
    for item in raw.split(","):
        symbol = item.strip().upper()
        if symbol and symbol not in tickers:
            tickers.append(symbol)
    return tickers


def fetch_screen_quotes(screen_name: str, count: int) -> list[dict[str, Any]]:
    result = yf.screen(screen_name, count=count)
    quotes = result.get("quotes", []) if isinstance(result, dict) else []
    return [quote for quote in quotes if quote.get("symbol")]


def build_universe(
    tickers: list[str], screens: list[str], count: int
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    if tickers:
        return tickers, {}

    seed_quotes: dict[str, dict[str, Any]] = {}
    for screen in screens:
        try:
            quotes = fetch_screen_quotes(screen, count)
        except Exception as exc:
            print(f"[warn] failed to load screen {screen}: {exc}")
            continue
        for quote in quotes:
            symbol = quote.get("symbol", "").upper()
            if not symbol:
                continue
            quote.setdefault("seedScreens", [])
            if screen not in quote["seedScreens"]:
                quote["seedScreens"].append(screen)
            if symbol in seed_quotes:
                existing = seed_quotes[symbol]
                existing.setdefault("seedScreens", [])
                for seed in quote["seedScreens"]:
                    if seed not in existing["seedScreens"]:
                        existing["seedScreens"].append(seed)
                for key, value in quote.items():
                    existing.setdefault(key, value)
            else:
                seed_quotes[symbol] = quote
    return sorted(seed_quotes.keys()), seed_quotes


def download_history(symbols: list[str], benchmark: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    universe = symbols + ([benchmark] if benchmark not in symbols else [])
    history = yf.download(
        universe,
        period="1y",
        interval="1d",
        auto_adjust=False,
        group_by="ticker",
        progress=False,
        threads=True,
    )
    benchmark_history = extract_history_frame(history, benchmark)
    return history, benchmark_history


def extract_history_frame(history: pd.DataFrame, symbol: str) -> pd.DataFrame:
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

    if frame.empty:
        return frame
    return frame.dropna(how="all")


def compute_benchmark_returns(benchmark_history: pd.DataFrame) -> tuple[float | None, float | None]:
    if benchmark_history.empty:
        return None, None
    close = benchmark_history.get("Adj Close")
    if close is None or close.dropna().empty:
        close = benchmark_history.get("Close")
    if close is None or close.dropna().empty:
        return None, None
    close = close.dropna()
    ret_63 = close.iloc[-1] / close.iloc[-64] - 1 if len(close) >= 64 else None
    ret_126 = close.iloc[-1] / close.iloc[-127] - 1 if len(close) >= 127 else None
    return ret_63, ret_126


def compute_technical_frame(
    frame: pd.DataFrame,
    benchmark_returns: tuple[float | None, float | None],
    profile_settings: dict[str, Any],
) -> dict[str, Any]:
    if frame.empty:
        return {}

    close = frame.get("Adj Close")
    if close is None or close.dropna().empty:
        close = frame["Close"]
    raw_close = frame["Close"]
    high = frame["High"]
    low = frame["Low"]
    volume = frame["Volume"]

    ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None
    ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
    ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

    prev_close = raw_close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr14 = true_range.rolling(14).mean().iloc[-1] if len(true_range) >= 14 else None
    current_close = clean_float(raw_close.iloc[-1])
    atr_pct = (atr14 / current_close) if atr14 and current_close else None

    volume_avg20 = volume.rolling(20).mean().iloc[-1] if len(volume) >= 20 else None
    volume_ratio = (volume.iloc[-1] / volume_avg20) if volume_avg20 else None
    avg_dollar_volume20 = (raw_close * volume).rolling(20).mean().iloc[-1] if len(volume) >= 20 else None

    pivot20 = close.shift(1).rolling(20).max().iloc[-1] if len(close) >= 21 else None
    pivot55 = close.shift(1).rolling(55).max().iloc[-1] if len(close) >= 56 else None
    breakout_ratio = profile_settings["breakout_volume_ratio"]
    pullback_ratio = profile_settings["pullback_volume_ratio"]
    breakout20 = bool(current_close and pivot20 and current_close > pivot20 and (volume_ratio or 0) >= breakout_ratio)
    breakout55 = bool(current_close and pivot55 and current_close > pivot55 and (volume_ratio or 0) >= breakout_ratio)

    near_ma20 = bool(current_close and ma20 and abs(current_close - ma20) / current_close <= 0.03)
    near_ma50 = bool(current_close and ma50 and abs(current_close - ma50) / current_close <= 0.03)
    low_volume_pullback = bool(
        current_close
        and ma50
        and current_close > ma50
        and (near_ma20 or near_ma50)
        and (volume_ratio is not None and volume_ratio <= pullback_ratio)
    )

    ret_63 = close.iloc[-1] / close.iloc[-64] - 1 if len(close) >= 64 else None
    ret_126 = close.iloc[-1] / close.iloc[-127] - 1 if len(close) >= 127 else None
    bench_63, bench_126 = benchmark_returns
    rs_3m = (ret_63 - bench_63) if ret_63 is not None and bench_63 is not None else None
    rs_6m = (ret_126 - bench_126) if ret_126 is not None and bench_126 is not None else None

    rolling_high = close.rolling(min(252, len(close))).max().iloc[-1] if len(close) >= 2 else None
    drawdown_52w = (1 - close.iloc[-1] / rolling_high) if rolling_high else None
    daily_return = (raw_close.iloc[-1] / raw_close.iloc[-2] - 1) if len(raw_close) >= 2 else None
    ma200_slope = (ma200 - close.rolling(200).mean().iloc[-21]) if len(close) >= 220 else None

    return {
        "last_price": current_close,
        "last_volume": clean_float(volume.iloc[-1]),
        "ma20": clean_float(ma20),
        "ma50": clean_float(ma50),
        "ma200": clean_float(ma200),
        "atr14": clean_float(atr14),
        "atr_pct": clean_float(atr_pct),
        "volume_avg20": clean_float(volume_avg20),
        "volume_ratio": clean_float(volume_ratio),
        "avg_dollar_volume20": clean_float(avg_dollar_volume20),
        "pivot20": clean_float(pivot20),
        "pivot55": clean_float(pivot55),
        "breakout20": breakout20,
        "breakout55": breakout55,
        "low_volume_pullback": low_volume_pullback,
        "ret_3m": clean_float(ret_63),
        "ret_6m": clean_float(ret_126),
        "rs_3m": clean_float(rs_3m),
        "rs_6m": clean_float(rs_6m),
        "drawdown_52w": clean_float(drawdown_52w),
        "daily_return": clean_float(daily_return),
        "bullish_ma_stack": bool(current_close and ma20 and ma50 and ma200 and current_close > ma20 > ma50 > ma200),
        "ma200_slope": clean_float(ma200_slope),
        "history_rows": int(len(frame.index)),
        "last_price_date": frame.index[-1].date().isoformat(),
    }


def safe_info(symbol: str) -> dict[str, Any]:
    ticker = yf.Ticker(symbol)
    data: dict[str, Any] = {"symbol": symbol}

    try:
        data["fast_info"] = dict(ticker.fast_info)
    except Exception:
        data["fast_info"] = {}

    try:
        data["info"] = ticker.info or {}
    except Exception:
        data["info"] = {}

    try:
        data["calendar"] = ticker.calendar or {}
    except Exception:
        data["calendar"] = {}

    try:
        upgrades = ticker.get_upgrades_downgrades()
        data["upgrades"] = upgrades if isinstance(upgrades, pd.DataFrame) else pd.DataFrame()
    except Exception:
        data["upgrades"] = pd.DataFrame()

    return data


def extract_earnings_days(calendar: dict[str, Any], seed_quote: dict[str, Any]) -> tuple[str | None, int | None]:
    earnings_value = calendar.get("Earnings Date")
    earnings_date: date | None = None

    if isinstance(earnings_value, list) and earnings_value:
        first_value = earnings_value[0]
        if isinstance(first_value, date):
            earnings_date = first_value
    elif isinstance(earnings_value, date):
        earnings_date = earnings_value

    if earnings_date is None:
        raw_timestamp = seed_quote.get("earningsTimestamp") or seed_quote.get("earningsTimestampStart")
        if raw_timestamp:
            try:
                earnings_date = datetime.fromtimestamp(int(raw_timestamp), tz=timezone.utc).date()
            except (TypeError, ValueError, OSError):
                earnings_date = None

    if earnings_date is None:
        return None, None

    today = datetime.now(timezone.utc).date()
    return earnings_date.isoformat(), (earnings_date - today).days


def summarize_upgrades(upgrades: pd.DataFrame) -> tuple[int, int]:
    if upgrades is None or upgrades.empty:
        return 0, 0

    frame = upgrades.copy()
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame.loc[frame.index.notna()]
    if frame.empty:
        return 0, 0

    if getattr(frame.index, "tz", None):
        frame.index = frame.index.tz_convert(None)

    cutoff = pd.Timestamp.now("UTC").tz_localize(None) - pd.Timedelta(days=30)
    recent = frame.loc[frame.index >= cutoff]
    if recent.empty:
        return 0, 0

    to_grade = recent.get("ToGrade", pd.Series(dtype=object)).fillna("").str.lower()
    positive = int(to_grade.str.contains("buy|overweight|outperform|strong buy", regex=True).sum())
    negative = int(to_grade.str.contains("sell|underperform|underweight", regex=True).sum())
    return positive, negative


def load_sec_ticker_map(session: requests.Session) -> dict[str, int]:
    response = session.get(SEC_TICKERS_URL, timeout=30)
    response.raise_for_status()
    payload = response.json()
    mapping: dict[str, int] = {}
    for cik, _name, ticker, _exchange in payload.get("data", []):
        symbol = str(ticker).upper()
        if symbol and symbol not in mapping:
            mapping[symbol] = int(cik)
    return mapping


def fetch_sec_events(session: requests.Session, cik: int) -> list[dict[str, Any]]:
    padded = f"{cik:010d}"
    url = SEC_SUBMISSIONS_URL.format(cik=padded)
    response = session.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    recent = payload.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])
    items = recent.get("items", [])

    events: list[dict[str, Any]] = []
    for idx, form in enumerate(forms):
        if form not in {"8-K", "10-Q", "10-K", "DEF 14A"}:
            continue
        filing_date = filing_dates[idx] if idx < len(filing_dates) else None
        accession = accession_numbers[idx] if idx < len(accession_numbers) else None
        document = docs[idx] if idx < len(docs) else None
        item_text = items[idx] if idx < len(items) else None
        if not accession or not document:
            filing_url = None
        else:
            accession_nodash = accession.replace("-", "")
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_nodash}/{document}"
        events.append(
            {
                "form": form,
                "filing_date": filing_date,
                "items": item_text,
                "filing_url": filing_url,
            }
        )
    return events


def valuation_percentiles(rows: list[dict[str, Any]], field: str) -> dict[str, float | None]:
    valid = [(row["ticker"], clean_float(row.get(field))) for row in rows if clean_float(row.get(field)) is not None]
    if len(valid) < 2:
        return {ticker: None for ticker, _value in valid}
    series = pd.Series({ticker: value for ticker, value in valid})
    ranked = series.rank(pct=True, ascending=True)
    return {ticker: clean_float(percentile) for ticker, percentile in ranked.to_dict().items()}


def compute_scores(
    row: dict[str, Any],
    min_price: float,
    min_dollar_volume: float,
    profile: str,
) -> dict[str, Any]:
    price = clean_float(row.get("last_price"))
    ma20 = clean_float(row.get("ma20"))
    ma50 = clean_float(row.get("ma50"))
    ma200 = clean_float(row.get("ma200"))
    rs_3m = clean_float(row.get("rs_3m"))
    rs_6m = clean_float(row.get("rs_6m"))
    atr_pct = clean_float(row.get("atr_pct"))
    avg_dollar_vol20 = clean_float(row.get("avg_dollar_volume20"))
    drawdown = clean_float(row.get("drawdown_52w"))
    debt_to_equity = clean_float(row.get("debt_to_equity"))
    current_ratio = clean_float(row.get("current_ratio"))
    revenue_growth = clean_float(row.get("revenue_growth"))
    profit_margin = clean_float(row.get("profit_margin"))
    roe = clean_float(row.get("return_on_equity"))
    forward_pe_pct = clean_float(row.get("forward_pe_percentile"))
    days_to_earnings = row.get("days_to_earnings")

    trend = 0
    if price and ma20 and price > ma20:
        trend += 4
    if price and ma50 and price > ma50:
        trend += 5
    if price and ma200 and price > ma200:
        trend += 6
    if ma20 and ma50 and ma20 > ma50:
        trend += 5
    if ma50 and ma200 and ma50 > ma200:
        trend += 6
    if rs_3m is not None and rs_3m > 0:
        trend += 4
        if rs_3m > 0.10:
            trend += 2
    if rs_6m is not None and rs_6m > 0:
        trend += 3
    if clean_float(row.get("ma200_slope")) and clean_float(row.get("ma200_slope")) > 0:
        trend += 2
    trend = min(trend, 35)

    volume_ratio = clean_float(row.get("volume_ratio"))
    daily_return = clean_float(row.get("daily_return"))
    analyst_positive = int(row.get("analyst_positive_30d", 0) or 0)
    analyst_negative = int(row.get("analyst_negative_30d", 0) or 0)

    if profile == "offensive":
        price_volume = 0
        if row.get("breakout55"):
            price_volume += 20
        elif row.get("breakout20"):
            price_volume += 16
        elif row.get("low_volume_pullback"):
            price_volume += 11
        if volume_ratio is not None and daily_return is not None and daily_return > 0:
            if volume_ratio >= 1.8:
                price_volume += 5
            elif volume_ratio >= 1.3:
                price_volume += 3
        if atr_pct is not None:
            if 0.03 <= atr_pct <= 0.09:
                price_volume += 3
            elif atr_pct < 0.12:
                price_volume += 1
        if rs_3m is not None and rs_3m > 0.15:
            price_volume += 3
        price_volume = min(price_volume, 30)

        fundamentals = 0
        if revenue_growth is not None and revenue_growth > 0:
            fundamentals += 5
            if revenue_growth > 0.20:
                fundamentals += 3
        if profit_margin is not None and profit_margin > 0:
            fundamentals += 4
            if profit_margin > 0.12:
                fundamentals += 2
        if debt_to_equity is not None and debt_to_equity < 200:
            fundamentals += 2
        elif current_ratio is not None and current_ratio > 1.0:
            fundamentals += 2
        if forward_pe_pct is not None:
            if forward_pe_pct <= 0.50:
                fundamentals += 2
            elif forward_pe_pct <= 0.80:
                fundamentals += 1
        if roe is not None and roe > 0.10:
            fundamentals += 2
        fundamentals = min(fundamentals, 18)

        event = 0
        if analyst_positive > analyst_negative:
            event += 4
        if row.get("recent_sec_count", 0):
            event += 2
        if row.get("has_recent_8k"):
            event += 3
        if isinstance(days_to_earnings, int):
            if 3 <= days_to_earnings <= 14:
                event += 4
            elif 15 <= days_to_earnings <= 28:
                event += 2
        event = min(event, 15)

        risk = 0
        if isinstance(days_to_earnings, int):
            if days_to_earnings <= 2:
                risk -= 12
            elif days_to_earnings <= 5:
                risk -= 6
            elif days_to_earnings <= 10:
                risk -= 3
        if atr_pct is not None:
            if atr_pct >= 0.12:
                risk -= 8
            elif atr_pct >= 0.10:
                risk -= 5
            elif atr_pct >= 0.08:
                risk -= 2
        if avg_dollar_vol20 is not None:
            if avg_dollar_vol20 < 5_000_000:
                risk -= 12
            elif avg_dollar_vol20 < min_dollar_volume:
                risk -= 6
        if drawdown is not None:
            if drawdown > 0.55:
                risk -= 8
            elif drawdown > 0.40:
                risk -= 4
        if price is not None:
            if price < min_price:
                risk -= 12
            elif price < 5:
                risk -= 4
        if debt_to_equity is not None and debt_to_equity > 300:
            risk -= 4

        total = int(clamp(trend + price_volume + fundamentals + event + risk, 0, 100))
        tradable = bool(
            price is not None
            and price >= min_price
            and avg_dollar_vol20 is not None
            and avg_dollar_vol20 >= min_dollar_volume
            and not (isinstance(days_to_earnings, int) and days_to_earnings <= 2)
            and not (drawdown is not None and drawdown > 0.55)
        )

        if isinstance(days_to_earnings, int) and days_to_earnings <= 2:
            bucket = "Catalyst / Event Watch"
        elif total >= 76 and (row.get("breakout20") or row.get("breakout55")) and tradable:
            bucket = "Aggressive Buy Candidate"
        elif total >= 62 and tradable and (row.get("low_volume_pullback") or row.get("bullish_ma_stack") or (rs_3m or 0) > 0.05):
            bucket = "Pullback Watch"
        elif total >= 48:
            bucket = "Catalyst / Event Watch"
        else:
            bucket = "Avoid / No-Trade"
    else:
        price_volume = 0
        if row.get("breakout55"):
            price_volume += 15
        elif row.get("breakout20"):
            price_volume += 12
        elif row.get("low_volume_pullback"):
            price_volume += 10
        if volume_ratio is not None and daily_return is not None and daily_return > 0 and volume_ratio >= 1.2:
            price_volume += 3
        if atr_pct is not None and atr_pct <= 0.06:
            price_volume += 2
        price_volume = min(price_volume, 20)

        fundamentals = 0
        if revenue_growth is not None and revenue_growth > 0:
            fundamentals += 6
            if revenue_growth > 0.10:
                fundamentals += 2
        if profit_margin is not None and profit_margin > 0:
            fundamentals += 5
            if profit_margin > 0.15:
                fundamentals += 2
        if debt_to_equity is not None and debt_to_equity < 150:
            fundamentals += 4
            if debt_to_equity < 80:
                fundamentals += 1
        elif current_ratio is not None and current_ratio > 1.0:
            fundamentals += 2
        if forward_pe_pct is not None:
            if forward_pe_pct <= 0.40:
                fundamentals += 4
            elif forward_pe_pct <= 0.70:
                fundamentals += 2
        if roe is not None and roe > 0.12:
            fundamentals += 3
        fundamentals = min(fundamentals, 25)

        event = 0
        if analyst_positive > analyst_negative:
            event += 3
        if row.get("recent_sec_count", 0):
            event += 2
        if row.get("has_recent_8k"):
            event += 2
        if isinstance(days_to_earnings, int) and 6 <= days_to_earnings <= 21:
            event += 3
        event = min(event, 10)

        risk = 0
        if isinstance(days_to_earnings, int):
            if days_to_earnings <= 5:
                risk -= 10
            elif days_to_earnings <= 10:
                risk -= 4
        if atr_pct is not None:
            if atr_pct >= 0.08:
                risk -= 5
            elif atr_pct >= 0.06:
                risk -= 3
        if avg_dollar_vol20 is not None:
            if avg_dollar_vol20 < 10_000_000:
                risk -= 10
            elif avg_dollar_vol20 < min_dollar_volume:
                risk -= 6
        if drawdown is not None:
            if drawdown > 0.45:
                risk -= 7
            elif drawdown > 0.35:
                risk -= 4
        if price is not None and price < min_price:
            risk -= 10
        if debt_to_equity is not None and debt_to_equity > 250:
            risk -= 4

        total = int(clamp(trend + price_volume + fundamentals + event + risk, 0, 100))
        tradable = bool(
            price is not None
            and price >= min_price
            and avg_dollar_vol20 is not None
            and avg_dollar_vol20 >= min_dollar_volume
            and not (isinstance(days_to_earnings, int) and days_to_earnings <= 5)
            and not (drawdown is not None and drawdown > 0.45)
        )

        if isinstance(days_to_earnings, int) and days_to_earnings <= 5:
            bucket = "Catalyst / Event Watch"
        elif total >= 80 and (row.get("breakout20") or row.get("breakout55")) and tradable:
            bucket = "Aggressive Buy Candidate"
        elif total >= 65 and (row.get("low_volume_pullback") or row.get("bullish_ma_stack")) and tradable:
            bucket = "Pullback Watch"
        elif total >= 50:
            bucket = "Catalyst / Event Watch"
        else:
            bucket = "Avoid / No-Trade"

    return {
        "trend_score": trend,
        "price_volume_score": price_volume,
        "fundamental_score": fundamentals,
        "event_score": event,
        "risk_penalty": risk,
        "score": total,
        "bucket": bucket,
        "tradable": tradable,
    }


def build_reasons(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if row.get("bullish_ma_stack"):
        reasons.append("Price sits above the 20/50/200-day moving averages with a bullish stack.")
    if clean_float(row.get("rs_3m")) is not None and row.get("rs_3m") > 0:
        reasons.append(f"3-month relative strength vs SPY is positive at {row['rs_3m']:.2%}.")
    if row.get("breakout55"):
        reasons.append(f"Broke above the prior 55-day high on {row.get('volume_ratio', 0):.2f}x normal volume.")
    elif row.get("breakout20"):
        reasons.append(f"Cleared the prior 20-day high on {row.get('volume_ratio', 0):.2f}x normal volume.")
    elif row.get("low_volume_pullback"):
        reasons.append("Pulled back toward support with quieter volume, which fits a constructive reset.")
    if clean_float(row.get("revenue_growth")) is not None and row.get("revenue_growth") > 0:
        reasons.append(f"Revenue growth is positive at {row['revenue_growth']:.1%}.")
    if row.get("recent_sec_forms"):
        reasons.append(f"Recent SEC activity includes {', '.join(row['recent_sec_forms'][:3])}.")
    return reasons[:4]


def build_risks(row: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    if isinstance(row.get("days_to_earnings"), int):
        if row["days_to_earnings"] <= 5:
            risks.append("Earnings are close enough to make the trade binary.")
        elif row["days_to_earnings"] <= 10:
            risks.append("Earnings are approaching, so headline risk is rising.")
    if clean_float(row.get("atr_pct")) is not None and row.get("atr_pct") >= 0.08:
        risks.append(f"ATR is elevated at {row['atr_pct']:.1%}, which makes sizing harder.")
    if clean_float(row.get("avg_dollar_volume20")) is not None and row.get("avg_dollar_volume20") < 20_000_000:
        risks.append("Liquidity is below the default threshold for a normal swing trade.")
    if clean_float(row.get("drawdown_52w")) is not None and row.get("drawdown_52w") > 0.35:
        risks.append(f"The stock is still {row['drawdown_52w']:.1%} below its 52-week high.")
    if clean_float(row.get("debt_to_equity")) is not None and row.get("debt_to_equity") > 250:
        risks.append("Balance-sheet leverage is elevated.")
    return risks[:4]


def build_trade_plan(row: dict[str, Any], account_size: float, profile: str) -> dict[str, Any]:
    bucket = row["bucket"]
    price = clean_float(row.get("last_price"))
    atr = clean_float(row.get("atr14")) or (price * 0.05 if price else None)
    ma20 = clean_float(row.get("ma20"))
    ma50 = clean_float(row.get("ma50"))
    pivot = clean_float(row.get("pivot55")) or clean_float(row.get("pivot20")) or price

    if not price or bucket == "Avoid / No-Trade":
        return {
            "setup": "broken-trend",
            "preferred_action": "Wait. The current setup does not justify a fresh trade.",
            "buy_zone_low": None,
            "buy_zone_high": None,
            "entry_reference": None,
            "stop": None,
            "trim_1": None,
            "trim_2": None,
            "planned_shares": 0,
            "max_position_value": 0,
            "risk_budget_pct": 0,
        }

    if row.get("breakout55") or row.get("breakout20"):
        setup = "breakout"
        entry_reference = max(pivot or price, price)
        buy_zone_low = entry_reference
        buy_zone_high = entry_reference + (atr or price * 0.03) * (0.75 if profile == "offensive" else 0.5)
        provisional_stop = entry_reference - (atr or price * 0.03) * (1.35 if profile == "offensive" else 1.2)
        stop = min(ma20, provisional_stop) if ma20 else provisional_stop
        preferred_action = "Buy only on a fresh breakout confirmation or an orderly retest near the pivot."
        risk_budget_pct = 0.018 if profile == "offensive" else 0.015
        max_alloc_pct = 0.40 if profile == "offensive" else 0.35
    elif row.get("low_volume_pullback"):
        setup = "pullback"
        support = ma20 if ma20 and abs(price - ma20) <= abs(price - (ma50 or ma20)) else (ma50 or ma20 or price)
        buy_zone_low = support * 0.99
        buy_zone_high = support * 1.01
        entry_reference = max(price, buy_zone_low)
        provisional_stop = buy_zone_low - (atr or price * 0.03) * 1.0
        stop = min((ma50 * 0.98) if ma50 else provisional_stop, provisional_stop)
        preferred_action = "Let the pullback prove support before adding or starting the position."
        risk_budget_pct = 0.0125 if profile == "offensive" else 0.01
        max_alloc_pct = 0.30 if profile == "offensive" else 0.25
    else:
        setup = "catalyst"
        entry_reference = price
        buy_zone_low = price * 0.985
        buy_zone_high = price * 1.025
        stop = price - (atr or price * 0.04) * 1.5
        preferred_action = "Treat this as a smaller catalyst trade rather than a normal swing position."
        risk_budget_pct = 0.0075 if profile == "offensive" else 0.005
        max_alloc_pct = 0.20 if profile == "offensive" else 0.15

    if bucket == "Catalyst / Event Watch":
        risk_budget_pct = min(risk_budget_pct, 0.0075 if profile == "offensive" else 0.005)
        max_alloc_pct = min(max_alloc_pct, 0.20 if profile == "offensive" else 0.15)
        if "smaller" not in preferred_action.lower():
            preferred_action += " Treat it as a smaller event-driven position."

    stop = min(stop, entry_reference * 0.97) if stop >= entry_reference else stop
    risk_per_share = max(entry_reference - stop, price * 0.01)
    trim_1 = entry_reference + risk_per_share
    trim_2 = entry_reference + risk_per_share * 2
    max_position_value = account_size * max_alloc_pct
    shares_by_cap = math.floor(max_position_value / entry_reference)
    shares_by_risk = math.floor((account_size * risk_budget_pct) / risk_per_share)
    planned_shares = max(0, min(shares_by_cap, shares_by_risk))

    return {
        "setup": setup,
        "preferred_action": preferred_action,
        "buy_zone_low": round_or_none(buy_zone_low),
        "buy_zone_high": round_or_none(buy_zone_high),
        "entry_reference": round_or_none(entry_reference),
        "stop": round_or_none(stop),
        "trim_1": round_or_none(trim_1),
        "trim_2": round_or_none(trim_2),
        "planned_shares": planned_shares,
        "max_position_value": round_or_none(max_position_value),
        "risk_budget_pct": round_or_none(risk_budget_pct * 100, 2),
    }


def enrich_row(
    symbol: str,
    seed_quote: dict[str, Any],
    frame: pd.DataFrame,
    benchmark_returns: tuple[float | None, float | None],
    profile_settings: dict[str, Any],
    sec_map: dict[str, int],
    sec_session: requests.Session,
) -> dict[str, Any]:
    tech = compute_technical_frame(frame, benchmark_returns, profile_settings)
    quote_pack = safe_info(symbol)
    info = quote_pack["info"]
    fast_info = quote_pack["fast_info"]
    calendar = quote_pack["calendar"]
    upgrades = quote_pack["upgrades"]

    earnings_date, days_to_earnings = extract_earnings_days(calendar, seed_quote)
    analyst_positive, analyst_negative = summarize_upgrades(upgrades)

    recent_sec_events: list[dict[str, Any]] = []
    cik = sec_map.get(symbol)
    if cik is not None:
        try:
            recent_sec_events = fetch_sec_events(sec_session, cik)[:10]
            time.sleep(0.12)
        except Exception:
            recent_sec_events = []

    filtered_recent = []
    cutoff = datetime.now(timezone.utc).date().toordinal() - 45
    for event in recent_sec_events:
        filing_date = event.get("filing_date")
        try:
            filing_ord = date.fromisoformat(filing_date).toordinal() if filing_date else None
        except ValueError:
            filing_ord = None
        if filing_ord is None or filing_ord >= cutoff:
            filtered_recent.append(event)

    row: dict[str, Any] = {
        "ticker": symbol,
        "company_name": info.get("longName") or info.get("shortName") or seed_quote.get("longName") or symbol,
        "exchange": fast_info.get("exchange") or seed_quote.get("fullExchangeName") or seed_quote.get("exchange"),
        "sector_key": info.get("sectorKey"),
        "industry_key": info.get("industryKey"),
        "market_cap": clean_float(fast_info.get("marketCap") or info.get("marketCap") or seed_quote.get("marketCap")),
        "revenue_growth": clean_float(info.get("revenueGrowth")),
        "profit_margin": clean_float(info.get("profitMargins")),
        "debt_to_equity": clean_float(info.get("debtToEquity")),
        "current_ratio": clean_float(info.get("currentRatio")),
        "forward_pe": clean_float(info.get("forwardPE") or seed_quote.get("forwardPE")),
        "trailing_pe": clean_float(info.get("trailingPE") or seed_quote.get("trailingPE")),
        "price_to_book": clean_float(info.get("priceToBook") or seed_quote.get("priceToBook")),
        "return_on_equity": clean_float(info.get("returnOnEquity")),
        "average_analyst_rating": seed_quote.get("averageAnalystRating"),
        "earnings_date": earnings_date,
        "days_to_earnings": days_to_earnings,
        "analyst_positive_30d": analyst_positive,
        "analyst_negative_30d": analyst_negative,
        "recent_sec_count": len(filtered_recent),
        "recent_sec_forms": [event.get("form") for event in filtered_recent if event.get("form")],
        "recent_sec_events": filtered_recent[:3],
        "has_recent_8k": any(event.get("form") == "8-K" for event in filtered_recent),
        "seed_screens": seed_quote.get("seedScreens", []),
    }
    row.update(tech)
    return row


def main() -> None:
    args = parse_args()
    profile_settings = PROFILE_SETTINGS[args.profile]
    screens = args.screens or profile_settings["screens"]
    min_price = args.min_price if args.min_price is not None else profile_settings["min_price"]
    min_dollar_volume = (
        args.min_dollar_volume if args.min_dollar_volume is not None else profile_settings["min_dollar_volume"]
    )
    tickers = parse_ticker_list(args.tickers)
    symbols, seed_quotes = build_universe(tickers, screens, args.count)
    if not symbols:
        raise SystemExit("No symbols found. Provide --tickers or choose working screens.")

    history, benchmark_history = download_history(symbols, args.benchmark.upper())
    benchmark_returns = compute_benchmark_returns(benchmark_history)

    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent, "Accept-Encoding": "gzip, deflate"})
    try:
        sec_map = load_sec_ticker_map(session)
    except Exception as exc:
        print(f"[warn] failed to load SEC ticker map: {exc}")
        sec_map = {}

    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        frame = extract_history_frame(history, symbol)
        if frame.empty:
            print(f"[warn] missing history for {symbol}")
            continue
        row = enrich_row(
            symbol,
            seed_quotes.get(symbol, {}),
            frame,
            benchmark_returns,
            profile_settings,
            sec_map,
            session,
        )
        rows.append(row)

    forward_percentiles = valuation_percentiles(rows, "forward_pe")
    price_to_book_percentiles = valuation_percentiles(rows, "price_to_book")
    for row in rows:
        row["forward_pe_percentile"] = forward_percentiles.get(row["ticker"])
        row["price_to_book_percentile"] = price_to_book_percentiles.get(row["ticker"])
        row.update(compute_scores(row, min_price, min_dollar_volume, args.profile))
        row["reasons"] = build_reasons(row)
        row["risks"] = build_risks(row)
        row["trade_plan"] = build_trade_plan(row, args.account_size, args.profile)

    rows.sort(key=lambda item: (item.get("score", 0), clean_float(item.get("market_cap")) or 0), reverse=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": args.profile,
        "benchmark": args.benchmark.upper(),
        "account_size": args.account_size,
        "screens_used": screens if not tickers else [],
        "tickers_requested": tickers,
        "risk_filters": {
            "min_price": min_price,
            "min_dollar_volume": min_dollar_volume,
        },
        "candidate_count": len(rows),
        "source_notes": {
            "prices": "yfinance",
            "filings": "SEC EDGAR / data.sec.gov when available",
        },
        "ideas": rows,
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, default=serialize))
    print(json.dumps(payload, indent=2, default=serialize))


if __name__ == "__main__":
    main()

