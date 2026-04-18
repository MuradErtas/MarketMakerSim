"""Tests for PnL bookkeeping and performance metrics."""
import numpy as np

from app.metrics import Metrics


def test_buy_then_sell_records_pnl_correctly():
    m = Metrics(dt=0.1)
    m.record_fill(ts=0.0, side="buy", price=100.0, size=1.0, mid=100.0)
    assert m.inventory == 1.0
    assert m.cash == -100.0
    m.record_fill(ts=1.0, side="sell", price=101.0, size=1.0, mid=101.0)
    assert m.inventory == 0.0
    # Realized PnL = +1.0
    assert m.cash == 1.0


def test_equity_marks_inventory_to_mid():
    m = Metrics(dt=0.1)
    m.record_fill(ts=0.0, side="buy", price=100.0, size=1.0, mid=100.0)
    m.tick(0.0, 100.0)
    assert m.equity == 0.0  # -100 cash + 1 * 100 mid
    m.tick(0.1, 105.0)
    assert m.equity == 5.0  # mark-to-market gain


def test_max_drawdown_captures_peak_to_trough():
    m = Metrics(dt=0.1)
    # Synthesize an equity path via buy at t=0, then mid drifts
    m.record_fill(ts=0.0, side="buy", price=100.0, size=1.0, mid=100.0)
    for i, mid in enumerate([100.0, 105.0, 110.0, 95.0, 90.0]):
        m.tick(i * 0.1, mid)
    # Peak equity 10 (at mid=110), trough -10 (at mid=90), DD = 20
    assert m.max_drawdown == 20.0


def test_sharpe_is_finite_and_nonzero_with_drift():
    m = Metrics(dt=1.0, sharpe_window=200)
    m.record_fill(ts=0.0, side="buy", price=100.0, size=1.0, mid=100.0)
    rng = np.random.default_rng(0)
    mid = 100.0
    for i in range(200):
        mid += 0.5 + rng.standard_normal() * 0.1  # strong positive drift
        m.tick(i * 1.0, mid)
    s = m.rolling_sharpe()
    assert s > 0.0
    assert np.isfinite(s)


def test_summary_fields_present():
    m = Metrics(dt=0.1)
    m.tick(0.0, 100.0)
    s = m.summary()
    for key in ("cash", "inventory", "equity", "realized_pnl",
                "max_drawdown", "sharpe", "adverse_selection", "num_fills"):
        assert key in s
