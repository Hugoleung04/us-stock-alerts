from __future__ import annotations

import json
import os
import urllib.request

from .strategy import Signal


def _post_json(url: str, payload: dict, timeout: int = 20) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "us-stock-alerts/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        resp.read()


def format_text(signals: list[Signal], only_actionable: bool, title: str = "US Stock Alerts") -> str:
    rows = [s for s in signals if s.actionable] if only_actionable else list(signals)
    lines = [title, ""]
    if not rows:
        lines.append("No BUY / SELL setup today.")
        holds = [s.symbol for s in signals if s.action == "HOLD"]
        if holds:
            lines.append("Watchlist HOLD: " + ", ".join(holds))
        return "\n".join(lines)

    for sig in rows:
        mark = {"BUY": "\U0001F7E2", "SELL": "\U0001F534", "HOLD": "\u26aa"}.get(sig.action, "\u2022")
        lines.append(f"{mark} {sig.action}  {sig.symbol}  ${sig.price:.2f}  ({sig.date})")
        for reason in sig.reasons:
            lines.append(f"   - {reason}")
        rs = sig.metrics.get("rs_20d")
        vol = sig.metrics.get("volume_ratio")
        extra = []
        if rs is not None:
            extra.append(f"RS {rs:+.1%}")
        if vol is not None:
            extra.append(f"Vol {vol:.2f}x")
        if extra:
            lines.append("   \u00b7 " + " \u00b7 ".join(extra))
        lines.append("")
    lines.append("Not financial advice. Signals only \u2014 no orders are sent.")
    return "\n".join(lines).rstrip()


def send_all(signals: list[Signal], notify_cfg: dict) -> list[str]:
    only = bool((notify_cfg or {}).get("only_actionable", True))
    text = format_text(signals, only_actionable=only)
    sent: list[str] = []

    tg = notify_cfg.get("telegram") or {}
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or tg.get("bot_token")
    chat = os.environ.get("TELEGRAM_CHAT_ID") or tg.get("chat_id")
    if tg.get("enabled") or (token and chat):
        if token and chat:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            _post_json(url, {"chat_id": chat, "text": text})
            sent.append("telegram")

    discord_url = os.environ.get("DISCORD_WEBHOOK_URL") or (notify_cfg.get("discord") or {}).get("webhook_url")
    if (notify_cfg.get("discord") or {}).get("enabled") or discord_url:
        if discord_url:
            _post_json(discord_url, {"content": text[:1900]})
            sent.append("discord")

    slack_url = os.environ.get("SLACK_WEBHOOK_URL") or (notify_cfg.get("slack") or {}).get("webhook_url")
    if (notify_cfg.get("slack") or {}).get("enabled") or slack_url:
        if slack_url:
            _post_json(slack_url, {"text": text})
            sent.append("slack")

    hook = os.environ.get("GENERIC_WEBHOOK_URL") or (notify_cfg.get("webhook") or {}).get("url")
    if (notify_cfg.get("webhook") or {}).get("enabled") or hook:
        if hook:
            payload = {
                "text": text,
                "signals": [
                    {
                        "symbol": s.symbol,
                        "action": s.action,
                        "price": s.price,
                        "date": s.date,
                        "reasons": s.reasons,
                        "metrics": s.metrics,
                    }
                    for s in signals
                ],
            }
            _post_json(hook, payload)
            sent.append("webhook")

    return sent
