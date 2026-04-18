"""FastAPI server: REST for params, WebSocket for tick stream.

Endpoints
---------
GET  /api/params            current parameters
POST /api/params            update parameters (hot reload, PnL preserved)
POST /api/reset             reset the whole sim
GET  /api/snapshot          latest snapshot (for slow clients / tests)
WS   /ws                    tick stream, ~20 Hz by default

The simulator is a single process-wide instance; one client at a time is
the intended use (this is a demo / portfolio piece).
"""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import DEFAULT_PARAMS, SimParams
from .simulator import Simulator

# When no browser is connected on /ws, do not burn CPU stepping the sim (helps
# Railway / other hosts scale down or sleep). Tune with IDLE_POLL_SECONDS.
_IDLE_POLL = max(0.25, float(os.environ.get("IDLE_POLL_SECONDS", "1.0")))


class AppState:
    sim: Simulator
    tick_hz: float = 20.0
    latest_snapshot: dict[str, Any] | None = None
    _task: asyncio.Task | None = None
    _lock: asyncio.Lock
    ws_clients: int = 0
    _ws_count_lock: asyncio.Lock

    def __init__(self) -> None:
        self.sim = Simulator(params=DEFAULT_PARAMS)
        self._lock = asyncio.Lock()
        self._ws_count_lock = asyncio.Lock()

    async def runner(self):
        """Background task: advance sim at ``tick_hz`` only while a WS client is connected."""
        period = 1.0 / self.tick_hz
        try:
            while True:
                if self.ws_clients == 0:
                    await asyncio.sleep(_IDLE_POLL)
                    continue
                async with self._lock:
                    self.latest_snapshot = self.sim.step()
                await asyncio.sleep(period)
        except asyncio.CancelledError:
            raise


state: AppState


@asynccontextmanager
async def lifespan(app: FastAPI):
    global state
    state = AppState()
    async with state._lock:
        state.latest_snapshot = state.sim.step()
    state._task = asyncio.create_task(state.runner())
    try:
        yield
    finally:
        if state._task:
            state._task.cancel()
            try:
                await state._task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="MarketMakerSim", lifespan=lifespan)

# CORS: permissive for the demo; lock down in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------- REST routes
@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.get("/api/params", response_model=SimParams)
async def get_params() -> SimParams:
    return state.sim.params


@app.post("/api/params", response_model=SimParams)
async def update_params(update: dict) -> SimParams:
    """Partial update of params, hot-swapped into the live sim."""
    # Validate by building a merged copy via pydantic
    merged = state.sim.params.model_copy(update=update)
    # Revalidate (run through constructor to enforce field validators)
    validated = SimParams(**merged.model_dump())
    async with state._lock:
        state.sim.update_params(**validated.model_dump())
    return state.sim.params


@app.post("/api/reset")
async def reset() -> dict:
    async with state._lock:
        state.sim.reset()
    return {"ok": True}


@app.get("/api/snapshot")
async def snapshot() -> dict:
    return state.latest_snapshot or {}


# ----------------------------------------------------------- WebSocket route
@app.websocket("/ws")
async def ws_stream(ws: WebSocket) -> None:
    await ws.accept()
    async with state._ws_count_lock:
        state.ws_clients += 1
    # Subscribe to broadcasts by polling latest_snapshot at tick_hz
    period = 1.0 / state.tick_hz
    try:
        while True:
            if state.latest_snapshot is not None:
                await ws.send_text(json.dumps(state.latest_snapshot,
                                              default=float))
            await asyncio.sleep(period)
    except WebSocketDisconnect:
        return
    except Exception:
        # Swallow and close; don't bring down the server for one bad client
        try:
            await ws.close()
        except Exception:
            pass
    finally:
        async with state._ws_count_lock:
            state.ws_clients -= 1
