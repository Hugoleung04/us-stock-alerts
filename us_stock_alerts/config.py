from __future__ import annotations

from pathlib import Path

import yaml

from .strategy import StrategyParams

DEFAULTS = {
    "watchlist": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META"],
    "benchmark": "SPY",
    "strategy": {},
    "notify": {"only_actionable": True},
    "output_dir": "out",
    "state_file": "state.json",
}


def load_config(path: str | Path | None) -> dict:
    cfg = dict(DEFAULTS)
    if path:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        merged = dict(DEFAULTS)
        merged.update(raw)
        merged["strategy"] = {**DEFAULTS["strategy"], **(raw.get("strategy") or {})}
        merged["notify"] = {**DEFAULTS["notify"], **(raw.get("notify") or {})}
        cfg = merged
    cfg["watchlist"] = [str(s).upper().strip() for s in cfg.get("watchlist") or []]
    cfg["benchmark"] = str(cfg.get("benchmark") or "SPY").upper()
    return cfg


def params_from_config(cfg: dict) -> StrategyParams:
    s = cfg.get("strategy") or {}
    return StrategyParams(
        fast_ma=int(s.get("fast_ma", 20)),
        slow_ma=int(s.get("slow_ma", 50)),
        rs_lookback=int(s.get("rs_lookback", 20)),
        volume_mult=float(s.get("volume_mult", 1.10)),
        sell_drawdown=float(s.get("sell_drawdown", 0.10)),
        min_history=int(s.get("min_history", 60)),
        buy_threshold=float(s.get("buy_threshold", 0.55)),
        sell_threshold=float(s.get("sell_threshold", 0.45)),
        trail_bars=int(s.get("trail_bars", 40)),
    )
