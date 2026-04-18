"""Sanity tests for Avellaneda-Stoikov quote math."""
import math

from app.agent import ASAgent


def _make_agent(**kw):
    defaults = dict(gamma=0.1, k=1.5, T=60.0, tick_size=0.01, max_inventory=50.0)
    defaults.update(kw)
    return ASAgent(**defaults)


def test_neutral_inventory_symmetric_quotes():
    ag = _make_agent()
    q = ag.quote(mid=100.0, inventory=0.0, t=0.0, sigma=1.0)
    assert abs((100.0 - q.bid) - (q.ask - 100.0)) <= 0.02  # symmetric within a tick


def test_long_inventory_skews_quotes_down():
    """Long inventory => reservation below mid => both quotes shift down."""
    ag = _make_agent()
    q0 = ag.quote(mid=100.0, inventory=0.0, t=0.0, sigma=1.0)
    q_long = ag.quote(mid=100.0, inventory=10.0, t=0.0, sigma=1.0)
    assert q_long.reservation < q0.reservation
    assert q_long.bid < q0.bid
    assert q_long.ask < q0.ask


def test_short_inventory_skews_quotes_up():
    ag = _make_agent()
    q0 = ag.quote(mid=100.0, inventory=0.0, t=0.0, sigma=1.0)
    q_short = ag.quote(mid=100.0, inventory=-10.0, t=0.0, sigma=1.0)
    assert q_short.reservation > q0.reservation
    assert q_short.bid > q0.bid
    assert q_short.ask > q0.ask


def test_higher_vol_widens_spread():
    ag = _make_agent()
    q_lo = ag.quote(mid=100.0, inventory=0.0, t=0.0, sigma=0.5)
    q_hi = ag.quote(mid=100.0, inventory=0.0, t=0.0, sigma=2.0)
    assert q_hi.spread > q_lo.spread


def test_spread_shrinks_toward_horizon():
    """As t -> T the inventory-risk component vanishes, spread narrows."""
    ag = _make_agent()
    q_early = ag.quote(mid=100.0, inventory=0.0, t=0.0, sigma=1.0)
    q_late = ag.quote(mid=100.0, inventory=0.0, t=55.0, sigma=1.0)
    assert q_late.spread <= q_early.spread + 1e-9


def test_hard_inventory_cap_pulls_quote():
    ag = _make_agent(max_inventory=5.0)
    q = ag.quote(mid=100.0, inventory=10.0, t=0.0, sigma=1.0)
    # inventory way over cap => bid should be pulled (NaN)
    assert math.isnan(q.bid)
    assert not math.isnan(q.ask)


def test_bid_strictly_below_ask():
    ag = _make_agent()
    for inv in [-20.0, -5.0, 0.0, 5.0, 20.0]:
        q = ag.quote(mid=100.0, inventory=inv, t=0.0, sigma=1.0)
        if not math.isnan(q.bid) and not math.isnan(q.ask):
            assert q.bid < q.ask
