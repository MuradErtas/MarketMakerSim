"""Simulation parameters.

All parameters are grouped in a single Pydantic model so they can be
updated live from the dashboard via WebSocket / REST.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SimParams(BaseModel):
    """Parameters controlling the simulation.

    Attributes
    ----------
    dt : float
        Length of one simulation step in seconds. The A-S time horizon
        is expressed in the same units.
    T : float
        Trading horizon (seconds) over which the A-S objective is defined.
        The simulator loops: each "episode" ends at T and resets inventory
        bookkeeping but keeps cumulative PnL.
    s0 : float
        Initial mid price.
    tick_size : float
        Minimum price increment on the book.
    gamma : float
        Risk aversion / inventory penalty.  Larger gamma => tighter
        inventory control, wider spreads.
    k : float
        Liquidity parameter in the fill intensity lambda = A * exp(-k*delta).
        Larger k => fills fall off faster with distance from mid.
    A : float
        Base order arrival intensity per side (orders per second at delta=0).
    sigma_low : float
        Mid-price volatility per sqrt(second) in the low-vol regime.
    sigma_high : float
        Mid-price volatility per sqrt(second) in the high-vol regime.
    p_low_to_high : float
        Probability per step of switching from low -> high regime.
    p_high_to_low : float
        Probability per step of switching from high -> low regime.
    quote_size : float
        Size posted at each side by the MM agent.
    max_inventory : float
        Hard cap on absolute inventory. If exceeded, one side is pulled.
    seed : int | None
        RNG seed for reproducibility.
    """

    dt: float = Field(default=0.1, gt=0)
    T: float = Field(default=60.0, gt=0)
    s0: float = Field(default=100.0, gt=0)
    tick_size: float = Field(default=0.01, gt=0)

    gamma: float = Field(default=0.1, gt=0)
    k: float = Field(default=1.5, gt=0)
    A: float = Field(default=1.4, gt=0)

    sigma_low: float = Field(default=0.3, gt=0)
    sigma_high: float = Field(default=1.2, gt=0)
    p_low_to_high: float = Field(default=0.002, ge=0, le=1)
    p_high_to_low: float = Field(default=0.01, ge=0, le=1)

    quote_size: float = Field(default=1.0, gt=0)
    max_inventory: float = Field(default=50.0, gt=0)

    seed: int | None = None


DEFAULT_PARAMS = SimParams()
