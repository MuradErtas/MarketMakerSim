import { useState } from "react";
import type { Params } from "../lib/types";
import { resetSim, updateParams } from "../hooks/useSimulation";

interface SliderSpec {
  key: keyof Params;
  label: string;
  min: number;
  max: number;
  step: number;
  help: string;
}

const SLIDERS: SliderSpec[] = [
  { key: "gamma",         label: "γ (risk aversion)",    min: 0.01, max: 2.0,  step: 0.01, help: "Higher γ shrinks inventory faster via asymmetric quotes." },
  { key: "k",             label: "k (liquidity)",        min: 0.1,  max: 5.0,  step: 0.05, help: "Higher k = fill intensity drops off faster, spread widens." },
  { key: "A",             label: "A (arrival rate)",     min: 0.1,  max: 10.0, step: 0.1,  help: "Base Poisson arrival intensity of market orders per second." },
  { key: "sigma_low",     label: "σ low-regime",         min: 0.05, max: 2.0,  step: 0.05, help: "Per-√sec vol in the low-vol regime." },
  { key: "sigma_high",    label: "σ high-regime",        min: 0.1,  max: 5.0,  step: 0.05, help: "Per-√sec vol in the high-vol regime." },
  { key: "p_low_to_high", label: "P(low → high)",        min: 0,    max: 0.05, step: 0.001,help: "Per-step probability of regime switch to high." },
  { key: "p_high_to_low", label: "P(high → low)",        min: 0,    max: 0.1,  step: 0.002,help: "Per-step probability of regime switch to low." },
  { key: "max_inventory", label: "max |inventory|",      min: 1,    max: 200,  step: 1,    help: "Hard cap; quotes on the inventory-worsening side get pulled." },
];

export function ParamControls({ params }: { params: Params }) {
  const [busy, setBusy] = useState(false);
  const [vals, setVals] = useState<Record<string, number>>(() =>
    Object.fromEntries(SLIDERS.map((s) => [s.key, params[s.key] as number]))
  );

  const onChange = async (key: string, v: number) => {
    setVals((x) => ({ ...x, [key]: v }));
    setBusy(true);
    try {
      await updateParams({ [key]: v });
    } finally {
      setBusy(false);
    }
  };

  const onReset = async () => {
    setBusy(true);
    try { await resetSim(); } finally { setBusy(false); }
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="font-semibold">Parameters</div>
        <button
          onClick={onReset}
          disabled={busy}
          className="text-xs px-2 py-1 rounded bg-panel2 hover:bg-[#22303d] disabled:opacity-50"
        >
          Reset sim
        </button>
      </div>
      <div className="space-y-3">
        {SLIDERS.map((s) => (
          <div key={s.key}>
            <div className="flex justify-between text-xs">
              <label className="text-muted">{s.label}</label>
              <span className="tabular-nums">{Number(vals[s.key]).toFixed(3)}</span>
            </div>
            <input
              type="range"
              min={s.min}
              max={s.max}
              step={s.step}
              value={vals[s.key]}
              onChange={(e) => onChange(String(s.key), Number(e.target.value))}
              className="w-full accent-accent"
            />
            <div className="text-[11px] text-muted leading-tight">{s.help}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
