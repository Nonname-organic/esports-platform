"use client";

import Link from "next/link";
import { Users, Coins, Sparkles } from "lucide-react";
import { cn, getGameColor, formatPrize } from "@/lib/utils";
import type { HomeRecommendation } from "@/features/home/api/home-api";
import { Countdown } from "@/components/live/countdown";

/** Upcoming For You / Because You Played: おすすめ大会の横スクロール。 */
export function RecommendationsRow({ title, recs }: { title: string; recs: HomeRecommendation[] }) {
  if (recs.length === 0) return null;
  return (
    <section>
      <h2 className="mb-3 flex items-center gap-2 text-lg font-bold text-white">
        <Sparkles className="h-5 w-5 text-brand-400" /> {title}
      </h2>
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
        {recs.map((r) => (
          <Link
            key={r.id}
            href={`/tournaments/${r.id}`}
            className="group w-64 flex-shrink-0 overflow-hidden rounded-2xl border border-white/10 bg-slate-900 transition-all hover:-translate-y-1 hover:border-green-500/40 hover:shadow-[0_12px_36px_-14px_rgba(34,197,94,0.4)]"
          >
            <div className="relative h-24 overflow-hidden bg-gradient-to-br from-slate-800 to-slate-950">
              {r.banner_url && <img src={r.banner_url} alt="" className="h-full w-full object-cover opacity-50 transition-transform duration-500 group-hover:scale-110" />}
              <span className={cn("absolute left-2 top-2 rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(r.game))}>{r.game}</span>
            </div>
            <div className="p-3">
              <p className="line-clamp-1 text-sm font-bold text-white group-hover:text-green-300">{r.name}</p>
              <p className="mt-0.5 line-clamp-1 text-[11px] text-purple-300">{r.reason}</p>
              <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                <span className="inline-flex items-center gap-1"><Users className="h-3 w-3 text-slate-500" />{r.registered}/{r.max_teams}</span>
                {r.prize_pool != null && r.prize_pool > 0 && (
                  <span className="inline-flex items-center gap-1 font-bold text-yellow-400"><Coins className="h-3 w-3" />{formatPrize(r.prize_pool, r.prize_currency)}</span>
                )}
              </div>
              {r.registration_end_at && <div className="mt-2"><Countdown target={r.registration_end_at} size="md" /></div>}
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
