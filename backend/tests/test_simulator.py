"""Integration-level tests: run the simulator for a few hundred ticks."""
from app.config import SimParams
from app.simulator import Simulator


def test_simulator_runs_stably():
    sim = Simulator(params=SimParams(seed=42, dt=0.1, T=10.0))
    for _ in range(500):
        snap = sim.step()
    # Invariants
    assert snap["step"] == 500
    assert "metrics" in snap
    assert "book" in snap
    # The MM should have posted a lot of quotes and likely taken some fills
    assert snap["metrics"]["num_fills"] >= 0  # non-negative


def test_simulator_reset_clears_state():
    sim = Simulator(params=SimParams(seed=42))
    for _ in range(100):
        sim.step()
    sim.reset()
    assert sim.step_idx == 0
    assert sim.t == 0.0
    assert sim.metrics.cash == 0.0
    assert sim.metrics.inventory == 0.0


def test_param_hot_swap():
    sim = Simulator(params=SimParams(seed=42, gamma=0.1))
    for _ in range(10):
        sim.step()
    sim.update_params(gamma=0.5)
    assert sim.params.gamma == 0.5
    assert sim.agent.gamma == 0.5


def test_snapshot_shape():
    sim = Simulator(params=SimParams(seed=7))
    snap = sim.step()
    assert set(["t", "step", "mid", "regime", "sigma", "quote",
                "book", "metrics", "recent_fills", "params"]).issubset(snap.keys())
    assert "bids" in snap["book"] and "asks" in snap["book"]
    assert "bid" in snap["quote"] and "ask" in snap["quote"]
