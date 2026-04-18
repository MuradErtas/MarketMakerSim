"""Verify the JSON schema emitted by Simulator.snapshot() matches the
TypeScript Snapshot interface in frontend/src/lib/types.ts.

Does NOT require pydantic/fastapi — shims SimParams like verify_simulator.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict

sys.path.insert(0, ".")


@dataclass
class SimParamsShim:
    dt: float = 0.1; T: float = 10.0; s0: float = 100.0; tick_size: float = 0.01
    gamma: float = 0.1; k: float = 1.5; A: float = 2.0
    sigma_low: float = 0.3; sigma_high: float = 1.2
    p_low_to_high: float = 0.01; p_high_to_low: float = 0.02
    quote_size: float = 1.0; max_inventory: float = 50.0; seed: int = 7
    def model_copy(self, update): d = asdict(self); d.update(update); return SimParamsShim(**d)
    def model_dump(self): return asdict(self)

import types
fake = types.ModuleType("app.config")
fake.SimParams = SimParamsShim
fake.DEFAULT_PARAMS = SimParamsShim()
sys.modules["app.config"] = fake

from app.simulator import Simulator  # noqa: E402

FAILED = []

def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond: FAILED.append(name)

# Run for a bit so we get some fills and populated history
sim = Simulator(params=SimParamsShim(A=5.0, k=0.5))
for _ in range(200):
    snap = sim.step()

# Round-trip through JSON to confirm it's wire-serializable
wire = json.loads(json.dumps(snap, default=float))

print("=== Snapshot schema ===")
required = {"t", "step", "mid", "regime", "sigma", "quote",
            "book", "metrics", "recent_fills", "params"}
check("top-level keys", required.issubset(wire.keys()))

quote_keys = {"bid", "ask", "reservation", "spread"}
check("quote keys", quote_keys.issubset(wire["quote"].keys()))

check("book.bids is list", isinstance(wire["book"]["bids"], list))
check("book.asks is list", isinstance(wire["book"]["asks"], list))
if wire["book"]["bids"]:
    check("book level has price+size",
          set(["price", "size"]).issubset(wire["book"]["bids"][0].keys()))

metrics_keys = {"cash", "inventory", "equity", "realized_pnl",
                "max_drawdown", "sharpe", "adverse_selection", "num_fills"}
check("metrics keys", metrics_keys.issubset(wire["metrics"].keys()))

check("regime is low or high", wire["regime"] in ("low", "high"))

if wire["recent_fills"]:
    fkeys = {"t", "side", "price", "size", "mid"}
    check("fill shape", fkeys.issubset(wire["recent_fills"][0].keys()))
    check("fill side is buy|sell",
          wire["recent_fills"][0]["side"] in ("buy", "sell"))

param_keys = {"dt", "T", "s0", "tick_size", "gamma", "k", "A",
              "sigma_low", "sigma_high", "p_low_to_high", "p_high_to_low",
              "quote_size", "max_inventory"}
check("params keys (subset)", param_keys.issubset(wire["params"].keys()))

print(f"\nExample snapshot (trimmed):")
trimmed = {**wire, "book": {
    "bids": wire["book"]["bids"][:2], "asks": wire["book"]["asks"][:2]
}}
trimmed["recent_fills"] = wire["recent_fills"][:2]
print(json.dumps(trimmed, indent=2, default=float)[:1500])

print("\n=== RESULT ===")
if FAILED:
    print(f"FAILED ({len(FAILED)})")
    for f in FAILED: print("  -", f)
    sys.exit(1)
print("Snapshot schema OK.")
