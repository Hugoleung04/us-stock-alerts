from __future__ import annotations

import numpy as np
import pandas as pd

from us_stock_alerts.strategy import StrategyParams, add_indicators, evaluate


def _synth(start: float, drift: float, vol_base: float, n: int = 120) -> pd.DataFrame:
    idx = pd.date_range("2025-01-02", periods=n, freq="B", tz="America/New_York")
    close = start * np.cumprod(1 + np.full(n, drift))
    volume = np.full(n, vol_base)
    volume[-1] = vol_base * 2
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "AdjClose": close,
            "Volume": volume,
        },
        index=idx,
    )


def test_buy_when_trend_rs_and_volume_confirm():
    stock = _synth(100, 0.004, 1_000_000)
    spy = _synth(400, 0.001, 5_000_000)
    sig = evaluate("TEST", stock, spy, StrategyParams(), previous_action=None)
    assert sig.action == "BUY"
    assert sig.metrics["spy_above_slow_ma"] is True


def test_hold_when_lagging_benchmark():
    stock = _synth(100, 0.0005, 1_000_000)
    spy = _synth(400, 0.004, 5_000_000)
    sig = evaluate("TEST", stock, spy, StrategyParams(), previous_action=None)
    assert sig.action == "HOLD"


def test_sell_after_buy_when_fast_ma_breaks():
    n = 120
    idx = pd.date_range("2025-01-02", periods=n, freq="B", tz="America/New_York")
    close = np.concatenate([np.linspace(100, 140, n - 5), np.array([138, 130, 120, 110, 100.0])])
    stock = pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "AdjClose": close,
            "Volume": np.full(n, 1_000_000),
        },
        index=idx,
    )
    spy = _synth(400, 0.002, 5_000_000)
    sig = evaluate("TEST", stock, spy, StrategyParams(), previous_action="BUY")
    assert sig.action == "SELL"


def test_indicators_have_expected_columns():
    stock = _synth(100, 0.002, 1_000_000)
    out = add_indicators(stock, StrategyParams())
    for col in ("ma_fast", "ma_slow", "vol_avg", "ret_rs", "drawdown"):
        assert col in out.columns
