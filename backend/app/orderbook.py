"""Price-time priority limit order book.

This is deliberately simple but correct:
- Bids and asks are stored as sorted dicts of price -> deque of orders.
- Orders carry ``owner`` so we can distinguish the MM agent's fills
  from noise-trader fills.
- `match_market_order` consumes liquidity from the opposite side at
  successive price levels and returns a list of ``Trade`` records.

For a ~100 ops/sec simulation this is more than fast enough; if the
simulation ever needs to scale, swap the SortedDict for a skiplist or
array-backed book.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Iterable, List, Literal, Optional

Side = Literal["buy", "sell"]


@dataclass
class Order:
    order_id: int
    side: Side
    price: float
    size: float
    owner: str = "noise"  # "mm" or "noise"
    ts: float = 0.0


@dataclass
class Trade:
    price: float
    size: float
    aggressor: Side         # side of the taker (market order)
    maker_owner: str        # who provided liquidity: "mm" or "noise"
    taker_owner: str        # who consumed liquidity
    ts: float = 0.0


@dataclass
class OrderBook:
    """Very small LOB with strict price-time priority.

    We keep two dicts of price -> deque[Order]. Best-bid is max(bids.keys()),
    best-ask is min(asks.keys()). Keep a cached "best" for O(1) reads by
    scanning dict keys; the book is small (a handful of levels) so this is
    cheap enough.
    """

    bids: Dict[float, Deque[Order]] = field(default_factory=dict)
    asks: Dict[float, Deque[Order]] = field(default_factory=dict)
    _next_order_id: int = 1

    # ------------------------------------------------------------------ add
    def add(self, side: Side, price: float, size: float, owner: str = "noise",
            ts: float = 0.0) -> Order:
        """Post a resting limit order. Returns the Order (with id)."""
        book = self.bids if side == "buy" else self.asks
        q = book.setdefault(price, deque())
        order = Order(
            order_id=self._next_order_id,
            side=side,
            price=price,
            size=size,
            owner=owner,
            ts=ts,
        )
        self._next_order_id += 1
        q.append(order)
        return order

    # --------------------------------------------------------------- cancel
    def cancel(self, order_id: int) -> bool:
        """Cancel an order by id. Returns True if found."""
        for book in (self.bids, self.asks):
            for price, q in list(book.items()):
                for o in list(q):
                    if o.order_id == order_id:
                        q.remove(o)
                        if not q:
                            del book[price]
                        return True
        return False

    def cancel_owner(self, owner: str) -> int:
        """Cancel every resting order belonging to ``owner``. Returns count."""
        removed = 0
        for book in (self.bids, self.asks):
            for price in list(book.keys()):
                q = book[price]
                keep = deque(o for o in q if o.owner != owner)
                removed += len(q) - len(keep)
                if keep:
                    book[price] = keep
                else:
                    del book[price]
        return removed

    # ------------------------------------------------------------- top-book
    def best_bid(self) -> Optional[float]:
        return max(self.bids.keys()) if self.bids else None

    def best_ask(self) -> Optional[float]:
        return min(self.asks.keys()) if self.asks else None

    def mid(self) -> Optional[float]:
        b, a = self.best_bid(), self.best_ask()
        if b is None or a is None:
            return None
        return 0.5 * (b + a)

    def spread(self) -> Optional[float]:
        b, a = self.best_bid(), self.best_ask()
        if b is None or a is None:
            return None
        return a - b

    # --------------------------------------------------------------- depth
    def depth(self, n_levels: int = 10) -> Dict[str, List[Dict[str, float]]]:
        """Return top-n aggregated depth per side for the dashboard."""
        bid_prices = sorted(self.bids.keys(), reverse=True)[:n_levels]
        ask_prices = sorted(self.asks.keys())[:n_levels]
        return {
            "bids": [
                {"price": p, "size": sum(o.size for o in self.bids[p])}
                for p in bid_prices
            ],
            "asks": [
                {"price": p, "size": sum(o.size for o in self.asks[p])}
                for p in ask_prices
            ],
        }

    # -------------------------------------------------------------- matching
    def match_market_order(
        self,
        side: Side,
        size: float,
        taker_owner: str = "noise",
        ts: float = 0.0,
    ) -> List[Trade]:
        """Execute a market order against the book.

        Walks price levels best-first, consuming resting orders in FIFO order
        until ``size`` is filled or the book is exhausted.  Returns the list
        of individual trades (one per maker order touched).
        """
        trades: List[Trade] = []
        opposite = self.asks if side == "buy" else self.bids
        prices_best_first: Iterable[float] = (
            sorted(opposite.keys()) if side == "buy"
            else sorted(opposite.keys(), reverse=True)
        )

        remaining = size
        for price in list(prices_best_first):
            if remaining <= 0:
                break
            q = opposite[price]
            while q and remaining > 0:
                maker = q[0]
                take = min(maker.size, remaining)
                trades.append(Trade(
                    price=price,
                    size=take,
                    aggressor=side,
                    maker_owner=maker.owner,
                    taker_owner=taker_owner,
                    ts=ts,
                ))
                maker.size -= take
                remaining -= take
                if maker.size <= 0:
                    q.popleft()
            if not q:
                del opposite[price]

        return trades

    # ------------------------------------------------------------------ len
    def __len__(self) -> int:
        return sum(len(q) for q in self.bids.values()) + \
               sum(len(q) for q in self.asks.values())
