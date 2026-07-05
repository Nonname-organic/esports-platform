"use client";

import { Map as MapIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { usePlayerCareer } from "@/features/career/hooks/use-career";

/** Map Performance: マップ別勝率。 */
export function MapPerformanceCard({ playerId }: { playerId: string }) {
  const { data: c } = usePlayerCareer(playerId);
  const maps = c?.map_performance ?? [];
  if (maps.length === 0) return null;

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-4 flex items-center gap-2 font-bold text-white">
        <MapIcon className="h-4 w-4 text-cyan-400" /> Map Performance
      </h2>
      <ul className="space-y-2.5">
        {maps.slice(0, 6).map((m) => {
          const wr = Math.round(m.win_rate * 100);
          return (
            <li key={m.map_name} className="flex items-center gap-3">
              <span className="w-20 flex-shrink-0 truncate text-sm font-semibold text-white">{m.map_name}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/10">
                <div className={cn("h-full rounded-full", m.win_rate >= 0.5 ? "bg-gradient-to-r from-brand-500 to-green-400" : "bg-gradient-to-r from-slate-600 to-red-500")}
                  style={{ width: `${wr}%` }} />
              </div>
              <span className="w-16 flex-shrink-0 text-right text-xs tabular-nums text-slate-400">
                <span className={cn("font-bold", m.win_rate >= 0.5 ? "text-green-400" : "text-slate-300")}>{wr}%</span> · {m.games}戦
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
