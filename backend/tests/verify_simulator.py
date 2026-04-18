"""Verify the simulator end-to-end without needing pydantic installed.

Builds a SimParams shim with a namedtuple-style object and runs the
simulator for 500 ticks to check invariants.  The real production code
uses pydantic for validation; this script only exists to let us smoke
test in environments where pydantic is absent.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, asdict

sys.path.insert(0, ".")


@dataclass
class SimParamsShim:
    dt: float = 0.1
    T: float = 10.0
    s0: float = 100.0
    tick_size: float = 0.01
    gamma: float = 0.1
    k: float = 1.5
    A: float = 1.4
    sigma_low: float = 0.3
    sigma_high: float = 1.2
    p_low_to_high: float = 0.01
    p_high_to_low: float = 0.02
    quote_size: float = 1.0
    max_inventory: float = 50.0
    seed: int = 42

    def model_copy(self, update: dict):
        d = asdict(self); d.update(update)
        return SimParamsShim(**d)

    def model_dump(self):
        return asdict(self)


# Monkeypatch app.config.SimParams so the simulator module imports without
# needing pydantic.
import types
fake_config = types.ModuleType("app.config")
fake_config.SimParams = SimParamsShim
fake_config.DEFAULT_PARAMS = SimParamsShim()
sys.modules["app.config"] = fake_config

from app.simulator import Simulator  # noqa: E402

FAILED = []

def check(name, cond):
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAILED.append(name)
    print(f"  [{status}] {name}")


print("=== Simulator end-to-end ===")
sim = Simulator(params=SimParamsShim(seed=42, dt=0.1, T=10.0))
snap = None
for _ in range(500):
    snap = sim.step()

check("step counter advances", snap["step"] == 500)
check("snapshot has book", "book" in snap and "bids" in snap["book"])
check("snapshot has metrics", "metrics" in snap)
check("num_fills >= 0", snap["metrics"]["num_fills"] >= 0)
check("regime is valid", snap["regime"] in ("low", "high"))
check("mid is positive", snap["mid"] > 0)
check("quote includes bid and ask", "bid" in snap["quote"] and "ask" in snap["quote"])

print(f"\nAfter 500 ticks: {snap['metrics']['num_fills']} fills, "
      f"equity={snap['metrics']['equity']:.3f}, "
      f"inventory={snap['metrics']['inventory']:.2f}, "
      f"sharpe={snap['metrics']['sharpe']:.3f}, "
      f"DD={snap['metrics']['max_drawdown']:.3f}")

# Reset test
sim.reset()
check("reset clears step", sim.step_idx == 0)
check("reset clears cash", sim.metrics.cash == 0.0)
check("reset clears inventory", sim.metrics.inventory == 0.0)

# Param hot-swap
sim.update_params(gamma=0.5)
check("hot-swap params.gamma", sim.params.gamma == 0.5)
check("hot-swap agent.gamma", sim.agent.gamma == 0.5)

# Longer run with different seed to get fills
sim2 = Simulator(params=SimParamsShim(seed=7, dt=0.1, T=60.0, A=5.0, k=0.5))
for _ in range(2000):
    sim2.step()
final = sim2.metrics.summary()
print(f"\nLong run (high flow): {final['num_fills']} fills, "
      f"equity={final['equity']:.3f}, sharpe={final['sharpe']:.3f}")
check("high-flow run produces fills", final['num_fills'] > 5)
check("sharpe is finite", -1e9 < final['sharpe'] < 1e9)

print("\n=== RESULT ===")
if FAILED:
    print(f"FAILED ({len(FAILED)}):")
    for f in FAILED:
        print(f"  - {f}")
    sys.exit(1)
print("All simulator checks passed.")
