"""Main simulation loop.

Flow per tick:
    1. Mid moves according to regime-switching Brownian motion.
    2. MM cancels stale quotes and posts fresh bid/ask from A-S.
    3. Noise-trader flow may hit bid and/or ask (Poisson w/ intensity
       that decays in the distance-from-mid).
    4. Any fills against the MM are booked.
    5. Metrics are updated and a compact snapshot is emitted.

The simulator is driven by an ``async step()`` / ``async run()`` so the
FastAPI WebSocket layer can await each tick, yield a frame to the client,
and sleep for ``dt`` wall-clock seconds to animate.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .agent import ASAgent, ASQuote
from .config import SimParams
from .flow import MidPriceProcess, PoissonFlow, RegimeVolatility
from .metrics import Metrics
from .orderbook import OrderBook, Order


@dataclass
class Simulator:
    params: SimParams

    # runtime state
    t: float = 0.0
    step_idx: int = 0
    episode_t: float = 0.0
    book: OrderBook = field(default_factory=OrderBook)
    metrics: Metrics = field(init=False)
    rng: np.random.Generator = field(init=False)
    vol: RegimeVolatility = field(init=False)
    mid_proc: MidPriceProcess = field(init=False)
    flow: PoissonFlow = field(init=False)
    agent: ASAgent = field(init=False)
    last_quote: Optional[ASQuote] = None
    last_orders: tuple[Optional[Order], Optional[Order]] = (None, None)

    def __post_init__(self) -> None:
        self.reset()

    # ------------------------------------------------------------------ reset
    def reset(self) -> None:
        p = self.params
        self.rng = np.random.default_rng(p.seed)
        self.vol = RegimeVolatility(
            sigma_low=p.sigma_low,
            sigma_high=p.sigma_high,
            p_low_to_high=p.p_low_to_high,
            p_high_to_low=p.p_high_to_low,
            rng=self.rng,
        )
        self.mid_proc = MidPriceProcess(s=p.s0, vol=self.vol, dt=p.dt, rng=self.rng)
        self.flow = PoissonFlow(A=p.A, k=p.k, rng=self.rng)
        self.agent = ASAgent(
            gamma=p.gamma, k=p.k, T=p.T,
            tick_size=p.tick_size, max_inventory=p.max_inventory,
        )
        self.metrics = Metrics(dt=p.dt)
        self.book = OrderBook()
        self.t = 0.0
        self.episode_t = 0.0
        self.step_idx = 0
        self.last_quote = None
        self.last_orders = (None, None)

    # ------------------------------------------------------ param hot-swap
    def update_params(self, **kwargs) -> None:
        """Update one or more parameters without resetting PnL.

        We DO rebuild the stochastic components (flow/vol/agent) because
        they reference the params, but keep ``metrics`` and ``book``.
        """
        self.params = self.params.model_copy(update=kwargs)
        p = self.params
        self.vol.sigma_low = p.sigma_low
        self.vol.sigma_high = p.sigma_high
        self.vol.p_low_to_high = p.p_low_to_high
        self.vol.p_high_to_low = p.p_high_to_low
        self.flow.A = p.A
        self.flow.k = p.k
        self.agent.gamma = p.gamma
        self.agent.k = p.k
        self.agent.T = p.T
        self.agent.tick_size = p.tick_size
        self.agent.max_inventory = p.max_inventory
        self.mid_proc.dt = p.dt
        self.metrics.dt = p.dt

    # ------------------------------------------------------------------ step
    def step(self) -> dict:
        """Advance the simulation one tick and return a snapshot."""
        p = self.params

        # 1. mid moves
        mid = self.mid_proc.step()

        # 2. episode handling: A-S horizon loops so sim can run forever
        if self.episode_t >= p.T:
            self.episode_t = 0.0

        # 3. agent re-quotes
        # Use current sigma from regime for the A-S calc
        sigma_now = p.sigma_low if self.vol.state == "low" else p.sigma_high
        quote = self.agent.quote(
            mid=mid,
            inventory=self.metrics.inventory,
            t=self.episode_t,
            sigma=sigma_now,
        )
        self.last_quote = quote

        # Cancel stale MM orders and repost (small-sim regime)
        self.book.cancel_owner("mm")
        bid_ord = ask_ord = None
        if not np.isnan(quote.bid):
            bid_ord = self.book.add("buy", float(quote.bid), p.quote_size,
                                    owner="mm", ts=self.t)
        if not np.isnan(quote.ask):
            ask_ord = self.book.add("sell", float(quote.ask), p.quote_size,
                                    owner="mm", ts=self.t)
        self.last_orders = (bid_ord, ask_ord)

        # 4. noise flow sampling
        delta_bid = None if np.isnan(quote.delta_bid) else float(quote.delta_bid)
        delta_ask = None if np.isnan(quote.delta_ask) else float(quote.delta_ask)
        bid_fill_size, ask_fill_size = self.flow.sample_step(
            delta_bid, delta_ask, p.dt,
        )

        # Clamp to the quoted size (we only posted `quote_size`)
        # The maker fill is the min of order-size and our resting size.
        if bid_fill_size is not None:
            # Market SELL hits our bid => we BUY at bid
            trades = self.book.match_market_order(
                side="sell", size=bid_fill_size, taker_owner="noise", ts=self.t,
            )
            for tr in trades:
                if tr.maker_owner == "mm":
                    self.metrics.record_fill(
                        ts=self.t, side="buy", price=tr.price,
                        size=tr.size, mid=mid,
                    )

        if ask_fill_size is not None:
            # Market BUY hits our ask => we SELL at ask
            trades = self.book.match_market_order(
                side="buy", size=ask_fill_size, taker_owner="noise", ts=self.t,
            )
            for tr in trades:
                if tr.maker_owner == "mm":
                    self.metrics.record_fill(
                        ts=self.t, side="sell", price=tr.price,
                        size=tr.size, mid=mid,
                    )

        # 5. metrics tick
        self.metrics.tick(self.t, mid)

        # 6. advance clock
        self.t += p.dt
        self.episode_t += p.dt
        self.step_idx += 1

        return self.snapshot(mid, quote)

    # -------------------------------------------------------------- snapshot
    def snapshot(self, mid: float, quote: ASQuote) -> dict:
        """Serializable state for the dashboard frame."""
        recent_fills = self.metrics.fills[-20:]
        return {
            "t": self.t,
            "step": self.step_idx,
            "mid": mid,
            "regime": self.vol.state,
            "sigma": self.params.sigma_low if self.vol.state == "low"
                     else self.params.sigma_high,
            "quote": {
                "bid": None if np.isnan(quote.bid) else float(quote.bid),
                "ask": None if np.isnan(quote.ask) else float(quote.ask),
                "reservation": float(quote.reservation),
                "spread": float(quote.spread),
            },
            "book": self.book.depth(n_levels=10),
            "metrics": self.metrics.summary(),
            "recent_fills": [
                {
                    "t": f.ts, "side": f.side, "price": f.price,
                    "size": f.size, "mid": f.mid_at_fill,
                }
                for f in recent_fills
            ],
            "params": self.params.model_dump(),
        }

    # --------------------------------------------------------------- async run
    async def run(self, tick_hz: float = 20.0):
        """Async generator yielding snapshots at roughly ``tick_hz`` per second."""
        period = 1.0 / tick_hz
        while True:
            yield self.step()
            await asyncio.sleep(period)
