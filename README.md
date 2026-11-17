# BTC Race Bot — Deep-Dip Mean Reversion

Long-only 1-minute trading bot for the make.fun `btc-race-24h-20261117-0603`
competition (bars-replay/v1, CBBTC/USDC, $1,000 paper capital).

## Strategy

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
- Full-size entries (100% of cash), at most one open position.

## Backtest (proxy: Binance.US BTCUSDT 1-min, 2026-11-12 → 2026-11-17)

Rolling 24h windows, every 6h start; fills at next bar's open, 4 bps fee +
2 bps slippage + 2 bps impact buffer per side:

- Median PnL: **+$3.33** per 24h window, positive on 9/17 windows
- Likely dev window (Nov 16 06:03 → Nov 17 06:03 UTC): **+$4.20**, max DD 0.45%
- Worst-window max drawdown: **1.97%**
- Deterministic: two runs on the same feed produce identical replies

## Run

`python3 main.py` — reads `hello` / `batch` / `done` JSON lines on stdin,
writes one `reply` JSON line per batch on stdout. Python 3.13 stdlib only;
no clock, no randomness, no network, no files.
