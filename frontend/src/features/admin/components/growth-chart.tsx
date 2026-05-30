"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ReferenceLine,
  type TooltipProps,
} from "recharts";
import { cn } from "@/lib/utils";
import type { GrowthMetric } from "@/types/admin";

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const rate = payload[0].value as number;
  const isPos = rate >= 0;
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/95 px-3 py-2 text-xs shadow-xl backdrop-blur">
      <p className="mb-1 font-semibold text-slate-200">{label}</p>
      <div className={cn("font-bold text-base", isPos ? "text-green-400" : "text-red-400")}>
        {isPos ? "+" : ""}{rate.toFixed(1)}%
      </div>
      <p className="text-slate-500 mt-0.5">前月比</p>
    </div>
  );
}

interface GrowthChartProps {
  data: GrowthMetric[];
}

export function GrowthChart({ data }: GrowthChartProps) {
  const chartData = data.map((d) => ({
    label: d.label,
    rate: parseFloat(d.growth_rate.toFixed(1)),
    current: d.current,
    unit: d.unit,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />

        <XAxis
          dataKey="label"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
          tickLine={false}
        />

        <YAxis
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}%`}
          width={40}
        />

        <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" />

        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />

        <Bar dataKey="rate" radius={[3, 3, 0, 0]} maxBarSize={48}>
          {chartData.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.rate >= 0 ? "#22c55e" : "#ef4444"}
              fillOpacity={Math.min(0.4 + Math.abs(entry.rate) / 100, 1)}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
