"""PnL and performance metrics.

PnL convention
--------------
Realized PnL from a trade where the MM is a maker:
    BUY fill  (agent's bid hit):   pnl += -price * size  and  q += size
    SELL fill (agent's ask lifted): pnl += +price * size  and  q -= size

Mark-to-market equity at any instant:
    equity = cash + q * mid

We expose two PnL series:
    realized_pnl : cumulative cash flow from fills
    equity       : cash + inventory marked at mid (the number that matters)

Performance metrics on the equity series:
- Rolling Sharpe (annualized, using sim-step time granularity)
- Max drawdown
- Inventory mean, stdev
- Fill counts, fill rate
- Adverse selection proxy: average mid move (mid_{t+k} - fill_price)
  weighted by side, over a fixed lookahead k. Positive = bad for MM.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional

import numpy as np


@dataclass
class FillRecord:
    ts: float
    side: str       # "buy" or "sell" from the MM's perspective
    price: float
    size: float
    mid_at_fill: float


@dataclass
class Metrics:
    dt: float                       # sim step size in seconds
    sharpe_window: int = 600        # ~60 sec if dt=0.1
    drawdown_window: int = 6000     # ~10 min if dt=0.1
    adverse_horizon: int = 50       # ticks ahead to measure adverse selection

    cash: float = 0.0
    inventory: float = 0.0

    equity_series: List[float] = field(default_factory=list)
    mid_series: List[float] = field(default_factory=list)
    inventory_series: List[float] = field(default_factory=list)
    time_series: List[float] = field(default_factory=list)
    fills: List[FillRecord] = field(default_factory=list)

    # internal
    _equity_window: Deque[float] = field(default_factory=deque)
    _returns_window: Deque[float] = field(default_factory=deque)
    _peak_equity: float = 0.0
    _max_drawdown: float = 0.0

    # ---- state updates --------------------------------------------------
    def record_fill(self, ts: float, side: str, price: float, size: float,
                    mid: float) -> None:
        """Book a maker fill. ``side`` is from the MM's perspective."""
        if side == "buy":
            self.cash -= price * size
            self.inventory += size
        elif side == "sell":
            self.cash += price * size
            self.inventory -= size
        else:
            raise ValueError(f"unknown side {side!r}")
        self.fills.append(FillRecord(ts, side, price, size, mid))

    def tick(self, ts: float, mid: float) -> None:
        """Record one sim step (call every tick, after any fills)."""
        equity = self.cash + self.inventory * mid

        # Rolling drawdown
        self._peak_equity = max(self._peak_equity, equity)
        dd = self._peak_equity - equity
        if dd > self._max_drawdown:
            self._max_drawdown = dd

        # Rolling return for Sharpe
        if self._equity_window:
            ret = equity - self._equity_window[-1]
            self._returns_window.append(ret)
            if len(self._returns_window) > self.sharpe_window:
                self._returns_window.popleft()
        self._equity_window.append(equity)
        if len(self._equity_window) > self.sharpe_window:
            self._equity_window.popleft()

        self.equity_series.append(equity)
        self.mid_series.append(mid)
        self.inventory_series.append(self.inventory)
        self.time_series.append(ts)

    # ---- derived metrics -------------------------------------------------
    @property
    def equity(self) -> float:
        return self.equity_series[-1] if self.equity_series else 0.0

    @property
    def realized_pnl(self) -> float:
        return self.cash

    @property
    def max_drawdown(self) -> float:
        return self._max_drawdown

    def rolling_sharpe(self) -> float:
        """Annualized Sharpe on the rolling equity-return window.

        Uses 252*6.5*3600 seconds/year as the equity-trading annualization
        factor so the number is in a familiar scale, even though this is a
        synthetic sim.
        """
        if len(self._returns_window) < 30:
            return 0.0
        r = np.asarray(self._returns_window, dtype=float)
        mu = r.mean()
        sd = r.std(ddof=1)
        if sd <= 0:
            return 0.0
        ann = np.sqrt((252 * 6.5 * 3600.0) / self.dt)
        return float((mu / sd) * ann)

    def adverse_selection(self) -> float:
        """Average post-fill mid move signed against the MM.

        For a BUY fill the MM wants mid to rise; for a SELL fill the MM
        wants mid to fall.  We return the mean of `(mid_future - mid_fill)`
        with sign flipped so higher = more adverse selection cost per fill.
        """
        if not self.fills or len(self.mid_series) < self.adverse_horizon + 1:
            return 0.0
        tot = 0.0
        n = 0
        # fills reference times in time_series
        ts_to_idx = {t: i for i, t in enumerate(self.time_series)}
        for f in self.fills:
            i = ts_to_idx.get(f.ts)
            if i is None or i + self.adverse_horizon >= len(self.mid_series):
                continue
            future_mid = self.mid_series[i + self.adverse_horizon]
            move = future_mid - f.mid_at_fill
            signed = move if f.side == "sell" else -move
            tot += signed
            n += 1
        return tot / n if n else 0.0

    # ---- snapshot for the dashboard -------------------------------------
    def summary(self) -> dict:
        return {
            "cash": self.cash,
            "inventory": self.inventory,
            "equity": self.equity,
            "realized_pnl": self.realized_pnl,
            "max_drawdown": self.max_drawdown,
            "sharpe": self.rolling_sharpe(),
            "adverse_selection": self.adverse_selection(),
            "num_fills": len(self.fills),
        }
