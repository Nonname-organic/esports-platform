"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Users, Coins, CalendarDays, Trophy, ChevronRight } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn, getGameColor, formatPrize, formatDate } from "@/lib/utils";
import type { ListResponse, TournamentSummary } from "@/types/tournament";
import { Countdown } from "./countdown";
import { LiveBadge } from "./live-dot";

function useList(status: "ongoing" | "registration_open") {
  return useQuery({
    queryKey: status === "ongoing" ? ["live", "ongoing-tournaments"] : ["live", "entry-open"],
    queryFn: async () => {
      const res = await apiClient.get<ListResponse<TournamentSummary>>(
        `/api/v1/tournaments?status=${status}&limit=12`,
      );
      return res.data;
    },
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
    staleTime: 30000,
  });
}

/** Hero 直下の大型 Featured Tournament（最も賞金の大きい進行中/受付中を大きく訴求）。 */
export function FeaturedTournamentBanner() {
  const ongoing = useList("ongoing");
  const entry = useList("registration_open");
  const loading = ongoing.isLoading || entry.isLoading;

  const pool = [...(ongoing.data ?? []), ...(entry.data ?? [])];
  const featured = pool
    .slice()
    .sort((a, b) => (b.prize_pool ?? 0) - (a.prize_pool ?? 0) || b.registered_teams - a.registered_teams)[0];

  if (loading && !featured) {
    return <div className="h-56 w-full animate-pulse rounded-3xl border border-white/10 bg-white/[0.03]" />;
  }
  if (!featured) return null;

  const isEntry = featured.status === "registration_open";
  const fill = Math.min((featured.registered_teams / Math.max(featured.max_teams, 1)) * 100, 100);

  return (
    <Link
      href={`/tournaments/${featured.id}`}
      className={cn(
        "group relative grid grid-cols-1 overflow-hidden rounded-3xl border border-white/10 bg-slate-900 md:grid-cols-2",
        "transition-all duration-300 will-change-transform hover:-translate-y-1",
        isEntry
          ? "hover:border-green-500/50 hover:shadow-[0_20px_60px_-20px_rgba(34,197,94,0.5)]"
          : "hover:border-red-500/50 hover:shadow-[0_20px_60px_-20px_rgba(239,68,68,0.5)]",
      )}
    >
      {/* ビジュアル */}
      <div className="relative h-48 overflow-hidden md:h-full md:min-h-[16rem]">
        {featured.banner_url ? (
          <img
            src={featured.banner_url}
            alt=""
            className="h-full w-full object-cover opacity-60 transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-slate-800 to-slate-950">
            <Trophy className="h-20 w-20 text-white/10" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/40 to-transparent md:bg-gradient-to-r" />
        <div className="absolute left-4 top-4 flex items-center gap-2">
          <span className={cn("rounded-full border px-3 py-1 text-xs font-bold", getGameColor(featured.game))}>
            {featured.game}
          </span>
          {isEntry ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-green-500/40 bg-green-500/15 px-2.5 py-1 text-[11px] font-black tracking-wide text-green-400">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-live-blink" /> ENTRY OPEN
            </span>
          ) : (
            <LiveBadge />
          )}
        </div>
      </div>

      {/* 情報 */}
      <div className="flex flex-col justify-center gap-4 p-6">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500">Featured Tournament</p>
          <h2 className="mt-1 text-2xl font-black leading-tight text-white transition-colors group-hover:text-white sm:text-3xl">
            {featured.name}
          </h2>
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
          {featured.prize_pool != null && featured.prize_pool > 0 && (
            <span className="inline-flex items-center gap-1.5">
              <Coins className="h-4 w-4 text-yellow-400" />
              <span className="text-lg font-black text-yellow-400">{formatPrize(featured.prize_pool)}</span>
            </span>
          )}
          <span className="inline-flex items-center gap-1.5 text-slate-300">
            <Users className="h-4 w-4 text-slate-500" />
            <span className="font-black text-white">{featured.registered_teams}</span>
            <span className="text-slate-500">/ {featured.max_teams} Teams</span>
          </span>
          {featured.start_at && (
            <span className="inline-flex items-center gap-1.5 text-slate-300">
              <CalendarDays className="h-4 w-4 text-slate-500" />
              {formatDate(featured.start_at)}
            </span>
          )}
        </div>

        {/* 参加率バー */}
        <div className="h-2 overflow-hidden rounded-full bg-white/10">
          <div
            className={cn("h-full rounded-full transition-all duration-500", isEntry ? "bg-gradient-to-r from-green-500 to-emerald-400" : "bg-gradient-to-r from-brand-500 to-red-400")}
            style={{ width: `${fill}%` }}
          />
        </div>

        <div className="flex flex-wrap items-end justify-between gap-3">
          {isEntry && featured.registration_end_at ? (
            <div>
              <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">Entry closes in</p>
              <Countdown target={featured.registration_end_at} size="md" />
            </div>
          ) : <span />}
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-xl px-5 py-2.5 text-sm font-black text-white transition-transform group-hover:translate-x-0.5",
              isEntry ? "bg-green-500" : "bg-brand-500",
            )}
          >
            {isEntry ? "エントリー" : "試合を見る"}
            <ChevronRight className="h-4 w-4" />
          </span>
        </div>
      </div>
    </Link>
  );
}
