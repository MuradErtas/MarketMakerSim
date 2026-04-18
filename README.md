# Market Maker Simulator

A live, interactive simulation of an **Avellaneda–Stoikov optimal market maker** trading against Poisson-driven noise flow in a regime-switching volatility environment. Built as a learning project and a portfolio piece for quant trading roles.

**What's inside**

- Price-time priority limit order book and matching engine (Python)
- Avellaneda–Stoikov quoting agent with inventory penalty and hard inventory caps
- Regime-switching (2-state Markov) stochastic volatility driving the mid
- Poisson noise-trader market orders with distance-from-mid fill intensity `λ = A·exp(−k·δ)`
- Real-time dashboard: live LOB depth, mid + quotes, PnL (MtM + realized), inventory, rolling Sharpe, max drawdown, adverse selection, fill heatmap
- Hot-swap controls for γ (risk aversion), k (liquidity), regime transition probabilities, and more

## The math

The agent solves the finite-horizon optimal market-making problem from Avellaneda & Stoikov (2008). With mid-price `s`, signed inventory `q`, volatility `σ`, risk aversion `γ`, time-to-horizon `T − t`, and a noise-flow intensity parameter `k`:

**Reservation price** — where the agent is indifferent between buying and selling given its current inventory:

```
r(s, q, t) = s − q · γ · σ² · (T − t)
```

**Optimal total bid-ask spread** around `r`:

```
δ_bid + δ_ask = γ · σ² · (T − t) + (2 / γ) · ln(1 + γ / k)
```

**Intuition**

- `γ ↑`: agent dislikes inventory more → reservation pulls harder toward zero inventory → asymmetric quotes that unload positions faster.
- `k ↑`: fill intensity drops off faster with distance from mid → optimal to quote tighter (smaller edge, more volume).
- `σ ↑` or `T − t ↑`: greater inventory risk → wider spread.
- Approaching the horizon (`t → T`): inventory-risk component vanishes → spread narrows.

**Noise flow**

Market orders on each side arrive as a Poisson process with intensity
`λ(δ) = A · exp(−k · δ)` where `δ` is the agent's distance from mid. Per step we discretise as Bernoulli(λ·dt).

**Regime-switching volatility**

A 2-state Markov chain between *low* and *high* regimes governs `σ`. Transition probabilities `p_low→high` and `p_high→low` are configurable; by default regimes are persistent (days of low-vol punctuated by short high-vol bursts).

**Adverse selection tracker**

For each MM fill, we measure the mid move over a fixed lookahead horizon, signed against the MM (up-move hurts after a sell, down-move hurts after a buy). The running average is reported on the dashboard — high values mean toxic flow is picking the MM off.

## Architecture

```
┌──────────────────────────┐        WebSocket (JSON snapshots @ 20 Hz)
│  Python backend (FastAPI)│ ──────────────────────────────────► ┌────────────────┐
│  - Limit order book      │        REST: /api/params, /reset    │ React + TS     │
│  - A-S agent             │ ◄────────────────────────────────── │ + Tailwind +   │
│  - Regime vol / Poisson  │                                     │ Recharts       │
│  - Metrics (Sharpe, DD)  │                                     └────────────────┘
└──────────────────────────┘
```

The simulator runs as a single background asyncio task inside the FastAPI process, stepping the sim at ~20 ticks/sec. Clients connect via WebSocket and receive full state snapshots each tick.

Directory layout:

```
backend/
  app/
    config.py       # SimParams (pydantic)
    orderbook.py    # LOB + matching engine
    flow.py         # Regime vol + Poisson noise flow
    agent.py        # A-S optimal quoting
    metrics.py      # PnL, inventory, Sharpe, drawdown, adverse selection
    simulator.py    # Main tick loop
    main.py         # FastAPI app + WS
  tests/
    test_*.py       # Pytest suite
    verify_core.py  # Standalone (stdlib + numpy only) smoke tests
    verify_simulator.py
frontend/
  src/
    App.tsx
    hooks/useSimulation.ts   # WebSocket client + rolling history
    components/
      PriceChart.tsx         # Mid, bid, ask, reservation
      DepthChart.tsx         # Cumulative LOB depth
      PnLChart.tsx           # MtM equity + realized cash
      InventoryChart.tsx
      FillHeatmap.tsx        # Price-offset × side heatmap
      SpreadAnalytics.tsx    # Optimal vs realized spread, adverse selection
      ParamControls.tsx      # Live sliders for γ, k, A, σ, regime probs
      StatCard.tsx
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Tests:

```bash
pytest                                 # full suite
python tests/verify_core.py            # stdlib + numpy only (no pytest/pydantic)
python tests/verify_simulator.py       # end-to-end smoke test without pydantic
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # Vite dev server on http://localhost:5173 (proxies /api and /ws to :8000)
```

### Or with Docker Compose

```bash
docker-compose up --build
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
```

## Parameters

| Param | Default | Meaning |
|---|---:|---|
| `dt` | 0.1 | Simulation step (seconds) |
| `T` | 60 | A-S horizon (seconds, episode length) |
| `s0` | 100 | Initial mid price |
| `gamma` | 0.1 | Inventory risk aversion |
| `k` | 1.5 | Fill-intensity decay |
| `A` | 1.4 | Base arrival rate per side (orders/sec) |
| `sigma_low` / `sigma_high` | 0.3 / 1.2 | Regime volatilities (per √sec) |
| `p_low_to_high` / `p_high_to_low` | 0.002 / 0.01 | Regime transition probabilities |
| `quote_size` | 1 | MM order size posted at each quote |
| `max_inventory` | 50 | Hard inventory cap |

## What this shows

- Working knowledge of the canonical optimal MM model (Avellaneda–Stoikov) and the trade-offs it captures
- Ability to build a correct price-time priority limit order book + matching engine from scratch
- Discrete-time simulation of a Poisson process and a regime-switching Markov chain
- Clean backend/frontend separation with a real-time WebSocket data channel
- Standard quant performance metrics (rolling Sharpe, max drawdown, adverse selection)
- Production-lite tooling: pytest, Docker, typed TS frontend, deployable config

## References

- Avellaneda, M. & Stoikov, S. (2008). *High-frequency trading in a limit order book.* Quantitative Finance 8:3.
- Guéant, O., Lehalle, C.-A. & Fernandez-Tapia, J. (2013). *Dealing with the inventory risk.* Mathematics and Financial Economics.
- Cartea, Á., Jaimungal, S. & Penalva, J. (2015). *Algorithmic and High-Frequency Trading.* Cambridge.

## License

MIT.
