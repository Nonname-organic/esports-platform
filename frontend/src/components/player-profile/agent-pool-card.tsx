"use client";

import { Swords, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { usePlayerCareer } from "@/features/career/hooks/use-career";

/** Agent Pool: 使用エージェントの起用率/勝率/KDA。最多起用に Favorite Glow。 */
export function AgentPoolCard({ playerId }: { playerId: string }) {
  const { data: c } = usePlayerCareer(playerId);
  const agents = c?.agent_usage ?? [];
  if (agents.length === 0) return null;

  const totalGames = agents.reduce((s, a) => s + a.games, 0) || 1;
  const favorite = agents[0]?.agent;

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-4 flex items-center gap-2 font-bold text-white">
        <Swords className="h-4 w-4 text-red-400" /> Agent Pool
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {agents.slice(0, 6).map((a) => {
          const isFav = a.agent === favorite;
          const playRate = Math.round((a.games / totalGames) * 100);
          return (
            <div
              key={a.agent}
              className={cn(
                "rounded-xl border bg-white/[0.02] p-3",
                isFav ? "border-yellow-500/40 shadow-[0_0_20px_-8px_rgba(234,179,8,0.6)]" : "border-white/8",
              )}
            >
              <div className="mb-1 flex items-center gap-1.5">
                <span className="truncate font-bold capitalize text-white">{a.agent}</span>
                {isFav && <Star className="h-3.5 w-3.5 flex-shrink-0 text-yellow-400" />}
              </div>
              <div className="grid grid-cols-3 gap-1 text-center text-[11px]">
                <Stat label="起用" value={`${playRate}%`} />
                <Stat label="勝率" value={`${(a.win_rate * 100).toFixed(0)}%`} highlight={a.win_rate >= 0.55} />
                <Stat label="KDA" value={a.avg_kda.toFixed(2)} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div>
      <p className={cn("font-black tabular-nums", highlight ? "text-green-400" : "text-white")}>{value}</p>
      <p className="text-[9px] text-slate-500">{label}</p>
    </div>
  );
}
