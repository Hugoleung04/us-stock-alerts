# us-stock-alerts

美股**波段訊號掃描器**。拉最新日線、用公開規則計訊號、產出報告，再經 Telegram / Discord / Slack / Webhook 通知你。

**唔會交易。** 冇券商登入、冇落單、冇模擬盤下單。

[English README](README.md)

## 做哪

```
Yahoo 日線 → 趨勢 + 相對 SPY 強弱 → BUY / SELL / HOLD → 通知
```

預設規則（可嗚 `config.yaml` 改）：

1. 只有 **SPY 收市高過 50 日均線** 先考慮買入
2. 個股要升軌：**價 > 20 日均 > 50 日均**
3. 近 20 日回報 **跑贏 SPY**
4. 最新成交量至少係 20 日均量 **1.1 倍**
5. `state.json` 記低上次 BUY 之後，跌破 20 日均、由 20 日高位回吐 10%、或者 SPY 跌穿 50 日均，就出 SELL

呢個係研究／提醒工具，唔保證賺錢。

## 本機跑

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp config.example.yaml config.yaml
# 改 watchlist
python -m us_stock_alerts --config config.yaml --no-notify --all
```

會出：

- 終端機摘要
- `out/signals.csv`
- `out/signals.md`
- `state.json`（記倉，下次先出得倒 SELL）

## 通知

環境變數優先（唔好把 token 寫死入 repo）：

| 渠道 | 變數 |
|---|---|
| Telegram | `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` |
| Discord | `DISCORD_WEBHOOK_URL` |
| Slack | `SLACK_WEBHOOK_URL` |
| 自訂 HTTP | `GENERIC_WEBHOOK_URL` |

Telegram：搞 [@BotFather](https://t.me/BotFather) 開 bot，然後 message 自己個 bot，用 `getUpdates` 支 `chat_id`。

## 用 GitHub Actions 每日通知（唔使自己開機）

1. Fork 或者 push 呢個 repo
2. Settings → Secrets and variables → Actions 加上述 secrets
3. `.github/workflows/daily-scan.yml` 每個美股交易日 **21:30 UTC** 跑一次（美股收市後；香港時間約凌晨 5:30）
4. 亦可以嗚 Actions 頁撲 **Run workflow** 即時跑

想用自己名單，commit 一份**唔包含密碼**的 `config.yaml`。

## 免責

唔係投資建議。美股可以蝕本。Yahoo 數據非官方、可能有延遲。睇完訊號點做，責任嗚你。

MIT License.
