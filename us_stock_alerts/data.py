"""Daily bars from Yahoo Finance public chart API. No API key."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Iterable

import pandas as pd

CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?range={range}&interval=1d&events=div%7Csplit"
)
USER_AGENT = (
    "Mozilla/5.0 (compatible; us-stock-alerts/1.0; "
    "+https://github.com/us-stock-alerts)"
)


class DataError(RuntimeError):
    pass


def _get_json(url: str, retries: int = 3, pause: float = 0.8) -> dict:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(pause * (attempt + 1))
    raise DataError(f"Failed to fetch {url}: {last}") from last


def fetch_daily(symbol: str, lookback: str = "1y") -> pd.DataFrame:
    payload = _get_json(CHART_URL.format(symbol=symbol, range=lookback))
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise DataError(f"{symbol}: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        raise DataError(f"No chart data for {symbol}")

    result = results[0]
    ts = result.get("timestamp") or []
    quote = (result.get("indicators") or {}).get("quote") or [{}]
    q = quote[0]
    if not ts or not q:
        raise DataError(f"Empty series for {symbol}")

    frame = pd.DataFrame(
        {
            "Open": q.get("open"),
            "High": q.get("high"),
            "Low": q.get("low"),
            "Close": q.get("close"),
            "Volume": q.get("volume"),
        },
        index=pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York"),
    )
    frame.index.name = "Date"
    frame = frame.dropna(subset=["Close"])
    adj = (result.get("indicators") or {}).get("adjclose")
    if adj:
        adj_vals = adj[0].get("adjclose")
        if adj_vals:
            adj_series = pd.Series(
                adj_vals,
                index=pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York"),
            )
            frame["AdjClose"] = adj_series.reindex(frame.index)
        else:
            frame["AdjClose"] = frame["Close"]
    else:
        frame["AdjClose"] = frame["Close"]
    return frame


def fetch_many(symbols: Iterable[str], lookback: str = "1y") -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    for symbol in symbols:
        try:
            out[symbol] = fetch_daily(symbol, lookback=lookback)
            time.sleep(0.25)
        except DataError as exc:
            errors[symbol] = str(exc)
    if errors and not out:
        raise DataError(
            "All downloads failed: " + "; ".join(f"{k}: {v}" for k, v in errors.items())
        )
    return out
