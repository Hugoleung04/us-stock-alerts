from __future__ import annotations

from pathlib import Path

import pandas as pd

from .strategy import Signal


def to_frame(signals: list[Signal]) -> pd.DataFrame:
    rows = []
    for s in signals:
        row = {
            "date": s.date,
            "symbol": s.symbol,
            "action": s.action,
            "price": s.price,
            "reasons": " | ".join(s.reasons),
        }
        row.update(s.metrics)
        rows.append(row)
    return pd.DataFrame(rows)


def write_outputs(signals: list[Signal], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame = to_frame(signals)
    csv_path = out / "signals.csv"
    md_path = out / "signals.md"
    frame.to_csv(csv_path, index=False)

    lines = ["# US Stock Alerts", "", "| Action | Symbol | Price | Date | Why |", "|---|---|---|---|---|"]
    for s in signals:
        why = "<br>".join(s.reasons)
        lines.append(f"| {s.action} | {s.symbol} | {s.price:.2f} | {s.date} | {why} |")
    lines += ["", "_Not financial advice. No orders are placed._", ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"csv": str(csv_path), "markdown": str(md_path)}
