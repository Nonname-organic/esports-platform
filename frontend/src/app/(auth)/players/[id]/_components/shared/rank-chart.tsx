"use client";

import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";

export interface RankPoint {
  label: string;   // Episode/Act または月
  value: number;   // RR または Rating
  sub?: string;    // Rank名など
}

/** ランク/レーティング推移の折れ線グラフ */
export function RankChart({ data, color = "#f43f5e", unit = "" }: { data: RankPoint[]; color?: string; unit?: string }) {
  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center rounded-xl border border-dashed border-white/10 text-sm text-slate-500">
        推移データがありません
      </div>
    );
  }
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="label" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
          <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} width={44} />
          <Tooltip
            contentStyle={{
              background: "#0f172a", border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 12, fontSize: 12,
            }}
            labelStyle={{ color: "#94a3b8" }}
            formatter={(v: number, _n, p: any) => [`${v}${unit}${p.payload.sub ? ` (${p.payload.sub})` : ""}`, "Rating"]}
          />
          <Line
            type="monotone" dataKey="value" stroke={color} strokeWidth={2}
            dot={{ r: 3, fill: color }} activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
