"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
  type TooltipProps,
} from "recharts";
import type { MonthlyStatsPoint } from "@/types/team";

interface MonthlyStatsChartProps {
  data: MonthlyStatsPoint[];
}

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;

  const wins = payload.find((p) => p.dataKey === "wins")?.value as number | undefined;
  const losses = payload.find((p) => p.dataKey === "losses")?.value as number | undefined;
  const total = (wins ?? 0) + (losses ?? 0);
  const wr = total > 0 ? (((wins ?? 0) / total) * 100).toFixed(0) : "-";

  return (
    <div className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1.5 font-semibold text-slate-300">{label}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-slate-400">{entry.name}:</span>
          <span className="font-semibold text-white">{entry.value}</span>
        </div>
      ))}
      {total > 0 && (
        <div className="mt-1.5 border-t border-white/10 pt-1.5 text-slate-500">
          勝率: <span className="font-semibold text-white">{wr}%</span>
        </div>
      )}
    </div>
  );
}

export function MonthlyStatsChart({ data }: MonthlyStatsChartProps) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart
        data={data}
        margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
        barCategoryGap="30%"
        barGap={2}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />

        <XAxis
          dataKey="month"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
          tickLine={false}
        />

        <YAxis
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
          width={28}
        />

        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />

        <Legend
          wrapperStyle={{ fontSize: 11, color: "#64748b", paddingTop: 8 }}
          formatter={(value) => (value === "wins" ? "勝利" : "敗北")}
        />

        <Bar dataKey="wins" name="wins" fill="#22c55e" radius={[3, 3, 0, 0]} maxBarSize={32}>
          {data.map((_, i) => (
            <Cell key={i} fill="#22c55e" fillOpacity={0.8} />
          ))}
        </Bar>

        <Bar dataKey="losses" name="losses" fill="#ef4444" radius={[3, 3, 0, 0]} maxBarSize={32}>
          {data.map((_, i) => (
            <Cell key={i} fill="#ef4444" fillOpacity={0.7} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
