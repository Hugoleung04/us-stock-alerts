# us-stock-alerts

US stock **swing-signal scanner**. It downloads the latest daily bars, applies a transparent rules-based strategy, writes a report, and can notify you on Telegram / Discord / Slack / a generic webhook.

It **does not trade**. There is no broker login, no order ticket, no paper-trading engine.

[繁體中文說明](README.zh-Hant.md)

## What it does

```
Yahoo daily bars → trend + relative strength vs SPY → BUY / SELL / HOLD → notify
```

Default rules (editable in `config.yaml`):

1. Only consider buys when **SPY is above its 50-day moving average**.
2. Stock must be in an uptrend: **price > 20-day MA > 50-day MA**.
3. Stock **20-day return beats SPY**.
4. Latest volume is at least **1.1×** the 20-day average.
5. After a BUY is stored in `state.json`, emit SELL if price loses the 20-day MA, drops 10% from the 20-day high, or SPY loses its 50-day MA.

This is a research helper, not a profit guarantee.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp config.example.yaml config.yaml
# edit watchlist in config.yaml
python -m us_stock_alerts --config config.yaml --no-notify --all
```

Output:

- terminal summary
- `out/signals.csv`
- `out/signals.md`
- `state.json` (remembers last BUY so the next SELL can fire)

## Notifications

Set any of these environment variables (recommended) or the matching fields in `config.yaml`:

| Channel | Variables |
|---|---|
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| Discord | `DISCORD_WEBHOOK_URL` |
| Slack | `SLACK_WEBHOOK_URL` |
| Generic HTTP | `GENERIC_WEBHOOK_URL` |

Telegram: talk to [@BotFather](https://t.me/BotFather), then message your bot and get `chat_id` from `https://api.telegram.org/bot<token>/getUpdates`.

```bash
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
python -m us_stock_alerts --config config.yaml
```

## GitHub Actions (no server)

1. Fork or push this repo.
2. Repo → Settings → Secrets and variables → Actions.
3. Add the token / webhook secrets you want.
4. The workflow `.github/workflows/daily-scan.yml` runs **21:30 UTC, Monday–Friday** (after the US cash session) and can also be started with **Run workflow**.

Optional: commit your own `config.yaml` (no secrets inside) so Actions uses your watchlist.

## Docker

```bash
docker build -t us-stock-alerts .
docker run --rm us-stock-alerts --config config.example.yaml --no-notify --all
```

## Disclaimer

This project is for education and personal workflow automation. It is **not investment advice**. US-listed securities can lose money. Data from Yahoo Finance is delayed / unofficial. You are responsible for any decision you make after reading a signal.

MIT License.
