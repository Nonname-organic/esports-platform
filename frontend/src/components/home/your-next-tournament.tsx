"use client";

import Link from "next/link";
import { Sparkles, Users, Coins, ChevronRight } from "lucide-react";
import { cn, getGameColor, formatPrize } from "@/lib/utils";
import type { HomeRecommendation } from "@/features/home/api/home-api";
import { Countdown } from "@/components/live/countdown";
import { LiveDot } from "@/components/live/live-dot";

/** Your Next Tournament: おすすめ最優先カード（AIおすすめ理由付き）。 */
export function YourNextTournament({ rec }: { rec: HomeRecommendation }) {
  const fill = Math.round(rec.fill * 100);
  return (
    <Link
      href={`/tournaments/${rec.id}`}
      className={cn(
        "group relative block overflow-hidden rounded-3xl border border-green-500/30 bg-slate-900",
        "transition-all duration-300 will-change-transform hover:-translate-y-1 hover:border-green-400/60 hover:shadow-[0_24px_70px_-24px_rgba(34,197,94,0.55)]",
      )}
    >
      {/* 背景 */}
      <div className="absolute inset-0">
        {rec.banner_url ? (
          <img src={rec.banner_url} alt="" className="h-full w-full object-cover opacity-30 transition-transform duration-500 group-hover:scale-105" />
        ) : (
          <div className="h-full w-full bg-gradient-to-br from-slate-800 to-slate-950" />
        )}
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950 via-slate-950/85 to-slate-950/40" />
        <span className="pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shine" />
      </div>

      <div className="relative p-6">
        <div className="mb-2 flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-green-500/40 bg-green-500/15 px-2.5 py-1 text-[11px] font-black tracking-wide text-green-400">
            <LiveDot /> ENTRY OPEN
          </span>
          <span className={cn("rounded-full border px-2.5 py-0.5 text-[10px] font-bold", getGameColor(rec.game))}>{rec.game}</span>
          <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-purple-500/15 px-2.5 py-1 text-[10px] font-bold text-purple-300">
            <Sparkles className="h-3 w-3" /> あなたにおすすめ
          </span>
        </div>

        <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500">Your Next Tournament</p>
        <h2 className="mt-1 text-2xl font-black leading-tight text-white transition-colors group-hover:text-green-300 sm:text-3xl">{rec.name}</h2>
        <p className="mt-1 inline-flex items-center gap-1.5 text-xs font-semibold text-purple-300">
          <Sparkles className="h-3.5 w-3.5" /> {rec.reason}
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
          {rec.prize_pool != null && rec.prize_pool > 0 && (
            <span className="inline-flex items-center gap-1.5"><Coins className="h-4 w-4 text-yellow-400" /><span className="text-lg font-black text-yellow-400">{formatPrize(rec.prize_pool, rec.prize_currency)}</span></span>
          )}
          <span className="inline-flex items-center gap-1.5 text-slate-300"><Users className="h-4 w-4 text-slate-500" /><span className="font-black text-white">{rec.registered}</span><span className="text-slate-500">/ {rec.max_teams}</span></span>
        </div>

        <div className="mt-3 h-1.5 max-w-md overflow-hidden rounded-full bg-white/10">
          <div className="h-full rounded-full bg-gradient-to-r from-green-500 to-emerald-400" style={{ width: `${fill}%` }} />
        </div>

        <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
          {rec.registration_end_at && (
            <div>
              <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">Entry closes in</p>
              <Countdown target={rec.registration_end_at} size="md" />
            </div>
          )}
          <span className="inline-flex items-center gap-1.5 rounded-xl bg-green-500 px-5 py-2.5 text-sm font-black text-white transition-transform group-hover:translate-x-0.5">
            エントリー <ChevronRight className="h-4 w-4" />
          </span>
        </div>
      </div>
    </Link>
  );
}
