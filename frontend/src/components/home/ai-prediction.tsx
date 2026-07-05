"use client";

import Link from "next/link";
import { Sparkles, Crown, Flame } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HomePredictions } from "@/features/home/api/home-api";

/** AI Prediction: 優勝予測（RuleBased・LLM差し替え可）。favorite/contenders/dark horse。 */
export function AiPrediction({ pred }: { pred: HomePredictions }) {
  if (!pred.favorite) return null;
  return (
    <section className="rounded-2xl border border-purple-500/25 bg-gradient-to-br from-slate-900 to-slate-950 p-5">
      <div className="mb-3 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-purple-400" />
        <h2 className="font-bold text-white">AI 優勝予測</h2>
        <span className="rounded-full border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 text-[10px] font-bold text-purple-300">Rule-based · LLM-ready</span>
      </div>
      <Link href={`/tournaments/${pred.tournament.id}`} className="mb-3 block truncate text-xs text-slate-500 hover:text-slate-300">
        {pred.tournament.name}
      </Link>

      {/* Favorite */}
      <Link href={`/teams/${pred.favorite.team_id}`} className="group mb-3 flex items-center gap-3 rounded-xl border border-yellow-500/25 bg-yellow-500/[0.06] px-3 py-2.5 transition-colors hover:border-yellow-400/50">
        <Crown className="h-5 w-5 flex-shrink-0 text-yellow-400" style={{ filter: "drop-shadow(0 0 8px rgba(234,179,8,0.6))" }} />
        <span className="min-w-0 flex-1 truncate font-black text-white group-hover:text-yellow-300">{pred.favorite.team_name}</span>
        <span className="text-lg font-black tabular-nums text-yellow-400">{pred.favorite.win_prob}%</span>
      </Link>

      {/* Contenders bars */}
      <ul className="space-y-1.5">
        {pred.contenders.slice(1).map((c) => (
          <li key={c.team_id}>
            <Link href={`/teams/${c.team_id}`} className="flex items-center gap-2 text-xs">
              <span className="w-24 flex-shrink-0 truncate text-slate-300">{c.team_name}</span>
              <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
                <span className="block h-full rounded-full bg-gradient-to-r from-brand-500 to-purple-400" style={{ width: `${Math.min(c.win_prob * 2.5, 100)}%` }} />
              </span>
              <span className="w-10 flex-shrink-0 text-right tabular-nums font-bold text-white">{c.win_prob}%</span>
            </Link>
          </li>
        ))}
      </ul>

      {pred.dark_horse && (
        <p className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-slate-300">
          <Flame className={cn("h-3.5 w-3.5 text-red-400")} /> ダークホース <b className="text-white">{pred.dark_horse.team_name}</b>
        </p>
      )}
    </section>
  );
}
