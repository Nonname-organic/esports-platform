"use client";

import { cn } from "@/lib/utils";
import type { HeatMapCell } from "@/types/analytics";

function interpolateColor(rate: number): string {
  // 0→red, 0.5→yellow, 1→green (dark palette)
  if (rate < 0.4) return `rgba(239,68,68,${0.15 + rate * 0.5})`; // red
  if (rate < 0.5) return `rgba(234,179,8,${0.15 + rate * 0.4})`;  // yellow
  return `rgba(34,197,94,${0.15 + (rate - 0.5) * 0.7})`;          // green
}

function textColor(rate: number): string {
  if (rate < 0.4) return "text-red-400";
  if (rate < 0.5) return "text-yellow-400";
  return "text-green-400";
}

interface HeatMapProps {
  data: HeatMapCell[];
}

export function HeatMap({ data }: HeatMapProps) {
  if (data.length === 0) return null;

  const maps = [...new Set(data.map((d) => d.map_name))].sort();
  const agents = [...new Set(data.map((d) => d.agent))].sort();

  const lookup = new Map(data.map((d) => [`${d.map_name}|${d.agent}`, d]));

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-0.5 text-xs">
        {/* ヘッダー行 (エージェント) */}
        <thead>
          <tr>
            <th className="w-24 text-left pb-1 text-slate-600 font-medium">MAP \ Agent</th>
            {agents.map((agent) => (
              <th key={agent} className="pb-1 font-medium text-slate-400 min-w-[52px]">
                <div className="writing-mode-vertical rotate-180 whitespace-nowrap text-[10px]" style={{ writingMode: "vertical-rl" }}>
                  {agent}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {maps.map((map) => (
            <tr key={map}>
              <td className="pr-2 py-0.5 text-slate-400 font-medium whitespace-nowrap text-xs">
                {map}
              </td>
              {agents.map((agent) => {
                const cell = lookup.get(`${map}|${agent}`);
                if (!cell) {
                  return (
                    <td
                      key={agent}
                      className="rounded text-center py-1.5 bg-white/3 text-slate-700 text-[10px]"
                    >
                      —
                    </td>
                  );
                }
                const wr = cell.win_rate;
                return (
                  <td
                    key={agent}
                    className={cn("rounded text-center py-1.5 transition-all cursor-default", textColor(wr))}
                    style={{ background: interpolateColor(wr) }}
                    title={`${map} × ${agent}: ${(wr * 100).toFixed(1)}% (${cell.games}試合)`}
                  >
                    <span className="font-bold text-[10px]">
                      {Math.round(wr * 100)}%
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* 凡例 */}
      <div className="mt-3 flex items-center gap-3">
        <span className="text-xs text-slate-600">勝率:</span>
        <div className="flex items-center gap-1">
          {["< 40%", "40–50%", "> 50%"].map((label, i) => (
            <div key={label} className="flex items-center gap-1">
              <span
                className="h-3 w-6 rounded-sm"
                style={{
                  background: i === 0 ? "rgba(239,68,68,0.4)" : i === 1 ? "rgba(234,179,8,0.3)" : "rgba(34,197,94,0.45)",
                }}
              />
              <span className="text-xs text-slate-500">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
