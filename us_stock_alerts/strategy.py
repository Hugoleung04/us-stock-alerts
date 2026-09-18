"""Probabilistic swing decisions. Signals only — never places orders."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class StrategyParams:
    fast_ma: int = 20
    slow_ma: int = 50
    rs_lookback: int = 20
    volume_mult: float = 1.10
    sell_drawdown: float = 0.10
    min_history: int = 60
    buy_threshold: float = 0.55
    sell_threshold: float = 0.45
    trail_bars: int = 40


@dataclass
class Signal:
    symbol: str
    action: str
    price: float
    date: str
    reasons: list[str]
    metrics: dict
    buy_pct: float = 50.0
    sell_pct: float = 50.0
    trail: list[dict] = field(default_factory=list)
    closes: list[dict] = field(default_factory=list)

    @property
    def actionable(self) -> bool:
        return self.action in {"BUY", "SELL"}

    @property
    def confidence(self) -> float:
        return max(self.buy_pct, self.sell_pct)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0).rolling(period).mean()
    loss = (-delta.clip(upper=0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def add_indicators(bars: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    df = bars.copy()
    close = df["AdjClose"] if "AdjClose" in df.columns else df["Close"]
    df["ma_fast"] = close.rolling(params.fast_ma).mean()
    df["ma_slow"] = close.rolling(params.slow_ma).mean()
    df["vol_avg"] = df["Volume"].rolling(params.fast_ma).mean()
    df["ret_rs"] = close.pct_change(params.rs_lookback)
    df["high_n"] = close.rolling(params.fast_ma).max()
    df["drawdown"] = close / df["high_n"] - 1.0
    df["rsi"] = _rsi(close, 14)
    return df


def _sigmoid(x: float) -> float:
    x = max(-12.0, min(12.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def buy_probability(row: pd.Series, bench_row: pd.Series) -> float:
    close = float(row["Close"])
    ma_fast = float(row["ma_fast"])
    ma_slow = float(row["ma_slow"])
    vol_avg = float(row["vol_avg"]) if row["vol_avg"] else 0.0
    fast_gap = (close - ma_fast) / ma_fast if ma_fast else 0.0
    slow_gap = (ma_fast - ma_slow) / ma_slow if ma_slow else 0.0
    rs = float(row["ret_rs"] - bench_row["ret_rs"])
    vol_ratio = float(row["Volume"] / vol_avg) if vol_avg else 1.0
    dd = float(row["drawdown"])
    rsi = float(row["rsi"]) if pd.notna(row["rsi"]) else 50.0
    market = 1.0 if float(bench_row["Close"]) > float(bench_row["ma_slow"]) else -1.0
    logit = (
        0.55 * market
        + 10.0 * fast_gap
        + 7.0 * slow_gap
        + 5.0 * rs
        + 0.40 * math.log(max(vol_ratio, 0.05))
        + 4.0 * dd
        + 0.45 * ((rsi - 50.0) / 25.0)
    )
    return _sigmoid(logit)


def _reasons(action: str, row: pd.Series, bench_row: pd.Series, p_buy: float, params: StrategyParams) -> list[str]:
    market_ok = float(bench_row["Close"]) > float(bench_row["ma_slow"])
    reasons: list[str] = [f"Model {p_buy * 100:.0f}% Buy / {(1 - p_buy) * 100:.0f}% Sell"]
    if action == "BUY":
        reasons += [
            "SPY above 50-day MA" if market_ok else "SPY filter weak (still high Buy %)",
            f"Price vs {params.fast_ma}/{params.slow_ma} MA trend",
        ]
    elif action == "SELL":
        if not market_ok:
            reasons.append("SPY closed below 50-day MA")
        if float(row["Close"]) < float(row["ma_fast"]):
            reasons.append(f"Close lost {params.fast_ma}-day MA")
        if float(row["drawdown"]) <= -params.sell_drawdown:
            reasons.append(f"Drawdown from {params.fast_ma}-day high")
        if p_buy <= params.sell_threshold:
            reasons.append("Sell probability dominates")
    else:
        if not market_ok:
            reasons.append("Market filter off — no new BUY")
        elif params.sell_threshold < p_buy < params.buy_threshold:
            reasons.append("Confidence inside dead zone")
        else:
            reasons.append("No actionable setup")
    return reasons


def _action_from_prob(p_buy, row, bench_row, params, previous_action):
    market_ok = float(bench_row["Close"]) > float(bench_row["ma_slow"])
    broken_fast = float(row["Close"]) < float(row["ma_fast"])
    deep_dd = float(row["drawdown"]) <= -params.sell_drawdown
    if previous_action == "BUY" and (p_buy <= 0.50 or broken_fast or deep_dd or not market_ok):
        return "SELL"
    if p_buy >= params.buy_threshold and market_ok:
        return "BUY"
    if p_buy <= params.sell_threshold:
        return "SELL"
    return "HOLD"


def evaluate(symbol, bars, benchmark, params, previous_action=None):
    stock = add_indicators(bars, params)
    bench = add_indicators(benchmark, params)
    if len(stock) < params.min_history or len(bench) < params.min_history:
        last = stock.iloc[-1] if len(stock) else None
        return Signal(
            symbol=symbol,
            action="HOLD",
            price=float(last["Close"]) if last is not None else 0.0,
            date=str(stock.index[-1].date()) if len(stock) else "",
            reasons=["Not enough history"],
            metrics={},
        )
    aligned = stock.join(bench[["Close", "ma_slow", "ret_rs"]], how="inner", rsuffix="_spy")
    start = max(params.min_history, len(aligned) - params.trail_bars)
    trail = []
    prev = None
    for i in range(start, len(aligned)):
        row = aligned.iloc[i]
        bench_row = pd.Series({"Close": row["Close_spy"], "ma_slow": row["ma_slow_spy"], "ret_rs": row["ret_rs_spy"]})
        if pd.isna(row["ma_fast"]) or pd.isna(row["ma_slow"]) or pd.isna(bench_row["ma_slow"]):
            continue
        p_buy = buy_probability(row, bench_row)
        act = _action_from_prob(p_buy, row, bench_row, params, prev)
        trail.append({"date": str(aligned.index[i].date()), "action": act, "buy_pct": round(p_buy * 100, 1), "sell_pct": round((1 - p_buy) * 100, 1), "price": round(float(row["Close"]), 4)})
        prev = act if act != "HOLD" else prev
    row = stock.iloc[-1]
    b = bench.iloc[-1]
    p_buy = buy_probability(row, b)
    action = _action_from_prob(p_buy, row, b, params, previous_action)
    price = float(row["Close"])
    date = str(stock.index[-1].date())
    vol_avg = float(row["vol_avg"]) if row["vol_avg"] else 0.0
    metrics = {
        "close": round(price, 4),
        "ma_fast": round(float(row["ma_fast"]), 4),
        "ma_slow": round(float(row["ma_slow"]), 4),
        "rs_20d": round(float(row["ret_rs"] - b["ret_rs"]), 4),
        "volume_ratio": round(float(row["Volume"] / vol_avg), 3) if vol_avg else None,
        "drawdown_20d": round(float(row["drawdown"]), 4),
        "rsi": round(float(row["rsi"]), 2) if pd.notna(row["rsi"]) else None,
        "spy_above_slow_ma": bool(b["Close"] > b["ma_slow"]),
        "buy_pct": round(p_buy * 100, 1),
        "sell_pct": round((1 - p_buy) * 100, 1),
    }
    closes = [{"date": str(idx.date()), "close": round(float(val), 4)} for idx, val in stock["Close"].tail(80).items()]
    return Signal(
        symbol=symbol,
        action=action,
        price=price,
        date=date,
        reasons=_reasons(action, row, b, p_buy, params),
        metrics=metrics,
        buy_pct=round(p_buy * 100, 1),
        sell_pct=round((1 - p_buy) * 100, 1),
        trail=trail,
        closes=closes,
    )
