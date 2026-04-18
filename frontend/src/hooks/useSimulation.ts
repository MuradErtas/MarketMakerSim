import { useEffect, useRef, useState } from "react";
import type { Snapshot } from "../lib/types";

// Rolling history window lengths (in ticks). Keep bounded so the browser
// doesn't balloon memory over a long session.
const HISTORY_LEN = 1200;

export interface SimHistory {
  t: number[];
  mid: number[];
  bid: (number | null)[];
  ask: (number | null)[];
  reservation: number[];
  equity: number[];
  realized: number[];
  inventory: number[];
  sharpe: number[];
  regime: ("low" | "high")[];
}

const emptyHistory = (): SimHistory => ({
  t: [], mid: [], bid: [], ask: [], reservation: [],
  equity: [], realized: [], inventory: [], sharpe: [], regime: [],
});

export function useSimulation(wsUrl: string) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [connected, setConnected] = useState(false);
  const [history, setHistory] = useState<SimHistory>(emptyHistory);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    let retries = 0;

    const connect = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retries = 0;
      };
      ws.onclose = () => {
        setConnected(false);
        if (!cancelled) {
          retries += 1;
          setTimeout(connect, Math.min(5000, 500 * 2 ** retries));
        }
      };
      ws.onerror = () => { /* handled by onclose */ };
      ws.onmessage = (ev) => {
        try {
          const snap: Snapshot = JSON.parse(ev.data);
          setSnapshot(snap);
          setHistory((h) => appendHistory(h, snap));
        } catch { /* ignore bad frames */ }
      };
    };

    connect();
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [wsUrl]);

  const resetHistory = () => setHistory(emptyHistory());

  return { snapshot, connected, history, resetHistory };
}

function pushBounded<T>(arr: T[], v: T): T[] {
  const out = arr.length >= HISTORY_LEN ? arr.slice(arr.length - HISTORY_LEN + 1) : arr.slice();
  out.push(v);
  return out;
}

function appendHistory(h: SimHistory, s: Snapshot): SimHistory {
  return {
    t: pushBounded(h.t, s.t),
    mid: pushBounded(h.mid, s.mid),
    bid: pushBounded(h.bid, s.quote.bid),
    ask: pushBounded(h.ask, s.quote.ask),
    reservation: pushBounded(h.reservation, s.quote.reservation),
    equity: pushBounded(h.equity, s.metrics.equity),
    realized: pushBounded(h.realized, s.metrics.realized_pnl),
    inventory: pushBounded(h.inventory, s.metrics.inventory),
    sharpe: pushBounded(h.sharpe, s.metrics.sharpe),
    regime: pushBounded(h.regime, s.regime),
  };
}

export async function updateParams(patch: Record<string, unknown>) {
  const res = await fetch("/api/params", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error("failed to update params");
  return res.json();
}

export async function resetSim() {
  const res = await fetch("/api/reset", { method: "POST" });
  if (!res.ok) throw new Error("failed to reset");
  return res.json();
}
