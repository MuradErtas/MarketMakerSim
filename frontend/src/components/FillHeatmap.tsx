import { useMemo } from "react";
import type { Fill } from "../lib/types";

/**
 * 2-D bin of fills by (relative-price offset from mid at fill time, side).
 * Not a true heatmap image — a simple grid with counts + fill-color by volume.
 * This is a fast way to show "where on the book did we actually trade?".
 */
export function FillHeatmap({ fills }: { fills: Fill[] }) {
  const { rows, maxCount } = useMemo(() => {
    const binSize = 0.02;          // price units per bin
    const halfBins = 12;
    const buys = new Array(halfBins * 2 + 1).fill(0);
    const sells = new Array(halfBins * 2 + 1).fill(0);
    for (const f of fills) {
      const d = f.price - f.mid;   // signed offset
      const idx = Math.max(0, Math.min(halfBins * 2, halfBins + Math.round(d / binSize)));
      if (f.side === "buy") buys[idx] += f.size;
      else sells[idx] += f.size;
    }
    const maxC = Math.max(1, ...buys, ...sells);
    const rows = [
      { label: "SELL", data: sells, color: "251, 113, 133" },
      { label: "BUY",  data: buys,  color: "110, 231, 183" },
    ];
    return { rows, maxCount: maxC };
  }, [fills]);

  return (
    <div className="card">
      <div className="font-semibold mb-2">Fill heatmap</div>
      <div className="text-xs text-muted mb-2">
        Offset from mid at fill time (price units). MM wants buys to concentrate below mid, sells above.
      </div>
      <div className="space-y-1">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center gap-1">
            <div className="w-10 text-xs text-muted">{r.label}</div>
            <div className="flex gap-[2px]">
              {r.data.map((v, i) => {
                const alpha = v / maxCount;
                return (
                  <div
                    key={i}
                    className="w-4 h-5 rounded-sm"
                    title={`count=${v.toFixed(2)}`}
                    style={{ background: `rgba(${r.color}, ${alpha.toFixed(3)})` }}
                  />
                );
              })}
            </div>
          </div>
        ))}
        <div className="flex gap-[2px] pl-11 mt-1">
          {Array.from({ length: 25 }, (_, i) => (
            <div key={i} className="w-4 text-[10px] text-muted text-center">
              {i === 0 ? "-" : i === 24 ? "+" : i === 12 ? "0" : ""}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
