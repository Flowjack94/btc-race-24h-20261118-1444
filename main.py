"""Momentum Ridge — a long-only cbBTC trend bot for make.fun's 24h BTC race.

Idea
----
cbBTC on 1-minute bars is mostly noise (typical 1-minute move ~5-7 bps) with
occasional multi-hour trends worth 100-200 bps. A full-size round trip costs
~26-36 bps in fees, slippage and pool impact, so the bot only trades when a
real regime move is under way and otherwise sits in cash.

Rules (all integer math, fully deterministic, no clock, no randomness):
  * Track the trailing 120-bar (2-hour) return of the close.
  * ENTER (flat, fully invested) when that return exceeds +25 bps.
  * EXIT the whole position when either:
      - the trailing 120-bar return falls below -40 bps, or
      - the close falls 100 bps below the highest close since entry
        (trailing stop).
  * After an entry, hold at least 60 bars before any exit can fire, so a
    1-minute noise spike cannot shake the bot out of a fresh position.
  * After an exit, wait 30 bars before the next entry.
  * Never trade during the warm-up batches (orders there are rejected anyway).
  * One order per reply at most; buys spend all cash, sells empty the position.

Why these numbers: backtested on the competition's dev window (24h of 1-minute
cbBTC bars, 2026-11-17 14:45 UTC -> 2026-11-18 14:44 UTC, a net -280 bps
falling day with one +195 bps rally in the middle), this system made about
+$7.75 net after every fee on $1,000 while buy-and-hold lost -$31.63. The
parameters sit in the middle of broad plateaus (entry +15..+40 bps, trailing
stop 80..150 bps, exit -50..-40 bps all end within a dollar or two of each
other), not on a sharp optimum, so the edge is the regime filter itself, not
a fitted constant.

Protocol: agent-fun/bars-replay/v1 via the kit's Python shim (vendor/).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

# --- Strategy constants (basis points unless noted) ---
LOOKBACK_BARS = 120      # 2-hour trailing return window
ENTRY_BPS = 25           # enter when trailing 120-bar return > +25 bps
EXIT_BPS = 40            # exit when trailing 120-bar return < -40 bps
TRAIL_BPS = 100          # trailing stop: exit 100 bps below peak since entry
MIN_HOLD_BARS = 60       # no exit before 60 bars after the entry fills
COOLDOWN_BARS = 30       # wait this long after an exit before re-entering
MAX_SLIPPAGE_BPS = 300   # 1-minute moves are <70 bps; 300 leaves ample room

SYMBOL = None            # set from hello: the universe's only symbol
closes = []              # closes seen so far, oldest first (ints, price scale 5)
entry_seq = None         # seq of the batch the position was first observed in
high_since_entry = None  # highest close seen while in the position
cool_until_seq = -1      # no new entry before this seq


def on_hello(state):
    global SYMBOL
    SYMBOL = state.hello["symbols"][0]["symbol"]


def _bps_above(now, then, bps):
    """True when now sits more than `bps` basis points above then (exact ints)."""
    return now * 10000 > then * (10000 + bps)


def _bps_below(now, then, bps):
    """True when now sits more than `bps` basis points below then (exact ints)."""
    return now * 10000 < then * (10000 - bps)


def _momentum():
    """The trailing LOOKBACK_BARS return as (now, then) closes, or None.

    `then` is the close LOOKBACK_BARS bars back, so (now - then) / then is the
    trailing return; callers compare it with _bps_above/_bps_below.
    """
    if len(closes) < LOOKBACK_BARS + 1:
        return None
    return closes[-1], closes[-LOOKBACK_BARS - 1]


def on_batch(state, batch):
    # Record this batch's bar (a minute with no sample carries no bar).
    for bar in batch.get("bars", []):
        if bar.get("symbol") == SYMBOL:
            closes.append(int(bar["c"]))
            break

    if state.warming_up:
        return []

    holding = state.positions.get(SYMBOL)
    is_long = holding is not None and holding.qty > 0
    close = state.close(SYMBOL)
    if close is None:
        return []

    if is_long:
        global entry_seq, high_since_entry
        if entry_seq is None:
            # The buy filled: the position appeared in this batch's account.
            entry_seq = state.seq
            high_since_entry = close
        if close > high_since_entry:
            high_since_entry = close
        if state.seq - entry_seq < MIN_HOLD_BARS:
            return []
        # Trailing stop: 100 bps below the peak since entry.
        if _bps_below(close, high_since_entry, TRAIL_BPS):
            return [_sell_all(state)]
        # Momentum turned: trailing 120-bar return below -40 bps.
        mom = _momentum()
        if mom is not None and _bps_below(mom[0], mom[1], EXIT_BPS):
            return [_sell_all(state)]
        return []

    # Flat: reset entry tracking the moment the position is observed gone.
    if entry_seq is not None:
        entry_seq = None
        high_since_entry = None
    if state.seq < cool_until_seq:
        return []
    mom = _momentum()
    if mom is None:
        return []
    # Enter when the trailing 120-bar return exceeds +25 bps, fully invested.
    if _bps_above(mom[0], mom[1], ENTRY_BPS):
        notional = min(state.cash, state.weight_room(SYMBOL))
        if notional < int(state.hello["fees"]["min_notional_quote_units"]):
            return []
        return [{
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": notional,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]
    return []


def _sell_all(state):
    global cool_until_seq
    cool_until_seq = state.seq + COOLDOWN_BARS
    holding = state.positions.get(SYMBOL)
    return {
        "side": "sell",
        "symbol": SYMBOL,
        "qty": holding.qty,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }


makefun_bars.run(on_batch, on_hello=on_hello)
