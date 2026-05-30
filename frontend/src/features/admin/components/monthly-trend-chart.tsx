"use client";

import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  type TooltipProps,
} from "recharts";
import type { MonthlyTrend } from "@/types/admin";

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const map: Record<string, string> = {
    tournaments: "大会数",
    matches: "試合数",
    active_users: "MAU",
    new_teams: "新規チーム",
    participation_rate: "参加率",
  };
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/95 px-3 py-2.5 text-xs shadow-xl backdrop-blur">
      <p className="mb-1.5 font-semibold text-slate-200">{label}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-2 py-0.5">
          <span className="h-2 w-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-slate-400">{map[entry.dataKey as string] ?? entry.dataKey}:</span>
          <span className="font-semibold text-white">
            {entry.dataKey === "participation_rate"
              ? `${(entry.value as number).toFixed(1)}%`
              : (entry.value as number).toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}

const LABEL_MAP: Record<string, string> = {
  tournaments: "大会数",
  matches: "試合数",
  active_users: "MAU",
  new_teams: "新規チーム",
  participation_rate: "参加率(%)",
};

interface MonthlyTrendChartProps {
  data: MonthlyTrend[];
}

export function MonthlyTrendChart({ data }: MonthlyTrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 8, right: 48, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="mauGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />

        <XAxis
          dataKey="month"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
          tickLine={false}
        />

        {/* 左軸: 件数系 */}
        <YAxis
          yAxisId="count"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={32}
        />

        {/* 右軸: ユーザー数 */}
        <YAxis
          yAxisId="users"
          orientation="right"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={48}
          tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)}
        />

        {/* 参加率 右軸2 */}
        <YAxis
          yAxisId="rate"
          orientation="right"
          domain={[0, 100]}
          tick={false}
          axisLine={false}
          tickLine={false}
          width={0}
        />

        <Tooltip content={<CustomTooltip />} />

        <Legend
          wrapperStyle={{ fontSize: 11, color: "#64748b", paddingTop: 8 }}
          formatter={(v) => LABEL_MAP[v] ?? v}
        />

        <Bar yAxisId="count" dataKey="tournaments" fill="#3b82f6" radius={[2, 2, 0, 0]} maxBarSize={20} />
        <Bar yAxisId="count" dataKey="matches" fill="#22c55e" radius={[2, 2, 0, 0]} maxBarSize={20} />
        <Bar yAxisId="count" dataKey="new_teams" fill="#8b5cf6" radius={[2, 2, 0, 0]} maxBarSize={20} />

        <Area
          yAxisId="users"
          type="monotone"
          dataKey="active_users"
          stroke="#f59e0b"
          strokeWidth={2}
          fill="url(#mauGrad)"
          dot={false}
          activeDot={{ r: 4 }}
        />

        <Line
          yAxisId="rate"
          type="monotone"
          dataKey="participation_rate"
          stroke="#ef4444"
          strokeWidth={1.5}
          strokeDasharray="4 2"
          dot={false}
          activeDot={{ r: 3 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
