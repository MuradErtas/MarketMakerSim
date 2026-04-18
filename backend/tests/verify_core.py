"""Standalone verification script for the core engine.

Mirrors the pytest suite but only uses stdlib + numpy so it can run in
environments without pytest.  Exits non-zero on failure.
"""
import math
import sys

sys.path.insert(0, ".")

from app.orderbook import OrderBook
from app.agent import ASAgent
from app.metrics import Metrics

import numpy as np

FAILED = []

def check(name, cond):
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAILED.append(name)
    print(f"  [{status}] {name}")


print("=== OrderBook ===")
ob = OrderBook()
ob.add("buy", 99.0, 1.0)
ob.add("buy", 100.0, 2.0)
ob.add("sell", 101.0, 1.0)
ob.add("sell", 102.0, 3.0)
check("best_bid=100", ob.best_bid() == 100.0)
check("best_ask=101", ob.best_ask() == 101.0)
check("mid=100.5", ob.mid() == 100.5)
check("spread=1", ob.spread() == 1.0)

ob = OrderBook()
ob.add("buy", 100.0, 1.0, owner="mm", ts=1.0)
ob.add("buy", 100.0, 1.0, owner="noise", ts=2.0)
trades = ob.match_market_order("sell", 1.0)
check("FIFO: first trade is mm", trades[0].maker_owner == "mm" and trades[0].size == 1.0)
trades = ob.match_market_order("sell", 1.0)
check("FIFO: second trade is noise", trades[0].maker_owner == "noise")

ob = OrderBook()
ob.add("sell", 100.0, 1.0)
ob.add("sell", 101.0, 2.0)
trades = ob.match_market_order("buy", 2.5)
check("level walk: two trades", len(trades) == 2)
check("level walk: first @100 size 1", trades[0].price == 100.0 and trades[0].size == 1.0)
check("level walk: second @101 size 1.5", trades[1].price == 101.0 and trades[1].size == 1.5)
check("level walk: remainder at 101", ob.best_ask() == 101.0)

ob = OrderBook()
ob.add("buy", 100.0, 1.0, owner="mm")
ob.add("buy", 100.0, 1.0, owner="noise")
ob.add("sell", 101.0, 1.0, owner="mm")
removed = ob.cancel_owner("mm")
check("cancel_owner removes exactly mm orders", removed == 2)
check("cancel_owner leaves noise bid", ob.best_bid() == 100.0)
check("cancel_owner empties asks", ob.best_ask() is None)

ob = OrderBook()
o = ob.add("buy", 100.0, 1.0)
check("cancel by id", ob.cancel(o.order_id) is True)
check("cancel unknown id returns False", ob.cancel(999) is False)

ob = OrderBook()
ob.add("buy", 100.0, 1.0, owner="mm")
ob.add("buy", 100.0, 2.0, owner="noise")
ob.add("buy", 99.0, 5.0, owner="noise")
d = ob.depth(n_levels=2)
check("depth aggregates sizes at level", d["bids"][0] == {"price": 100.0, "size": 3.0})
check("depth: second level present", d["bids"][1] == {"price": 99.0, "size": 5.0})


print("\n=== A-S Agent ===")
def _agent(**kw):
    defaults = dict(gamma=0.1, k=1.5, T=60.0, tick_size=0.01, max_inventory=50.0)
    defaults.update(kw)
    return ASAgent(**defaults)

ag = _agent()
q = ag.quote(mid=100.0, inventory=0.0, t=0.0, sigma=1.0)
check("neutral inventory ~symmetric", abs((100.0 - q.bid) - (q.ask - 100.0)) <= 0.02)

q0 = ag.quote(mid=100.0, inventory=0.0, t=0.0, sigma=1.0)
qL = ag.quote(mid=100.0, inventory=10.0, t=0.0, sigma=1.0)
check("long inventory => reservation < mid", qL.reservation < q0.reservation)
check("long inventory => bid shifts down", qL.bid < q0.bid)
check("long inventory => ask shifts down", qL.ask < q0.ask)

qS = ag.quote(mid=100.0, inventory=-10.0, t=0.0, sigma=1.0)
check("short inventory => reservation > mid", qS.reservation > q0.reservation)
check("short inventory => bid shifts up", qS.bid > q0.bid)
check("short inventory => ask shifts up", qS.ask > q0.ask)

q_lo = ag.quote(mid=100.0, inventory=0.0, t=0.0, sigma=0.5)
q_hi = ag.quote(mid=100.0, inventory=0.0, t=0.0, sigma=2.0)
check("higher vol => wider spread", q_hi.spread > q_lo.spread)

q_early = ag.quote(mid=100.0, inventory=0.0, t=0.0, sigma=1.0)
q_late = ag.quote(mid=100.0, inventory=0.0, t=55.0, sigma=1.0)
check("spread narrows toward horizon", q_late.spread <= q_early.spread + 1e-9)

ag_cap = _agent(max_inventory=5.0)
q_cap = ag_cap.quote(mid=100.0, inventory=10.0, t=0.0, sigma=1.0)
check("hard cap pulls bid when long", math.isnan(q_cap.bid))
check("hard cap keeps ask when long", not math.isnan(q_cap.ask))

for inv in [-20.0, -5.0, 0.0, 5.0, 20.0]:
    q = ag.quote(mid=100.0, inventory=inv, t=0.0, sigma=1.0)
    if not math.isnan(q.bid) and not math.isnan(q.ask):
        check(f"bid<ask at inv={inv}", q.bid < q.ask)


print("\n=== Metrics ===")
m = Metrics(dt=0.1)
m.record_fill(ts=0.0, side="buy", price=100.0, size=1.0, mid=100.0)
check("buy increments inventory", m.inventory == 1.0)
check("buy debits cash", m.cash == -100.0)
m.record_fill(ts=1.0, side="sell", price=101.0, size=1.0, mid=101.0)
check("sell zeros inventory", m.inventory == 0.0)
check("realized pnl = 1.0", m.cash == 1.0)

m = Metrics(dt=0.1)
m.record_fill(ts=0.0, side="buy", price=100.0, size=1.0, mid=100.0)
m.tick(0.0, 100.0)
check("equity zero at entry", m.equity == 0.0)
m.tick(0.1, 105.0)
check("equity marks to mid", m.equity == 5.0)

m = Metrics(dt=0.1)
m.record_fill(ts=0.0, side="buy", price=100.0, size=1.0, mid=100.0)
for i, mid in enumerate([100.0, 105.0, 110.0, 95.0, 90.0]):
    m.tick(i * 0.1, mid)
check("max drawdown = 20", m.max_drawdown == 20.0)

m = Metrics(dt=1.0, sharpe_window=200)
m.record_fill(ts=0.0, side="buy", price=100.0, size=1.0, mid=100.0)
rng = np.random.default_rng(0)
mid = 100.0
for i in range(200):
    mid += 0.5 + rng.standard_normal() * 0.1
    m.tick(i * 1.0, mid)
s = m.rolling_sharpe()
check("sharpe > 0 with positive drift", s > 0.0 and np.isfinite(s))

summary = m.summary()
for key in ("cash", "inventory", "equity", "realized_pnl",
            "max_drawdown", "sharpe", "adverse_selection", "num_fills"):
    check(f"summary has {key}", key in summary)


print("\n=== RESULT ===")
if FAILED:
    print(f"FAILED ({len(FAILED)}):")
    for f in FAILED:
        print(f"  - {f}")
    sys.exit(1)
print("All checks passed.")
