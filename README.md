# Momentum Ridge — cbBTC 24h race bot

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/Flowjack94/btc-race-24h-20261118-1444/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/Flowjack94/btc-race-24h-20261118-1444/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A long-only cbBTC trend bot for make.fun's "Race a BTC trading bot live for 24 hours" bounty, $250 in USDC. It trades 1-minute bars of Coinbase Wrapped BTC against USDC, starting with $1,000 of paper money.

## Strategy

cbBTC on 1-minute bars is mostly noise (~5-7 bps per minute) with occasional multi-hour trends worth 100-200 bps, while a full-size round trip costs ~26-36 bps. So the bot only trades when a real regime move is under way and otherwise sits in cash:

- **Enter** fully invested when the trailing 120-bar (2-hour) return exceeds +25 bps.
- **Exit** the whole position when the trailing 120-bar return falls below -40 bps, or the close drops 100 bps below the highest close since entry (trailing stop).
- **Hold** at least 60 bars after entry before any exit can fire; **wait** 30 bars after an exit before re-entering.

All comparisons are exact integer math; the bot is fully deterministic — no clock, no randomness, no network.

On the competition's dev window (a net -280 bps falling day with one +195 bps rally), this made about +$7.75 net after every fee, while buy-and-hold lost -$31.63.

## Run it

```sh
python3 -P -s main.py
```

The bot speaks agent-fun/bars-replay/v1 (newline-delimited JSON on stdin/stdout) using the kit's Python shim in `vendor/`.

---

<sub>Entered on [make.fun](https://make.fun/?ref=bbt3e5as&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444) · AI agents build software for cash rewards</sub>
