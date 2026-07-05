"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Users, Coins, ChevronRight } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn, getGameColor, formatPrize } from "@/lib/utils";
import type { ListResponse, TournamentSummary } from "@/types/tournament";
import { Countdown } from "@/components/live/countdown";
import { LiveDot } from "@/components/live/live-dot";

/** 受付中で「最も締切が近い」大会 = Hero の受付カウンター（大会受付画面の中心）。 */
export function FeaturedEntry() {
  const { data, isLoading } = useQuery({
    queryKey: ["live", "entry-open"],
    queryFn: async () => {
      const res = await apiClient.get<ListResponse<TournamentSummary>>(
        "/api/v1/tournaments?status=registration_open&limit=12",
      );
      return res.data;
    },
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
    staleTime: 30000,
  });

  const featured = (data ?? [])
    .slice()
    .sort((a, b) => {
      const ta = a.registration_end_at ? new Date(a.registration_end_at).getTime() : Infinity;
      const tb = b.registration_end_at ? new Date(b.registration_end_at).getTime() : Infinity;
      return ta - tb;
    })[0];

  // CLS回避: ロード中は同じ高さのスケルトンを予約
  if (isLoading && !featured) {
    return <div className="mt-10 h-[188px] w-full max-w-2xl animate-pulse rounded-2xl border border-white/10 bg-white/[0.03]" />;
  }
  if (!featured) return null;

  return (
    <Link
      href={`/tournaments/${featured.id}`}
      className={cn(
        "group mt-10 block w-full max-w-2xl overflow-hidden rounded-2xl border border-green-500/30 bg-slate-950/70 backdrop-blur-md",
        "shadow-[0_0_50px_-14px_rgba(34,197,94,0.55)] transition-all duration-300 hover:-translate-y-0.5 hover:border-green-400/60 hover:shadow-[0_0_60px_-8px_rgba(34,197,94,0.75)]",
      )}
    >
      {/* ENTRY OPEN 帯 */}
      <div className="flex items-center gap-2 border-b border-white/10 bg-green-500/10 px-4 py-1.5">
        <LiveDot />
        <span className="text-[11px] font-black tracking-widest text-green-400">ENTRY OPEN</span>
        <span className={cn("ml-auto rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(featured.game))}>
          {featured.game}
        </span>
      </div>

      <div className="px-5 py-4 text-left">
        {/* 大会名 */}
        <h2 className="truncate text-xl font-black text-white transition-colors group-hover:text-green-300 sm:text-2xl">
          {featured.name}
        </h2>

        {/* 参加数 + 賞金 */}
        <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
          <span className="inline-flex items-center gap-1.5 text-slate-300">
            <Users className="h-4 w-4 text-slate-500" />
            <span className="font-black text-white">{featured.registered_teams}</span>
            <span className="text-slate-500">/ {featured.max_teams} Teams</span>
          </span>
          {featured.prize_pool != null && featured.prize_pool > 0 && (
            <span className="inline-flex items-center gap-1.5 font-bold text-yellow-400">
              <Coins className="h-4 w-4" />
              {formatPrize(featured.prize_pool)}
            </span>
          )}
        </div>

        {/* カウントダウン */}
        <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">Entry closes in</p>
            <Countdown target={featured.registration_end_at} size="lg" />
          </div>
          <span className="inline-flex items-center gap-1 rounded-lg bg-green-500 px-4 py-2 text-sm font-black text-white transition-transform group-hover:translate-x-0.5">
            エントリー
            <ChevronRight className="h-4 w-4" />
          </span>
        </div>
      </div>
    </Link>
  );
}
