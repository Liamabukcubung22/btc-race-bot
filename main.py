#!/usr/bin/env python3
"""BTC race bot (bars-replay/v1, long-only, $1,000 paper).

Strategy: deep-dip mean reversion.
  - Buy ONLY when the 1-min close is >= 0.8% below EMA50: a stretched dip
    in a choppy/down market. No buying into strength, no chasing breakouts.
  - Exit fast: +0.5% take-profit, -0.3% stop-loss, 0.2% trailing stop
    (armed once +0.05% in profit), or 90-bar max hold.
  - Guards: stop new entries after $8 realized loss (0.8% of starting
    capital) in the run, and while equity drawdown from peak exceeds 10%.
  - Full-size entries (100% of cash); at most one open position.

Protocol: reads hello (caps/fees/capital/warmup) at runtime, replies to
every batch, empty orders during warmup, exits cleanly on done/EOF.
Stdlib only. Deterministic: no clock, no randomness, no network, no files.
"""

import sys
import json

DEPTH = 0.008          # buy only this far below EMA50
TP = 0.005             # take profit
SL = 0.003             # stop loss
TRAIL = 0.002          # trailing stop from peak
TRAIL_ARM = 0.0005     # trail only once this far in profit
MAX_HOLD = 90          # bars
LOSS_LIMIT_FRAC = 0.008  # stop new entries after this frac of capital lost
DD_GUARD = 0.10        # stop new entries while equity DD exceeds this
MIN_BARS = 50          # bars of history before first entry


def main():
    symbol = None
    quote_scale = 6
    start_capital = 0
    min_notional = 0
    max_weight_bps = 10000
    warmup_left = 60

    ema50 = None
    ema_k = 2.0 / 51.0
    bars_seen = 0

    cash = 0
    pos_qty = 0
    entry_px = None
    peak_px = None
    hold_bars = 0
    realized = 0
    buy_cost = 0
    equity_peak = 0

    out = sys.stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        mtype = msg.get("type")

        if mtype == "hello":
            syms = msg.get("symbols") or []
            if syms:
                symbol = syms[0].get("symbol")
            cap = msg.get("capital") or {}
            quote_scale = int(cap.get("quote_scale", 6))
            start_capital = int(cap.get("quote_units", 0))
            fees = msg.get("fees") or {}
            min_notional = int(fees.get("min_notional_quote_units", 0))
            caps = msg.get("caps") or {}
            max_weight_bps = int(caps.get("max_weight_bps", 10000))
            warmup_left = int(msg.get("warmup_bars", 60))
            equity_peak = start_capital
            continue

        if mtype == "done":
            break

        if mtype != "batch":
            continue

        seq = int(msg.get("seq", 0))

        # Authoritative account snapshot.
        acct = msg.get("account") or {}
        cash = int(acct.get("cash_quote_units", cash))
        equity = int(acct.get("equity_quote_units", cash))
        if equity > equity_peak:
            equity_peak = equity
        pos = None
        for p in acct.get("positions") or []:
            if p.get("symbol") == symbol:
                pos = p
                break
        pos_qty = int(pos.get("qty", 0)) if pos else 0

        # Fills of the previous batch's orders.
        for f in msg.get("fills") or []:
            if f.get("symbol") != symbol or f.get("status") != "filled":
                continue
            if f.get("side") == "buy":
                entry_px = int(f.get("price", 0))
                peak_px = entry_px
                hold_bars = 0
                buy_cost = int(f.get("notional_quote_units", 0))
            elif f.get("side") == "sell":
                proceeds = int(f.get("notional_quote_units", 0)) - int(
                    f.get("fee_quote_units", 0)
                )
                realized += proceeds - buy_cost
                entry_px = None
                peak_px = None
                buy_cost = 0

        # Indicator update from this bar's close.
        close = None
        for b in msg.get("bars") or []:
            if b.get("symbol") == symbol:
                close = int(b.get("c", 0))
                break
        if close is not None:
            if ema50 is None:
                ema50 = float(close)
            else:
                ema50 = close * ema_k + ema50 * (1.0 - ema_k)
            bars_seen += 1

        orders = []

        if warmup_left > 0:
            warmup_left -= 1
        elif close is not None and ema50 is not None:
            if pos_qty > 0:
                if entry_px is None:
                    entry_px = close
                    peak_px = close
                    hold_bars = 0
                if close > peak_px:
                    peak_px = close
                hold_bars += 1
                ret = (close - entry_px) / entry_px
                trail = (peak_px - close) / peak_px if peak_px else 0.0
                sell = False
                if ret <= -SL:
                    sell = True
                elif ret >= TP:
                    sell = True
                elif ret > TRAIL_ARM and trail >= TRAIL:
                    sell = True
                elif hold_bars >= MAX_HOLD:
                    sell = True
                if sell:
                    orders.append(
                        {
                            "side": "sell",
                            "client_id": "s%d" % seq,
                            "symbol": symbol,
                            "qty": str(pos_qty),
                            "max_slippage_bps": 100,
                        }
                    )
            else:
                # Flat: look for a deep dip.
                dd = 0.0
                if equity_peak > 0:
                    dd = (equity_peak - equity) / equity_peak
                loss_limit = int(LOSS_LIMIT_FRAC * start_capital) if start_capital else 0
                depth = (ema50 - close) / ema50 if ema50 else 0.0
                if (
                    bars_seen >= MIN_BARS
                    and depth >= DEPTH
                    and realized > -loss_limit
                    and dd <= DD_GUARD
                    and cash > min_notional
                ):
                    # Respect the hello weight cap: position value after the
                    # buy may not exceed max_weight_bps of equity. Flat here,
                    # so equity == cash and the cap is cash * weight / 10000.
                    # At 10000 this is a no-op (full-size buy).
                    buy_notional = cash
                    if max_weight_bps < 10000:
                        buy_notional = min(
                            cash, equity * max_weight_bps // 10000
                        )
                    if buy_notional <= min_notional:
                        buy_notional = 0
                    if buy_notional > 0:
                        orders.append(
                            {
                                "side": "buy",
                                "client_id": "b%d" % seq,
                                "symbol": symbol,
                                "notional_quote_units": str(buy_notional),
                                "max_slippage_bps": 100,
                            }
                        )

        out.write(json.dumps({"type": "reply", "seq": seq, "orders": orders}) + "\n")
        out.flush()


if __name__ == "__main__":
    main()
