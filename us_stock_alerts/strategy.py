"""Rules-based swing strategy. Signals only — never places orders."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class StrategyParams:
    fast_ma: int = 20
    slow_ma: int = 50
    rs_lookback: int = 20
    volume_mult: float = 1.10
    sell_drawdown: float = 0.10
    min_history: int = 60


@dataclass
class Signal:
    symbol: str
    action: str  # BUY, SELL, HOLD
    price: float
    date: str
    reasons: list[str]
    metrics: dict

    @property
    def actionable(self) -> bool:
        return self.action in {"BUY", "SELL"}


def add_indicators(bars: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    df = bars.copy()
    close = df["AdjClose"] if "AdjClose" in df.columns else df["Close"]
    df["ma_fast"] = close.rolling(params.fast_ma).mean()
    df["ma_slow"] = close.rolling(params.slow_ma).mean()
    df["vol_avg"] = df["Volume"].rolling(params.fast_ma).mean()
    df["ret_rs"] = close.pct_change(params.rs_lookback)
    df["high_n"] = close.rolling(params.fast_ma).max()
    df["drawdown"] = close / df["high_n"] - 1.0
    return df


def evaluate(
    symbol: str,
    bars: pd.DataFrame,
    benchmark: pd.DataFrame,
    params: StrategyParams,
    previous_action: str | None = None,
) -> Signal:
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

    row = stock.iloc[-1]
    b = bench.iloc[-1]
    price = float(row["Close"])
    date = str(stock.index[-1].date())

    market_ok = bool(b["Close"] > b["ma_slow"])
    trend_up = bool(row["Close"] > row["ma_fast"] and row["ma_fast"] > row["ma_slow"])
    rs_ok = bool(row["ret_rs"] > b["ret_rs"])
    volume_ok = bool(row["Volume"] >= row["vol_avg"] * params.volume_mult)
    broken_fast = bool(row["Close"] < row["ma_fast"])
    deep_dd = bool(row["drawdown"] <= -params.sell_drawdown)
    market_off = not market_ok

    metrics = {
        "close": round(price, 4),
        "ma_fast": round(float(row["ma_fast"]), 4),
        "ma_slow": round(float(row["ma_slow"]), 4),
        "rs_20d": round(float(row["ret_rs"] - b["ret_rs"]), 4),
        "volume_ratio": round(float(row["Volume"] / row["vol_avg"]), 3) if row["vol_avg"] else None,
        "drawdown_20d": round(float(row["drawdown"]), 4),
        "spy_above_slow_ma": market_ok,
    }

    reasons: list[str] = []
    action = "HOLD"

    if previous_action == "BUY" and (broken_fast or deep_dd or market_off):
        action = "SELL"
        if broken_fast:
            reasons.append(f"Close lost {params.fast_ma}-day MA")
        if deep_dd:
            reasons.append(
                f"Pullback from {params.fast_ma}-day high >= {params.sell_drawdown:.0%}"
            )
        if market_off:
            reasons.append("SPY closed below its 50-day MA")
    elif market_ok and trend_up and rs_ok and volume_ok:
        action = "BUY"
        reasons = [
            "SPY above 50-day MA",
            f"Price > {params.fast_ma}MA > {params.slow_ma}MA",
            "20-day return beating SPY",
            f"Volume >= {params.volume_mult:.2f}x average",
        ]
    else:
        if not market_ok:
            reasons.append("Market filter off (SPY < 50-day MA)")
        if not trend_up:
            reasons.append("Stock trend not aligned")
        if not rs_ok:
            reasons.append("Lagging SPY over 20 days")
        if not volume_ok:
            reasons.append("Volume not confirming")
        if not reasons:
            reasons.append("No setup")

    return Signal(
        symbol=symbol,
        action=action,
        price=price,
        date=date,
        reasons=reasons,
        metrics=metrics,
    )
