"use client";

import { Trophy, Star, Swords, Coins } from "lucide-react";
import { formatPrize } from "@/lib/utils";
import { useTournamentOverview } from "@/features/tournament-live/hooks/use-tournament-live";

/** Results 演出: 完了大会の Champion / Runner-up / MVP / Prize（Glow + Shine / Confetti-ready）。 */
export function ResultsCard({ tournamentId }: { tournamentId: string }) {
  const { data } = useTournamentOverview(tournamentId);
  const result = data?.result;
  const champion = result?.champion?.team_name;
  if (!result || !champion) return null;

  return (
    <section className="relative overflow-hidden rounded-2xl border border-yellow-500/30 bg-gradient-to-br from-slate-900 to-slate-950 p-6 text-center">
      {/* Glow + Shine（Confetti はここに載せられる接合点） */}
      <div className="pointer-events-none absolute -top-16 left-1/2 h-40 w-40 -translate-x-1/2 rounded-full bg-yellow-500/15 blur-3xl" />
      <span className="pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 bg-gradient-to-r from-transparent via-white/12 to-transparent animate-shine" />

      <div className="relative">
        <p className="text-[11px] font-black uppercase tracking-[0.3em] text-yellow-400">Champion</p>
        <div className="mt-2 inline-flex items-center gap-2">
          <Trophy className="h-7 w-7 text-yellow-400" style={{ filter: "drop-shadow(0 0 10px rgba(234,179,8,0.7))" }} />
          <span className="text-3xl font-black text-white sm:text-4xl">{champion}</span>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm">
          {result.runner_up?.team_name && (
            <span className="inline-flex items-center gap-1.5 text-slate-400">
              <Swords className="h-3.5 w-3.5 text-slate-500" /> Runner-up <span className="font-semibold text-slate-200">{result.runner_up.team_name}</span>
            </span>
          )}
          {result.mvp && (
            <span className="inline-flex items-center gap-1.5 text-slate-300">
              <Star className="h-3.5 w-3.5 text-pink-400" /> MVP <span className="font-bold text-white">{result.mvp}</span>
            </span>
          )}
          {data?.prize_pool && data.prize_pool > 0 && (
            <span className="inline-flex items-center gap-1.5 font-bold text-yellow-400">
              <Coins className="h-3.5 w-3.5" /> {formatPrize(data.prize_pool, data.prize_currency)}
            </span>
          )}
        </div>
      </div>
    </section>
  );
}
