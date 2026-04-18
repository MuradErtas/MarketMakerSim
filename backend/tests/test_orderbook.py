"""Tests for the limit order book + matching engine."""
from app.orderbook import OrderBook


def test_add_and_top_of_book():
    ob = OrderBook()
    ob.add("buy", 99.0, 1.0, owner="noise")
    ob.add("buy", 100.0, 2.0, owner="noise")
    ob.add("sell", 101.0, 1.0, owner="noise")
    ob.add("sell", 102.0, 3.0, owner="noise")
    assert ob.best_bid() == 100.0
    assert ob.best_ask() == 101.0
    assert ob.mid() == 100.5
    assert ob.spread() == 1.0


def test_price_time_priority_matching():
    """Two resting bids at the same price: earlier order must fill first."""
    ob = OrderBook()
    ob.add("buy", 100.0, 1.0, owner="mm", ts=1.0)
    ob.add("buy", 100.0, 1.0, owner="noise", ts=2.0)

    trades = ob.match_market_order("sell", 1.0, taker_owner="noise")
    assert len(trades) == 1
    assert trades[0].maker_owner == "mm"
    assert trades[0].price == 100.0
    assert trades[0].size == 1.0

    # Second market sell should hit the remaining noise order
    trades = ob.match_market_order("sell", 1.0, taker_owner="noise")
    assert trades[0].maker_owner == "noise"


def test_partial_fill_and_level_walking():
    ob = OrderBook()
    ob.add("sell", 100.0, 1.0, owner="noise")
    ob.add("sell", 101.0, 2.0, owner="noise")

    trades = ob.match_market_order("buy", 2.5, taker_owner="noise")
    # Should fill 1.0 @ 100, 1.5 @ 101
    assert len(trades) == 2
    assert trades[0].price == 100.0 and trades[0].size == 1.0
    assert trades[1].price == 101.0 and trades[1].size == 1.5
    # 0.5 remaining at 101 still on book
    assert ob.best_ask() == 101.0


def test_cancel_owner_pulls_only_that_owner():
    ob = OrderBook()
    ob.add("buy", 100.0, 1.0, owner="mm")
    ob.add("buy", 100.0, 1.0, owner="noise")
    ob.add("sell", 101.0, 1.0, owner="mm")

    removed = ob.cancel_owner("mm")
    assert removed == 2
    assert ob.best_bid() == 100.0  # noise bid still there
    assert ob.best_ask() is None   # mm ask was the only one


def test_cancel_by_id():
    ob = OrderBook()
    o = ob.add("buy", 100.0, 1.0)
    assert ob.cancel(o.order_id) is True
    assert ob.best_bid() is None
    assert ob.cancel(9999) is False


def test_depth_snapshot_aggregates_sizes_at_level():
    ob = OrderBook()
    ob.add("buy", 100.0, 1.0, owner="mm")
    ob.add("buy", 100.0, 2.0, owner="noise")
    ob.add("buy", 99.0, 5.0, owner="noise")
    d = ob.depth(n_levels=2)
    assert d["bids"][0] == {"price": 100.0, "size": 3.0}
    assert d["bids"][1] == {"price": 99.0, "size": 5.0}
