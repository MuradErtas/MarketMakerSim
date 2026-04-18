"""Avellaneda-Stoikov optimal market-making agent.

Reference: Avellaneda & Stoikov, "High-frequency trading in a limit order
book" (2008).  Key formulas (arithmetic mid):

    Reservation price:
        r(s, q, t) = s - q * gamma * sigma^2 * (T - t)

    Optimal bid-ask spread around r:
        delta_ask + delta_bid = gamma * sigma^2 * (T - t)
                                + (2 / gamma) * ln(1 + gamma / k)

    Quotes:
        bid = r - spread/2,  ask = r + spread/2

Interpretation:
- gamma: inventory risk aversion. Higher gamma tilts r away from s as q grows,
  making the agent quote asymmetrically to unload inventory.
- k: liquidity parameter of the fill-intensity curve lambda = A exp(-k delta).
  Higher k means fills drop off fast, so optimal spread widens.
- (T - t): urgency. Closer to horizon => less inventory risk => spread shrinks.

Extensions added on top of the base model:
- Hard inventory cap: if |q| >= max_inventory we pull the quote on the
  side that would worsen inventory.
- Adverse-selection-safe minimum half-spread of 1 tick.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class ASQuote:
    bid: float
    ask: float
    reservation: float
    spread: float
    # deltas are distances from mid (useful for fill intensity)
    delta_bid: float
    delta_ask: float


@dataclass
class ASAgent:
    gamma: float
    k: float
    T: float
    tick_size: float
    max_inventory: float
    min_half_spread_ticks: int = 1

    def quote(
        self,
        mid: float,
        inventory: float,
        t: float,
        sigma: float,
    ) -> ASQuote:
        """Produce optimal bid/ask given current mid, inventory and time.

        Parameters
        ----------
        mid : current mid price s_t.
        inventory : signed inventory q (positive = long).
        t : elapsed time within the current episode.
        sigma : current volatility estimate (per sqrt(second)).
        """
        tau = max(self.T - t, 1e-8)

        # Reservation price
        r = mid - inventory * self.gamma * (sigma ** 2) * tau

        # Optimal total spread
        spread = self.gamma * (sigma ** 2) * tau + (2.0 / self.gamma) * np.log1p(self.gamma / self.k)

        # Enforce min spread of 2 * min_half_spread_ticks
        spread = max(spread, 2 * self.min_half_spread_ticks * self.tick_size)

        bid = r - spread / 2.0
        ask = r + spread / 2.0

        # Snap to tick grid (round bid down, ask up to keep spread wider,
        # not tighter, than optimal).
        bid = np.floor(bid / self.tick_size) * self.tick_size
        ask = np.ceil(ask / self.tick_size) * self.tick_size

        # Ensure the book is crossable-safe: bid < ask
        if ask <= bid:
            ask = bid + self.tick_size

        # Deltas from mid
        delta_bid = max(mid - bid, 0.0)
        delta_ask = max(ask - mid, 0.0)

        # Hard inventory throttle
        if inventory >= self.max_inventory:
            # already too long => don't buy more
            delta_bid_out: Optional[float] = None
            bid_out: Optional[float] = None
        else:
            delta_bid_out = delta_bid
            bid_out = bid

        if inventory <= -self.max_inventory:
            delta_ask_out: Optional[float] = None
            ask_out: Optional[float] = None
        else:
            delta_ask_out = delta_ask
            ask_out = ask

        return ASQuote(
            bid=bid_out if bid_out is not None else float("nan"),
            ask=ask_out if ask_out is not None else float("nan"),
            reservation=r,
            spread=spread,
            delta_bid=delta_bid_out if delta_bid_out is not None else float("nan"),
            delta_ask=delta_ask_out if delta_ask_out is not None else float("nan"),
        )
