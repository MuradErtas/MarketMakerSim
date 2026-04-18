import React from "react";

export function StatCard({
  label, value, sub, tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  tone?: "default" | "good" | "bad" | "warn";
}) {
  const tones = {
    default: "text-ink",
    good: "text-accent",
    bad: "text-danger",
    warn: "text-warn",
  };
  return (
    <div className="card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${tones[tone]}`}>{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  );
}
