"use client";

import { BarChart3 } from "lucide-react";
import { usePlayerCareer } from "@/features/career/hooks/use-career";
import { AnimatedNumber } from "@/components/live/animated-number";

/** Career Statistics: 主要指標を CountUp 表示。 */
export function CareerStatisticsCard({ playerId }: { playerId: string }) {
  const { data: c } = usePlayerCareer(playerId);
  if (!c) return null;

  const counts = [
    { label: "Matches", value: c.total_matches },
    { label: "Wins", value: c.total_wins },
    { label: "Losses", value: c.total_losses },
    { label: "MVP", value: c.mvp_count },
    { label: "優勝", value: c.championships },
    { label: "大会", value: c.tournaments_played },
  ];
  const rates = [
    { label: "Win Rate", value: `${(c.win_rate * 100).toFixed(1)}%` },
    { label: "KDA", value: c.avg_kda.toFixed(2) },
    { label: "ACS", value: c.avg_acs.toFixed(0) },
    { label: "Peak RR", value: c.peak_rating != null ? String(c.peak_rating) : "—" },
  ];

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-4 flex items-center gap-2 font-bold text-white">
        <BarChart3 className="h-4 w-4 text-brand-400" /> Career Statistics
      </h2>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
        {counts.map((s) => (
          <div key={s.label} className="rounded-xl border border-white/8 bg-white/[0.02] p-3 text-center">
            <p className="text-xl font-black tabular-nums text-white sm:text-2xl"><AnimatedNumber value={s.value} durationMs={900} /></p>
            <p className="text-[10px] text-slate-500">{s.label}</p>
          </div>
        ))}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {rates.map((s) => (
          <div key={s.label} className="rounded-xl border border-white/8 bg-white/[0.02] p-3 text-center">
            <p className="text-xl font-black tabular-nums text-white sm:text-2xl">{s.value}</p>
            <p className="text-[10px] text-slate-500">{s.label}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
