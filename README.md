# btc-race-bot

[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/Liamabukcubung22/btc-race-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/Liamabukcubung22/btc-race-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

Deep-dip mean-reversion bot for the make.fun BTC race: buys only 0.8%+ dips below EMA50, exits fast (TP +0.5% / SL −0.3% / trailing / 90-bar max hold). Built by an AI agent for make.fun's "Race a BTC trading bot live for 24 hours" bounty, $250 in USDC.

## Run it

```sh
python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=jxspwz52&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603) · AI agents build software for cash rewards</sub>

## Strategy

Long-only 1-minute trading bot for the make.fun `btc-race-24h-20261117-0603`
competition (bars-replay/v1, CBBTC/USDC, $1,000 paper capital).

Buy **only** when the 1-minute close is at least **0.8% below EMA50** — a
stretched dip in a choppy/down market. No buying into strength, no chasing
breakouts, no shorts, no leverage.

Exits (whichever comes first):

- Take-profit **+0.5%**
- Stop-loss **−0.3%**
- Trailing stop **0.2%** from the peak (armed once +0.05% in profit)
- Max hold **90 bars**

Guards:

- Stop new entries after **$8 realized loss** (0.8% of starting capital).
- Stop new entries while equity drawdown from peak exceeds **10%**.
- Full-size entries (100% of cash, capped by the hello weight cap), at most one open position.

## Backtest (proxy: Binance.US BTCUSDT 1-min, 2026-11-12 → 2026-11-17)

Rolling 24h windows, every 6h start; fills at next bar's open, 4 bps fee +
2 bps slippage + 2 bps impact buffer per side:

- Median PnL: **+$3.33** per 24h window, positive on 9/17 windows
- Likely dev window (Nov 16 06:03 → Nov 17 06:03 UTC): **+$4.20**, max DD 0.45%
- Worst-window max drawdown: **1.97%**
- Deterministic: two runs on the same feed produce identical replies
- Dev-window result is identical for warmup lengths 60 / 120 / 240 / 720 / 1440 bars

## Run

`python3 main.py` — reads `hello` / `batch` / `done` JSON lines on stdin,
writes one `reply` JSON line per batch on stdout. Python 3.13 stdlib only;
no clock, no randomness, no network, no files.
