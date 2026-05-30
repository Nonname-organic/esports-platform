"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  type TooltipProps,
} from "recharts";
import type { WinRatePoint } from "@/types/team";

interface WinRateChartProps {
  data: WinRatePoint[];
}

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1.5 font-semibold text-slate-300">{label}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-slate-400">{entry.name}:</span>
          <span className="font-semibold text-white">
            {entry.dataKey === "win_rate"
              ? `${((entry.value as number) * 100).toFixed(1)}%`
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export function WinRateChart({ data }: WinRateChartProps) {
  const formatted = data.map((d) => ({
    ...d,
    win_rate_pct: Math.round(d.win_rate * 100),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={formatted} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="winRateGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="ratingGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />

        <XAxis
          dataKey="month"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
          tickLine={false}
        />

        <YAxis
          yAxisId="rate"
          domain={[0, 100]}
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}%`}
          width={36}
        />

        <YAxis
          yAxisId="rating"
          orientation="right"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={48}
        />

        <Tooltip content={<CustomTooltip />} />

        <Legend
          wrapperStyle={{ fontSize: 11, color: "#64748b", paddingTop: 8 }}
          formatter={(value) =>
            value === "win_rate_pct" ? "勝率 (%)" : "レーティング"
          }
        />

        <Area
          yAxisId="rate"
          type="monotone"
          dataKey="win_rate_pct"
          name="win_rate_pct"
          stroke="#3b82f6"
          strokeWidth={2}
          fill="url(#winRateGrad)"
          dot={{ r: 3, fill: "#3b82f6", strokeWidth: 0 }}
          activeDot={{ r: 5, fill: "#3b82f6" }}
        />

        <Area
          yAxisId="rating"
          type="monotone"
          dataKey="rating"
          name="rating"
          stroke="#a78bfa"
          strokeWidth={1.5}
          strokeDasharray="4 2"
          fill="url(#ratingGrad)"
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
