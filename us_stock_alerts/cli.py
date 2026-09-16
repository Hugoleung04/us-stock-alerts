from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config, params_from_config
from .data import DataError, fetch_daily, fetch_many
from .notify import format_text, send_all
from .report import write_outputs
from .state import load_state, save_state, update_from_signals
from .strategy import evaluate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="us-stock-alerts",
        description="Scan a US stock watchlist and send BUY/SELL notifications. No trading.",
    )
    p.add_argument("--config", "-c", default=None, help="Path to config.yaml")
    p.add_argument("--no-notify", action="store_true", help="Print only, do not send")
    p.add_argument("--all", action="store_true", help="Include HOLD rows in the message")
    p.add_argument("--lookback", default="1y", help="Yahoo range, default 1y")
    return p


def run(args: argparse.Namespace) -> int:
    cfg_path = args.config
    if cfg_path is None and Path("config.yaml").exists():
        cfg_path = "config.yaml"
    cfg = load_config(cfg_path)
    params = params_from_config(cfg)
    watch = list(cfg["watchlist"])
    bench_sym = cfg["benchmark"]

    try:
        benchmark = fetch_daily(bench_sym, lookback=args.lookback)
        frames = fetch_many(watch, lookback=args.lookback)
    except DataError as exc:
        print(f"Data error: {exc}", file=sys.stderr)
        return 2

    state = load_state(cfg["state_file"])
    positions = state.get("positions") or {}

    signals = []
    missing = [s for s in watch if s not in frames]
    for symbol in watch:
        if symbol not in frames:
            continue
        prev = (positions.get(symbol) or {}).get("action")
        signals.append(evaluate(symbol, frames[symbol], benchmark, params, previous_action=prev))

    notify_cfg = dict(cfg.get("notify") or {})
    if args.all:
        notify_cfg["only_actionable"] = False

    print(format_text(signals, only_actionable=notify_cfg.get("only_actionable", True)))
    if missing:
        print("\nSkipped (no data): " + ", ".join(missing), file=sys.stderr)

    paths = write_outputs(signals, cfg["output_dir"])
    print(f"\nWrote {paths['csv']} and {paths['markdown']}")

    state = update_from_signals(state, signals)
    save_state(cfg["state_file"], state)

    if not args.no_notify:
        try:
            sent = send_all(signals, notify_cfg)
        except Exception as exc:
            print(f"Notify error: {exc}", file=sys.stderr)
            return 3
        if sent:
            print("Sent via: " + ", ".join(sent))
        else:
            print("No notification channels configured.")
    return 0


def main() -> None:
    raise SystemExit(run(build_parser().parse_args()))


if __name__ == "__main__":
    main()
