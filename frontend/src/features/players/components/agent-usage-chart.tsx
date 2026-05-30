"use client";

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  type TooltipProps,
} from "recharts";
import { cn } from "@/lib/utils";
import type { AgentUsage } from "@/types/player";

const PALETTE = [
  "#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#a78bfa",
  "#06b6d4", "#f97316", "#ec4899", "#84cc16", "#64748b",
];

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as AgentUsage & { fill: string };
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1.5 font-bold text-white">{d.agent}</p>
      <div className="space-y-0.5 text-slate-400">
        <p>試合数: <span className="text-white font-semibold">{d.games}</span></p>
        <p>勝率: <span className="text-white font-semibold">{(d.win_rate * 100).toFixed(1)}%</span></p>
        <p>KDA: <span className="text-white font-semibold">{d.avg_kda.toFixed(2)}</span></p>
      </div>
    </div>
  );
}

interface AgentUsageChartProps {
  data: AgentUsage[];
}

export function AgentUsageChart({ data }: AgentUsageChartProps) {
  const total = data.reduce((s, d) => s + d.games, 0);

  const sorted = [...data].sort((a, b) => b.games - a.games);

  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
      {/* Pie chart */}
      <div className="flex flex-col items-center">
        <div className="h-52 w-52 flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={sorted}
                dataKey="games"
                nameKey="agent"
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={90}
                paddingAngle={2}
                strokeWidth={0}
              >
                {sorted.map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-1 text-xs text-slate-500">総試合数: {total}</p>
      </div>

      {/* テーブル */}
      <div className="flex-1 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              {["エージェント", "試合", "勝率", "K/D/A", "KDA"].map((h) => (
                <th
                  key={h}
                  className="pb-2 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 pr-4 last:pr-0"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {sorted.map((agent, i) => {
              const pct = total > 0 ? (agent.games / total) * 100 : 0;
              const color = PALETTE[i % PALETTE.length];
              return (
                <tr key={agent.agent} className="hover:bg-white/3 transition-colors">
                  <td className="py-2.5 pr-4">
                    <div className="flex items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
                        style={{ background: color }}
                      />
                      <span className="font-semibold text-white">{agent.agent}</span>
                    </div>
                    <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${pct}%`, background: color, opacity: 0.7 }}
                      />
                    </div>
                  </td>
                  <td className="py-2.5 pr-4 tabular-nums text-slate-300">
                    {agent.games}
                    <span className="ml-1 text-xs text-slate-600">({pct.toFixed(0)}%)</span>
                  </td>
                  <td className="py-2.5 pr-4">
                    <span
                      className={cn(
                        "font-semibold",
                        agent.win_rate >= 0.6
                          ? "text-green-400"
                          : agent.win_rate >= 0.4
                          ? "text-white"
                          : "text-red-400",
                      )}
                    >
                      {(agent.win_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 tabular-nums text-slate-400 text-xs">
                    {agent.avg_kills.toFixed(1)}/
                    {agent.avg_deaths.toFixed(1)}/
                    {agent.avg_assists.toFixed(1)}
                  </td>
                  <td className="py-2.5 tabular-nums font-bold text-brand-400">
                    {agent.avg_kda.toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
