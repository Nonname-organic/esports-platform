"use client";

import { Users, Swords, Coins } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatPrize } from "@/lib/utils";
import { useTournamentStatistics } from "@/features/tournament-live/hooks/use-tournament-live";
import { AnimatedNumber } from "@/components/live/animated-number";

/** Statistics カード: 参加数 / 試合数 / 賞金（CountUp）。 */
export function TournamentStatisticsCard({ tournamentId }: { tournamentId: string }) {
  const { data } = useTournamentStatistics(tournamentId);
  if (!data) return null;

  const tiles = [
    { icon: Users, color: "text-brand-400", bg: "bg-brand-500/10", label: "参加チーム", value: data.participants, suffix: `/${data.max_teams}` },
    { icon: Swords, color: "text-red-400", bg: "bg-red-500/10", label: "試合数", value: data.matches },
  ];

  return (
    <div className="grid grid-cols-3 gap-3">
      {tiles.map((t) => (
        <div key={t.label} className="rounded-2xl border border-white/10 bg-slate-900 p-4">
          <div className={cn("mb-2 inline-flex rounded-xl p-2", t.bg)}>
            <t.icon className={cn("h-4 w-4", t.color)} />
          </div>
          <p className="text-2xl font-black tabular-nums text-white sm:text-3xl">
            <AnimatedNumber value={t.value} durationMs={1000} />
            {t.suffix && <span className="text-sm font-normal text-slate-500">{t.suffix}</span>}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">{t.label}</p>
        </div>
      ))}
      {/* Prize */}
      <div className="rounded-2xl border border-white/10 bg-slate-900 p-4">
        <div className="mb-2 inline-flex rounded-xl bg-yellow-500/10 p-2"><Coins className="h-4 w-4 text-yellow-400" /></div>
        <p className="text-2xl font-black text-yellow-400 sm:text-3xl">
          {data.prize_pool && data.prize_pool > 0 ? formatPrize(data.prize_pool, data.prize_currency) : "—"}
        </p>
        <p className="mt-0.5 text-xs text-slate-500">賞金総額</p>
      </div>
    </div>
  );
}
