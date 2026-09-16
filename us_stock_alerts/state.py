from __future__ import annotations

import json
from pathlib import Path


def load_state(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {"positions": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"positions": {}}


def save_state(path: str | Path, state: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


def update_from_signals(state: dict, signals: list) -> dict:
    positions = dict(state.get("positions") or {})
    for sig in signals:
        if sig.action == "BUY":
            positions[sig.symbol] = {"action": "BUY", "since": sig.date, "price": sig.price}
        elif sig.action == "SELL":
            positions.pop(sig.symbol, None)
    state["positions"] = positions
    if signals:
        state["last_scan"] = signals[0].date
    return state
