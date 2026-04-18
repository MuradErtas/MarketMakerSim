import { useMemo, useRef } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import type { Book } from "../lib/types";

/**
 * Depth chart: cumulative bid (left) and ask (right) liquidity.
 *
 * Uses the **book inside mid** \((bestBid + bestAsk)/2\) for the vertical
 * split and x-window center, not the process mid from the simulator. The
 * process mid can drift through the spread while quotes stay put, which made
 * the old `price <= processMid` mask flip every tick and look broken.
 *
 * Y-axis max uses a sticky peak with slow decay so the scale does not twitch
 * at 20 Hz when depth is noisy.
 */
export function DepthChart({
  book,
  mid,
  tickSize = 0.01,
  halfRange = 2.0,
  binSize = 0.05,
}: {
  book: Book;
  mid: number;
  tickSize?: number;
  halfRange?: number;
  binSize?: number;
}) {
  const depthPeak = useRef(1);

  const { data, xDomain, insideMid } = useMemo(() => {
    const bestBid = book.bids[0]?.price;
    const bestAsk = book.asks[0]?.price;
    const inside =
      bestBid != null && bestAsk != null ? 0.5 * (bestBid + bestAsk) : mid;

    const centerSnapped = Math.round(inside / binSize) * binSize;
    const xMin = centerSnapped - halfRange;
    const xMax = centerSnapped + halfRange;
    const nBins = Math.round((xMax - xMin) / binSize) + 1;

    const bins: { price: number; bid: number | null; ask: number | null }[] =
      Array.from({ length: nBins }, (_, i) => ({
        price: Number((xMin + i * binSize).toFixed(4)),
        bid: null,
        ask: null,
      }));

    const bidsSorted = [...book.bids].sort((a, b) => b.price - a.price);
    let cum = 0;
    for (const lvl of bidsSorted) {
      cum += lvl.size;
      const idx = Math.round((lvl.price - xMin) / binSize);
      if (idx >= 0 && idx < nBins) {
        bins[idx].bid = Math.max(bins[idx].bid ?? 0, cum);
      }
    }
    let running = 0;
    for (let i = nBins - 1; i >= 0; i--) {
      running = Math.max(running, bins[i].bid ?? 0);
      // Strict < inside so the bin exactly at the microprice does not double-count.
      bins[i].bid = running > 0 && bins[i].price < inside ? running : null;
    }

    const asksSorted = [...book.asks].sort((a, b) => a.price - b.price);
    cum = 0;
    for (const lvl of asksSorted) {
      cum += lvl.size;
      const idx = Math.round((lvl.price - xMin) / binSize);
      if (idx >= 0 && idx < nBins) {
        bins[idx].ask = Math.max(bins[idx].ask ?? 0, cum);
      }
    }
    running = 0;
    for (let i = 0; i < nBins; i++) {
      running = Math.max(running, bins[i].ask ?? 0);
      bins[i].ask = running > 0 && bins[i].price > inside ? running : null;
    }

    return {
      data: bins,
      xDomain: [xMin, xMax] as [number, number],
      insideMid: inside,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [book, mid, halfRange, binSize]);

  let rawMax = 0;
  for (const b of data) {
    if (b.bid != null && b.bid > rawMax) rawMax = b.bid;
    if (b.ask != null && b.ask > rawMax) rawMax = b.ask;
  }
  const target =
    rawMax <= 0
      ? 1
      : (() => {
          const step = rawMax < 5 ? 0.5 : 1;
          return Math.ceil(rawMax / step) * step;
        })();
  const prev = depthPeak.current;
  if (target > prev) depthPeak.current = target;
  else if (target < prev * 0.6) depthPeak.current = Math.max(target, 0.5);
  const maxDepth = depthPeak.current;

  void tickSize;

  return (
    <div className="card h-72">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold">Order book depth</div>
        <div className="text-xs text-muted">inside {insideMid.toFixed(2)}</div>
      </div>
      <ResponsiveContainer width="100%" height="88%">
        <AreaChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#1a2330" />
          <XAxis
            dataKey="price"
            type="number"
            domain={xDomain}
            tickFormatter={(v) => Number(v).toFixed(2)}
            tick={{ fontSize: 10, fill: "#8b96a5" }}
            allowDataOverflow
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#8b96a5" }}
            width={40}
            domain={[0, maxDepth]}
            allowDecimals
            tickCount={5}
          />
          <Tooltip
            cursor={{ stroke: "rgba(255,255,255,0.12)", strokeWidth: 1 }}
            contentStyle={{
              background: "#121821",
              border: "1px solid #1a2330",
              fontSize: 12,
              color: "#e6edf3",
              borderRadius: 4,
            }}
            labelStyle={{ color: "#8b96a5" }}
            formatter={(value, name) => {
              const label = String(name);
              if (value == null || value === "") return ["—", label];
              const n = typeof value === "number" ? value : Number(value);
              if (Number.isNaN(n)) return ["—", label];
              return [n.toFixed(2), label];
            }}
            labelFormatter={(v) => `price ${Number(v).toFixed(2)}`}
          />
          <ReferenceLine
            x={insideMid}
            stroke="#e6edf3"
            strokeOpacity={0.35}
            strokeDasharray="2 3"
          />
          <Area
            type="stepAfter"
            dataKey="bid"
            stroke="#6ee7b7"
            fill="#6ee7b7"
            fillOpacity={0.35}
            strokeWidth={1}
            connectNulls={false}
            isAnimationActive={false}
            baseLine={0}
          />
          <Area
            type="stepAfter"
            dataKey="ask"
            stroke="#fb7185"
            fill="#fb7185"
            fillOpacity={0.35}
            strokeWidth={1}
            connectNulls={false}
            isAnimationActive={false}
            baseLine={0}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
