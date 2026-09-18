from __future__ import annotations

import json
from pathlib import Path

from .strategy import Signal

HTML = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>US Stock Decision Board</title>
<style>
:root { --bg:#070b14; --card:#10182a; --line:#1e2b45; --text:#e8eefc; --mut:#8b9bb8; --buy:#22d67a; --sell:#ff5d6c; --hold:#8b9bb8; }
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 ui-sans-serif,system-ui,sans-serif}
header{padding:20px 24px 8px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
h1{margin:0;font-size:22px}
.sub{color:var(--mut);font-size:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;padding:12px 16px 32px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px}
.sym{font-size:18px;font-weight:700}
.px{font-variant-numeric:tabular-nums;color:var(--mut)}
.split{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin:10px 0 8px}
.pct{font-size:28px;font-weight:800}
.buy{color:var(--buy)} .sell{color:var(--sell)}
.bar{display:flex;height:10px;border-radius:99px;overflow:hidden;background:#223}
.bar>i{display:block;height:100%}
.bar .b{background:var(--buy)} .bar .s{background:var(--sell)}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700}
.chip.BUY{background:#123d28;color:var(--buy)}
.chip.SELL{background:#3d1218;color:var(--sell)}
.chip.HOLD{background:#1b2436;color:var(--hold)}
svg{width:100%;height:84px;margin:8px 0}
.trail{display:flex;gap:2px;align-items:flex-end;height:28px;margin:8px 0}
.trail b{flex:1;min-width:2px;border-radius:1px}
.why{color:var(--mut);font-size:12px;margin:0;padding-left:16px}
table{width:100%;border-collapse:collapse;font-size:12px}
td,th{padding:4px 0;border-bottom:1px solid var(--line);text-align:left}
.warn{padding:0 16px 20px;color:#c9b07a;font-size:12px}
</style></head>
<body>
<header><div><h1>US Stock Decision Board</h1>
<div class="sub">Typed Buy / Sell probabilities · notify only · no orders · __ASOF__</div></div>
<div class="sub">Benchmark SPY · daily bars</div></header>
<section class="grid">__CARDS__</section>
<p class="warn">Not financial advice. Transparent feature score, not TypeSafe Jev. No orders are sent.</p>
</body></html>
"""


def _sparkline(closes, color):
    if len(closes) < 2:
        return ""
    vals = [c["close"] for c in closes]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    w, h = 300, 84
    pts = []
    for i, v in enumerate(vals):
        x = i / (len(vals) - 1) * w
        y = h - ((v - lo) / span) * (h - 8) - 4
        pts.append(f"{x:.1f},{y:.1f}")
    return f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none"><polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(pts)}"/></svg>'


def _trail(trail):
    bits = []
    for item in trail[-48:]:
        color = {"BUY": "#22d67a", "SELL": "#ff5d6c", "HOLD": "#31425f"}.get(item["action"], "#31425f")
        bits.append(f'<b style="background:{color};height:{50 + item["buy_pct"]/2}%"></b>')
    return '<div class="trail">' + "".join(bits) + "</div>"


def _card(sig: Signal) -> str:
    color = {"BUY": "#22d67a", "SELL": "#ff5d6c", "HOLD": "#8b9bb8"}.get(sig.action, "#8b9bb8")
    why = "".join(f"<li>{r}</li>" for r in sig.reasons[:4])
    rows = ""
    for item in reversed(sig.trail[-8:]):
        rows += f"<tr><td>{item['date']}</td><td>{item['action']}</td><td>{item['buy_pct']:.0f}% / {item['sell_pct']:.0f}%</td><td>${item['price']:.2f}</td></tr>"
    return f"""<article class="card">
  <div class="split"><div><div class="sym">{sig.symbol}</div><div class="px">${sig.price:.2f} · {sig.date}</div></div>
  <span class="chip {sig.action}">{sig.action}</span></div>
  <div class="split"><div class="pct buy">{sig.buy_pct:.0f}% Buy</div><div class="pct sell">{sig.sell_pct:.0f}% Sell</div></div>
  <div class="bar"><i class="b" style="width:{sig.buy_pct}%"></i><i class="s" style="width:{sig.sell_pct}%"></i></div>
  {_sparkline(sig.closes, color)}
  {_trail(sig.trail)}
  <ul class="why">{why}</ul>
  <table><thead><tr><th>Date</th><th>Dec</th><th>Buy/Sell</th><th>Px</th></tr></thead><tbody>{rows}</tbody></table>
</article>"""


def render(signals, asof=""):
    asof = asof or (signals[0].date if signals else "")
    cards = "".join(_card(s) for s in signals) or "<article class='card'>No symbols.</article>"
    return HTML.replace("__ASOF__", asof).replace("__CARDS__", cards)


def write_dashboard(signals, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / "dashboard.html"
    json_path = out / "decisions.json"
    html_path.write_text(render(signals), encoding="utf-8")
    payload = [{"symbol": s.symbol, "action": s.action, "price": s.price, "date": s.date, "buy_pct": s.buy_pct, "sell_pct": s.sell_pct, "reasons": s.reasons, "metrics": s.metrics, "trail": s.trail} for s in signals]
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"html": str(html_path), "json": str(json_path)}
