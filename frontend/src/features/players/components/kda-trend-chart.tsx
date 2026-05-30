"use client";

import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  type TooltipProps,
} from "recharts";
import type { PlayerKdaPoint } from "@/types/player";

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;

  const data = Object.fromEntries(
    payload.map((p) => [p.dataKey as string, p.value as number]),
  );

  return (
    <div className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1.5 font-semibold text-slate-300">{label}</p>
      <div className="space-y-1">
        {payload.map((entry) => (
          <div key={entry.dataKey} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ background: entry.color }} />
            <span className="text-slate-400">
              {entry.dataKey === "avg_kills"
                ? "K"
                : entry.dataKey === "avg_deaths"
                ? "D"
                : entry.dataKey === "avg_assists"
                ? "A"
                : "KDA"}:
            </span>
            <span className="font-semibold text-white">
              {(entry.value as number).toFixed(
                entry.dataKey === "avg_kda" ? 2 : 1,
              )}
            </span>
          </div>
        ))}
        {data.matches != null && (
          <p className="mt-1 border-t border-white/10 pt-1 text-slate-500">
            {data.matches} 試合
          </p>
        )}
      </div>
    </div>
  );
}

interface KdaTrendChartProps {
  data: PlayerKdaPoint[];
}

export function KdaTrendChart({ data }: KdaTrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="killsGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
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
          yAxisId="stats"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={28}
        />

        <YAxis
          yAxisId="kda"
          orientation="right"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => v.toFixed(1)}
          width={36}
        />

        <Tooltip content={<CustomTooltip />} />

        <Legend
          wrapperStyle={{ fontSize: 11, color: "#64748b", paddingTop: 8 }}
          formatter={(value) =>
            value === "avg_kills"
              ? "Kill"
              : value === "avg_deaths"
              ? "Death"
              : value === "avg_assists"
              ? "Assist"
              : "KDA"
          }
        />

        {/* Kills */}
        <Line
          yAxisId="stats"
          type="monotone"
          dataKey="avg_kills"
          stroke="#22c55e"
          strokeWidth={2}
          dot={{ r: 3, fill: "#22c55e", strokeWidth: 0 }}
          activeDot={{ r: 5 }}
        />

        {/* Deaths */}
        <Line
          yAxisId="stats"
          type="monotone"
          dataKey="avg_deaths"
          stroke="#ef4444"
          strokeWidth={2}
          dot={{ r: 3, fill: "#ef4444", strokeWidth: 0 }}
          activeDot={{ r: 5 }}
        />

        {/* Assists */}
        <Line
          yAxisId="stats"
          type="monotone"
          dataKey="avg_assists"
          stroke="#f59e0b"
          strokeWidth={1.5}
          strokeDasharray="4 2"
          dot={false}
        />

        {/* KDA (右軸) */}
        <Line
          yAxisId="kda"
          type="monotone"
          dataKey="avg_kda"
          stroke="#a78bfa"
          strokeWidth={2.5}
          dot={{ r: 4, fill: "#a78bfa", strokeWidth: 0 }}
          activeDot={{ r: 6 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
