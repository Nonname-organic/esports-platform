"use client";

import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  type TooltipProps,
} from "recharts";
import type { TrendPoint } from "@/types/analytics";

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/95 px-3 py-2 text-xs shadow-xl backdrop-blur">
      <p className="mb-1.5 font-semibold text-slate-200">{label}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-2 py-0.5">
          <span className="h-2 w-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-slate-400">
            {entry.dataKey === "matches" ? "試合数" : entry.dataKey === "win_rate_pct" ? "勝率" : "KDA"}:
          </span>
          <span className="font-semibold text-white">
            {entry.dataKey === "win_rate_pct"
              ? `${(entry.value as number).toFixed(1)}%`
              : entry.dataKey === "avg_kda"
              ? (entry.value as number).toFixed(2)
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

interface TrendChartProps {
  data: TrendPoint[];
}

export function TrendChart({ data }: TrendChartProps) {
  const formatted = data.map((d) => ({
    ...d,
    win_rate_pct: parseFloat((d.win_rate * 100).toFixed(1)),
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={formatted} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="trendWrGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />

        <XAxis
          dataKey="date"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
          tickLine={false}
        />

        <YAxis
          yAxisId="matches"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={28}
        />

        <YAxis
          yAxisId="rate"
          orientation="right"
          domain={[0, 100]}
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}%`}
          width={40}
        />

        <Tooltip content={<CustomTooltip />} />

        <Legend
          wrapperStyle={{ fontSize: 11, color: "#64748b", paddingTop: 8 }}
          formatter={(v) =>
            v === "matches" ? "試合数" : v === "win_rate_pct" ? "勝率" : "KDA"
          }
        />

        {/* 試合数 Bar */}
        <Bar
          yAxisId="matches"
          dataKey="matches"
          fill="#334155"
          radius={[2, 2, 0, 0]}
          maxBarSize={32}
        />

        {/* 勝率 Area */}
        <Area
          yAxisId="rate"
          type="monotone"
          dataKey="win_rate_pct"
          stroke="#3b82f6"
          strokeWidth={2}
          fill="url(#trendWrGrad)"
          dot={false}
          activeDot={{ r: 4, fill: "#3b82f6" }}
        />

        {/* KDA Line */}
        <Line
          yAxisId="rate"
          type="monotone"
          dataKey="avg_kda"
          stroke="#a78bfa"
          strokeWidth={1.5}
          dot={false}
          activeDot={{ r: 3 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
