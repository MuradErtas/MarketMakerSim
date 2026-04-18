"""Exogenous mid-price process and noise-trader order flow.

Two pieces:

1. ``RegimeVolatility``
   A 2-state Markov chain between "low" and "high" volatility regimes.
   Each step returns the current sigma (per sqrt(second)) to use for the
   mid-price Brownian increment.

2. ``PoissonFlow``
   Market-order arrivals on each side follow a Poisson process with
   intensity

       lambda(delta) = A * exp(-k * delta)

   where delta is the distance between the *agent's* quote and the mid,
   measured in price units.  This is the standard Avellaneda-Stoikov
   fill-intensity form and makes fills rarer as we quote further out.
   The size of each arriving market order is drawn from an exponential
   distribution by default (fat-ish tails).

The two pieces are kept separate so a backtest or a Hawkes extension
can drop into the same place without touching the simulator.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np

Regime = Literal["low", "high"]


@dataclass
class RegimeVolatility:
    """Two-state regime-switching volatility."""

    sigma_low: float
    sigma_high: float
    p_low_to_high: float
    p_high_to_low: float
    rng: np.random.Generator
    state: Regime = "low"

    def step(self) -> float:
        """Advance one tick; return the sigma to use on this tick."""
        if self.state == "low":
            if self.rng.random() < self.p_low_to_high:
                self.state = "high"
        else:
            if self.rng.random() < self.p_high_to_low:
                self.state = "low"
        return self.sigma_low if self.state == "low" else self.sigma_high


@dataclass
class MidPriceProcess:
    """Geometric-BM-ish mid with regime-dependent vol.

    We use arithmetic Brownian motion on mid to keep the A-S closed-form
    valid (A-S assumes arithmetic).  In practice this is fine over the
    short horizons the sim runs for.
    """

    s: float
    vol: RegimeVolatility
    dt: float
    rng: np.random.Generator

    def step(self) -> float:
        sigma = self.vol.step()
        self.s = self.s + sigma * np.sqrt(self.dt) * self.rng.standard_normal()
        return self.s


@dataclass
class PoissonFlow:
    """Generate market orders hitting the agent's quotes.

    Per step we draw Bernoulli(lambda * dt) on each side. For small
    lambda*dt this is a valid discretization of a Poisson process and
    cheaper than sampling inter-arrival times.
    """

    A: float
    k: float
    rng: np.random.Generator
    avg_size: float = 1.0  # mean exponential order size

    def arrival_prob(self, delta: float, dt: float) -> float:
        """Probability of a market order hitting a quote at distance delta."""
        lam = self.A * np.exp(-self.k * max(delta, 0.0))
        # first-order approximation to 1 - exp(-lam*dt), good for small lam*dt
        return min(1.0, lam * dt)

    def sample_step(
        self,
        delta_bid: Optional[float],
        delta_ask: Optional[float],
        dt: float,
    ) -> tuple[Optional[float], Optional[float]]:
        """Returns (bid_fill_size, ask_fill_size) each possibly None.

        A non-None bid_fill_size means a market SELL hit the agent's bid.
        A non-None ask_fill_size means a market BUY hit the agent's ask.
        """
        bid_fill = None
        ask_fill = None
        if delta_bid is not None and self.rng.random() < self.arrival_prob(delta_bid, dt):
            bid_fill = float(self.rng.exponential(self.avg_size))
        if delta_ask is not None and self.rng.random() < self.arrival_prob(delta_ask, dt):
            ask_fill = float(self.rng.exponential(self.avg_size))
        return bid_fill, ask_fill
