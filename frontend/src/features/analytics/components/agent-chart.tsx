"use client";

import { useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  type TooltipProps,
} from "recharts";
import { cn } from "@/lib/utils";
import type { AgentStat } from "@/types/analytics";

type Metric = "win_rate" | "pick_rate" | "ban_rate" | "avg_kda";

const METRIC_CONFIG: Record<Metric, { label: string; color: string; fmt: (v: number) => string }> = {
  win_rate: { label: "勝率", color: "#3b82f6", fmt: (v) => `${(v * 100).toFixed(1)}%` },
  pick_rate: { label: "ピック率", color: "#22c55e", fmt: (v) => `${(v * 100).toFixed(1)}%` },
  ban_rate: { label: "バン率", color: "#ef4444", fmt: (v) => `${(v * 100).toFixed(1)}%` },
  avg_kda: { label: "KDA", color: "#a78bfa", fmt: (v) => v.toFixed(2) },
};

function CustomTooltip({
  active,
  payload,
  label,
  metric,
}: TooltipProps<number, string> & { metric: Metric }) {
  if (!active || !payload?.length) return null;
  const cfg = METRIC_CONFIG[metric];
  const d = payload[0].payload as AgentStat;
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/95 px-3 py-2 text-xs shadow-xl backdrop-blur">
      <p className="mb-1.5 font-bold text-white">{label}</p>
      <div className="space-y-0.5 text-slate-400">
        <p>{cfg.label}: <span className="text-white font-semibold">{cfg.fmt(payload[0].value as number)}</span></p>
        <p>試合数: <span className="text-white">{d.games}</span></p>
        <p>勝/敗: <span className="text-green-400">{d.wins}</span>/<span className="text-red-400">{d.losses}</span></p>
      </div>
    </div>
  );
}

interface AgentChartProps {
  data: AgentStat[];
}

export function AgentChart({ data }: AgentChartProps) {
  const [metric, setMetric] = useState<Metric>("win_rate");
  const cfg = METRIC_CONFIG[metric];

  const sorted = [...data]
    .sort((a, b) => (b[metric] as number) - (a[metric] as number))
    .slice(0, 12);

  return (
    <div>
      {/* メトリクス切替 */}
      <div className="mb-4 flex flex-wrap gap-1">
        {(Object.entries(METRIC_CONFIG) as [Metric, typeof METRIC_CONFIG[Metric]][]).map(
          ([key, { label, color }]) => (
            <button
              key={key}
              onClick={() => setMetric(key)}
              className={cn(
                "rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors",
                metric === key
                  ? "border-transparent text-white"
                  : "border-white/10 text-slate-500 hover:text-white",
              )}
              style={metric === key ? { background: color + "25", borderColor: color + "50", color } : {}}
            >
              {label}
            </button>
          ),
        )}
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={sorted}
          layout="vertical"
          margin={{ top: 0, right: 48, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: "#64748b", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={cfg.fmt}
          />
          <YAxis
            type="category"
            dataKey="agent"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={72}
          />
          <Tooltip
            content={(props) => (
              <CustomTooltip
                active={props.active}
                payload={props.payload as TooltipProps<number, string>["payload"]}
                label={props.label}
                metric={metric}
              />
            )}
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
          />
          <Bar dataKey={metric} radius={[0, 3, 3, 0]} maxBarSize={18}>
            {sorted.map((entry, i) => {
              const val = entry[metric] as number;
              const opacity = 0.5 + (i / sorted.length) * 0.5;
              return (
                <Cell key={entry.agent} fill={cfg.color} fillOpacity={1 - i * 0.05} />
              );
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
